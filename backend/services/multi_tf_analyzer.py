"""
multi_tf_analyzer.py — محلل متعدد الأطر الزمنية المتكامل
==========================================================
يفتح TradingView لكل إطار زمني مطلوب تلقائياً عبر Playwright،
ثم يشغّل voting_engine + agent_manager على كل إطار،
ويجمع النتائج في توصية صفقة واحدة شاملة.
"""

import asyncio
import logging
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# الأطر الزمنية المرتبة من الأكبر للأصغر (top-down)
ANALYSIS_TIMEFRAMES = {
    "scalping": ["H1", "M15", "M5"],
    "يومي":    ["H4", "H1", "M15"],
    "day":     ["H4", "H1", "M15"],
    "swing":   ["D1", "H4", "H1"],
    "سوينج":   ["D1", "H4", "H1"],
    "سكالبينج": ["H1", "M15", "M5"],
}

DEFAULT_TFS = ["H4", "H1", "M15"]  # fallback إذا لم يُحدد نوع التداول


async def capture_screenshots_parallel(
    symbol: str, timeframes: List[str]
) -> Dict[str, Optional[bytes]]:
    """
    يلتقط شاشات TradingView لجميع الأطر الزمنية بالتوازي.
    يُرجع dict مثل: {"H4": bytes, "H1": bytes, "M15": None}
    """
    try:
        from services.tv_screenshot import capture_tradingview_chart
    except ImportError:
        logger.error("tv_screenshot not available")
        return {tf: None for tf in timeframes}

    results = {}
    for tf in timeframes:
        try:
            logger.info(f"Capturing {symbol} {tf} sequentially...")
            res = await asyncio.wait_for(
                capture_tradingview_chart(symbol, tf),
                timeout=65
            )
            results[tf] = res
        except Exception as e:
            logger.warning(f"Screenshot failed for {symbol} {tf}: {e}")
            results[tf] = None

    success_count = sum(1 for v in results.values() if v)
    logger.info(f"Captured {success_count}/{len(timeframes)} screenshots for {symbol}")
    return results


def run_voting_engine_for_screenshot(
    screenshot_bytes: Optional[bytes],
    symbol: str,
    tf: str,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    يشغّل voting_engine على صورة واحدة (إطار زمني واحد).
    يُرجع نتيجة التحليل الكاملة.
    """
    try:
        from services.voting_engine import voting_engine
        from services.agent_manager import AgentManager

        # بناء visual_context
        visual_context = [{
            "description": f"TradingView chart for {symbol} on {tf} timeframe",
            "market": symbol,
            "timeframe": tf,
        }]

        if screenshot_bytes:
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            visual_context[0]["images"] = [{"data": b64, "mimeType": "image/png"}]

        # تشغيل agent_manager أولاً للحصول على أوزان المنظم
        orchestrator_weights = None
        try:
            agent_mgr = AgentManager()
            unified = voting_engine.data_adapter.normalize_input(visual_context, symbol)
            agent_payload = agent_mgr.run(unified)
            orchestrator_weights = agent_payload.get("orchestrator", {}).get("weights")
        except Exception as e:
            logger.warning(f"AgentManager pre-analysis failed for {tf}: {e}")

        # تشغيل voting_engine الكامل
        result = voting_engine.analyze(
            visual_context, symbol, user_id,
            orchestrator_weights=orchestrator_weights
        )
        result["timeframe"] = tf
        result["has_screenshot"] = screenshot_bytes is not None
        return result

    except Exception as e:
        logger.error(f"voting_engine failed for {symbol} {tf}: {e}")
        return {
            "timeframe": tf,
            "recommendation": "تعليق",
            "confidence": 0,
            "reason": f"فشل التحليل: {str(e)}",
            "has_screenshot": screenshot_bytes is not None,
        }


async def full_multi_tf_analysis(
    symbol: str,
    trade_type: str = "يومي",
    user_id: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    التحليل الشامل المتكامل:
    1. يفتح TradingView لكل إطار زمني بالتوازي
    2. يشغّل voting_engine + agent_manager على كل إطار
    3. يجمع النتائج عبر Gemini Vision
    4. يُرجع توصية صفقة كاملة أو "لا توجد فرصة"
    """
    timeframes = ANALYSIS_TIMEFRAMES.get(trade_type.lower(), DEFAULT_TFS)

    logger.info(f"🔍 بدء التحليل الشامل: {symbol} | أطر: {timeframes} | نوع: {trade_type}")

    # الخطوة 1: التقاط الشاشات بالتوازي
    screenshots = await capture_screenshots_parallel(symbol, timeframes)

    # الخطوة 2: تشغيل voting_engine على كل إطار بالتوازي (في thread pool)
    tf_results = {}
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(
            None,
            run_voting_engine_for_screenshot,
            screenshots.get(tf),
            symbol,
            tf,
            user_id,
        )
        for tf in timeframes
    ]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    for tf, result in zip(timeframes, gathered):
        if isinstance(result, Exception):
            tf_results[tf] = {
                "timeframe": tf, "recommendation": "تعليق",
                "confidence": 0, "reason": str(result),
                "has_screenshot": screenshots.get(tf) is not None
            }
        else:
            tf_results[tf] = result

    # الخطوة 3: تجميع إشارات كل الأطر
    signals_summary = _aggregate_tf_signals(tf_results, timeframes)

    # الخطوة 4: تحليل Gemini Vision الشامل
    gemini_result = await _run_gemini_final_analysis(
        symbol, trade_type, timeframes, screenshots, tf_results, signals_summary, api_key
    )

    return {
        "symbol": symbol,
        "trade_type": trade_type,
        "timeframes_analyzed": timeframes,
        "screenshots_captured": [tf for tf, v in screenshots.items() if v],
        "tf_results": tf_results,
        "signals_summary": signals_summary,
        "final_analysis": gemini_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _aggregate_tf_signals(tf_results: Dict, timeframes: List[str]) -> Dict[str, Any]:
    """يجمع إشارات كل الأطر الزمنية ويحسب الاتجاه العام."""
    buy_score = 0
    sell_score = 0
    neutral_count = 0
    total_confidence = 0
    details = []

    # أوزان الأطر الزمنية: الأعلى يأخذ وزناً أكبر
    weights_map = {"D1": 3, "H4": 2.5, "H1": 2, "M30": 1.5, "M15": 1, "M5": 0.7}

    for tf in timeframes:
        res = tf_results.get(tf, {})
        rec = res.get("recommendation", "")
        conf = res.get("confidence", 0)
        w = weights_map.get(tf, 1)
        total_confidence += conf

        if "شراء" in rec or rec == "Buy":
            buy_score += conf * w
        elif "بيع" in rec or rec == "Sell":
            sell_score += conf * w
        else:
            neutral_count += 1

        details.append({
            "tf": tf,
            "signal": rec,
            "confidence": conf,
            "has_screenshot": res.get("has_screenshot", False),
        })

    avg_conf = total_confidence // max(len(timeframes), 1)
    overall = "محايد"
    if buy_score > sell_score and buy_score > 0:
        overall = "شراء"
    elif sell_score > buy_score and sell_score > 0:
        overall = "بيع"

    alignment = "متوافق" if neutral_count == 0 else "جزئي"
    if buy_score > 0 and sell_score > 0:
        alignment = "متعارض"

    return {
        "overall_signal": overall,
        "buy_score": round(buy_score, 1),
        "sell_score": round(sell_score, 1),
        "avg_confidence": avg_conf,
        "alignment": alignment,
        "details": details,
    }


async def _run_gemini_final_analysis(
    symbol: str,
    trade_type: str,
    timeframes: List[str],
    screenshots: Dict[str, Optional[bytes]],
    tf_results: Dict,
    signals_summary: Dict,
    api_key: Optional[str],
) -> str:
    """يُشغّل Gemini Vision على كل الشاشات مع سياق نتائج voting_engine."""

    if not api_key:
        return _fallback_analysis_text(symbol, trade_type, signals_summary, tf_results, timeframes)

    # بناء البرومبت الشامل
    tf_context = "\n".join([
        f"• {d['tf']}: {d['signal']} (ثقة: {d['confidence']}%) {'📸' if d['has_screenshot'] else '⚠️ بدون شاشة'}"
        for d in signals_summary.get("details", [])
    ])

    prompt_text = f"""أنت كبير محللي التداول في VisionTrader AI. معك الآن تحليل متكامل من نظام الوكلاء الاصطناعيين.

**الزوج:** {symbol}
**نوع التداول:** {trade_type}
**الأطر الزمنية المحللة:** {', '.join(timeframes)}

**نتائج نظام التصويت (voting_engine) لكل إطار:**
{tf_context}

**الإشارة الإجمالية:** {signals_summary.get('overall_signal', 'محايد')} | متوسط الثقة: {signals_summary.get('avg_confidence', 0)}% | التوافق: {signals_summary.get('alignment', 'محايد')}

**مهمتك:** بناءً على الصور الحية من TradingView والنتائج أعلاه، قدم:

1. 📈 **الاتجاه العام** (صعودي/هابط/عرضي) مع التفسير
2. 🔍 **قراءة كل إطار زمني** بإيجاز
3. ⚡ **فرصة الصفقة** (إذا وجدت):
   - نوع الصفقة: شراء/بيع
   - **نقطة الدخول:** سعر محدد
   - **وقف الخسارة (SL):** سعر محدد + السبب
   - **الهدف الأول (TP1):** 
   - **الهدف الثاني (TP2):**
   - **الهدف الثالث (TP3):**
   - **نسبة المخاطرة/العائد (R:R):**
4. ⚠️ **تحذيرات أو ملاحظات** مهمة
5. ⏱️ **أفضل توقيت للدخول**

إذا لم تكن هناك فرصة واضحة، قل ذلك صراحةً مع السبب.
أسلوبك: احترافي، حاسم، بالأرقام الفعلية."""

    # بناء الأجزاء مع الصور
    parts = [{"text": prompt_text}]
    screenshots_added = 0
    for tf in timeframes:
        img_bytes = screenshots.get(tf)
        if img_bytes:
            import base64
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts.append({
                "text": f"\n\n--- شارت {symbol} على الإطار {tf} ---"
            })
            parts.append({
                "inlineData": {"mimeType": "image/png", "data": b64}
            })
            screenshots_added += 1

    if screenshots_added == 0:
        parts.append({"text": "\n\n⚠️ ملاحظة: لم تُلتقط الشاشات تلقائياً. حلل بناءً على نتائج الوكلاء فقط."})

    import httpx
    import os

    note_gemini = (
        f"\n\n---\n"
        f"\u00f0\u009f\u0093\u00b8 **\u062a\u0645 \u062a\u062d\u0644\u064a\u0644 {screenshots_added}/{len(timeframes)} \u0634\u0627\u0634\u0627\u062a**"
        f" \u0645\u0646 TradingView \u0639\u0628\u0631 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a\n"
        f"\u00f0\u009f\u00a4\u0096 **\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0645\u064f\u0641\u0639\u0651\u064e\u0644\u0629:** "
        f"\u0646\u0638\u0627\u0645 \u0627\u0644\u062a\u0635\u0648\u064a\u062a + \u0645\u062f\u064a\u0631 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 + Gemini Vision"
    )
    note_openrouter = (
        f"\n\n---\n"
        f"\u00f0\u009f\u0093\u00b8 **\u062a\u0645 \u062a\u062d\u0644\u064a\u0644 {screenshots_added}/{len(timeframes)} \u0634\u0627\u0634\u0627\u062a**"
        f" \u0645\u0646 TradingView\n"
        f"\u00f0\u009f\u00a4\u0096 **\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0645\u064f\u0641\u0639\u0651\u064e\u0644\u0629:** "
        f"\u0646\u0638\u0627\u0645 \u0627\u0644\u062a\u0635\u0648\u064a\u062a + \u0645\u062f\u064a\u0631 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 + AI Vision (OpenRouter)"
    )

    # --- 1. Try Gemini (primary, supports vision/images) ---
    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]:
        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            payload = {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2500,
                }
            }
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 429:
                    logger.warning(f"Gemini {model_name}: quota exceeded (429), trying next")
                    continue
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        extracted = content_parts[0].get("text", "").strip()
                        if extracted:
                            logger.info(f"Gemini {model_name} succeeded")
                            return extracted + note_gemini
                logger.warning(f"Gemini {model_name}: empty response")
        except Exception as e:
            logger.warning(f"Gemini {model_name} failed: {e}")
            continue

    # --- 2. Try OpenRouter (supports many models, text-only) ---
    openrouter_key = ""
    try:
        from config import settings as _cfg_or
        openrouter_key = getattr(_cfg_or, "OPENROUTER_API_KEY", "")
    except ImportError:
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

    if openrouter_key:
        for or_model in [
            "anthropic/claude-3-haiku",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.0-flash-001",
        ]:
            try:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://visiontrader.ai",
                    "X-Title": "VisionTrader AI",
                }
                payload = {
                    "model": or_model,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": 0.4,
                    "max_tokens": 2500,
                }
                async with httpx.AsyncClient(timeout=45) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code in (402, 403, 404):
                        logger.warning(f"OpenRouter {or_model}: unavailable ({resp.status_code})")
                        continue
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    if text:
                        logger.info(f"OpenRouter {or_model} succeeded")
                        return text + note_openrouter
            except Exception as e:
                logger.warning(f"OpenRouter {or_model} failed: {e}")
                continue

    # --- 3. Try DeepSeek (tertiary, text-only) ---
    deepseek_key = ""
    try:
        from config import settings as _cfg_ds
        deepseek_key = getattr(_cfg_ds, "DEEPSEEK_API_KEY", "")
    except ImportError:
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")

    if deepseek_key:
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {deepseek_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt_text}],
                "temperature": 0.4,
                "max_tokens": 2500
            }
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code not in (402, 403):
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    if text:
                        logger.info("DeepSeek succeeded")
                        return text + note_openrouter
        except Exception as e:
            logger.warning(f"DeepSeek fallback failed: {e}")

    return _fallback_analysis_text(symbol, trade_type, signals_summary, tf_results, timeframes)

def _fallback_analysis_text(
    symbol: str,
    trade_type: str,
    signals_summary: Dict,
    tf_results: Dict,
    timeframes: List[str],
) -> str:
    """نص تحليلي احتياطي عند فشل Gemini."""
    overall = signals_summary.get("overall_signal", "محايد")
    avg_conf = signals_summary.get("avg_confidence", 0)
    alignment = signals_summary.get("alignment", "غير محدد")

    lines = [f"## 📊 تحليل {symbol} — {trade_type}\n"]
    lines.append(f"**الإشارة الإجمالية:** {overall} | **الثقة:** {avg_conf}% | **التوافق:** {alignment}\n")

    lines.append("\n### قراءة الأطر الزمنية:")
    for tf in timeframes:
        res = tf_results.get(tf, {})
        rec = res.get("recommendation", "غير محدد")
        conf = res.get("confidence", 0)
        icon = "📸" if res.get("has_screenshot") else "⚠️"
        lines.append(f"- **{tf}**: {rec} ({conf}%) {icon}")

    if overall in ("شراء", "بيع") and avg_conf >= 55:
        lines.append(f"\n### ⚡ فرصة محتملة:")
        lines.append(f"- **النوع:** {overall}")
        lines.append(f"- **التحقق مطلوب:** راجع مستويات الدعم والمقاومة على الشارت")
        lines.append(f"- **الإطار الرئيسي:** {timeframes[0]}")
    else:
        lines.append("\n### ⛔ لا توجد فرصة واضحة الآن")
        lines.append("- الإشارات غير متوافقة بما يكفي")
        lines.append("- انتظر تأكيد أوضح قبل الدخول")

    lines.append("\n---")
    lines.append("⚠️ *التحليل من نظام التصويت فقط - Gemini غير متاح*")
    return "\n".join(lines)
