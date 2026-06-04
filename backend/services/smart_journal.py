from collections import defaultdict
from datetime import datetime, timezone
from database import SessionLocal
import models

SESSIONS = [
    (0, 2, "جلسة سيدني"),
    (2, 10, "جلسة طوكيو"),
    (10, 18, "جلسة لندن"),
    (18, 24, "جلسة نيويورك")
]

MISTAKE_KEYWORDS = {
    "وقف ضيق": ["وقف ضيق", "tight stop", "stop tight", "ضيق"],
    "دخول مبكر": ["دخول مبكر", "early entry", "دخلت مبكراً", "الحققت"],
    "طمع": ["طمع", "greed", "جشع", "أطمع"],
    "خروج مبكر": ["خروج مبكر", "early exit", "خرجت مبكراً", "سبقت"],
}

class SmartJournal:
    def _session_name(self, created_at: datetime):
        hour = created_at.hour
        for start, end, name in SESSIONS:
            if start <= hour < end:
                return name
        return "غير معروفة"

    def _normalize_result(self, result: str):
        return str(result or "").strip().lower()

    def _common_mistakes(self, entries):
        mistakes = defaultdict(int)
        for entry in entries:
            text = f"{entry.notes or ''} {entry.mood or ''}".lower()
            for label, keywords in MISTAKE_KEYWORDS.items():
                if any(keyword in text for keyword in keywords):
                    mistakes[label] += 1

            if entry.profit_loss is not None and entry.profit_loss < 0:
                if entry.profit_loss > -50:
                    mistakes["وقف ضيق"] += 0.2
                if "دخلت" in text or "مبك" in text:
                    mistakes["دخول مبكر"] += 0.3
                if "سبقت" in text or "خرجت" in text:
                    mistakes["خروج مبكر"] += 0.3
            if entry.profit_loss is not None and entry.profit_loss > 0:
                if "طمع" in text or "جشع" in text:
                    mistakes["طمع"] += 0.5

        sorted_mistakes = [key for key, count in sorted(mistakes.items(), key=lambda x: x[1], reverse=True) if count > 0]
        return sorted_mistakes[:3]

    def _best_session(self, entries):
        session_stats = defaultdict(lambda: {"wins": 0, "trades": 0, "pnl": 0.0})
        for entry in entries:
            session = self._session_name(entry.created_at or entry.date or datetime.now(timezone.utc))
            session_stats[session]["trades"] += 1
            if self._normalize_result(entry.result) == "win":
                session_stats[session]["wins"] += 1
            session_stats[session]["pnl"] += float(entry.profit_loss or 0)

        if not session_stats:
            return None

        best = None
        best_score = -1
        for session, stats in session_stats.items():
            if stats["trades"] == 0:
                continue
            win_rate = stats["wins"] / stats["trades"]
            score = win_rate * 100 + (stats["pnl"] / 1000)
            if score > best_score:
                best_score = score
                best = {
                    "session": session,
                    "win_rate": int(win_rate * 100),
                    "trades": stats["trades"],
                    "pnl": round(stats["pnl"], 2)
                }
        return best

    def _best_market(self, entries):
        market_stats = defaultdict(lambda: {"wins": 0, "trades": 0, "pnl": 0.0})
        for entry in entries:
            market = entry.market or "غير محدد"
            market_stats[market]["trades"] += 1
            if self._normalize_result(entry.result) == "win":
                market_stats[market]["wins"] += 1
            market_stats[market]["pnl"] += float(entry.profit_loss or 0)

        best = None
        best_rate = -1
        for market, stats in market_stats.items():
            if stats["trades"] < 2:
                continue
            win_rate = stats["wins"] / stats["trades"]
            if win_rate > best_rate:
                best_rate = win_rate
                best = {
                    "market": market,
                    "win_rate": int(win_rate * 100),
                    "trades": stats["trades"],
                    "pnl": round(stats["pnl"], 2)
                }

        if best is None and market_stats:
            market, stats = max(market_stats.items(), key=lambda item: item[1]["wins"] / max(item[1]["trades"], 1))
            best = {
                "market": market,
                "win_rate": int((stats["wins"] / max(stats["trades"], 1)) * 100),
                "trades": stats["trades"],
                "pnl": round(stats["pnl"], 2)
            }
        return best

    def _ideal_risk(self, entries):
        if not entries:
            return 2.0
        win_rate = len([e for e in entries if self._normalize_result(e.result) == "win"]) / max(len(entries), 1)
        avg_loss = 0.0
        loss_count = 0
        for e in entries:
            if e.profit_loss is not None and e.profit_loss < 0:
                avg_loss += abs(e.profit_loss)
                loss_count += 1
        avg_loss = avg_loss / max(loss_count, 1)

        if win_rate >= 0.65:
            return 1.3
        if win_rate >= 0.55:
            return 1.7
        if win_rate >= 0.45:
            return 2.0
        return 2.5

    def get_insights(self, user_id):
        db = SessionLocal()
        try:
            entries = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).all()
            if not entries:
                return {
                    "best_session": None,
                    "best_market": None,
                    "common_mistakes": [],
                    "ideal_risk": 2.0,
                    "recommendation": "لا يوجد بيانات كافية بعد لبناء تحليل الأداء. سجّل بعض الصفقات الأولى.",
                    "summary": "ابدأ بتسجيل الصفقات في دفتر اليوميات حتى يتمكن النظام من تقديم توصيات ذكية." 
                }

            best_session = self._best_session(entries)
            best_market = self._best_market(entries)
            mistakes = self._common_mistakes(entries)
            ideal_risk = self._ideal_risk(entries)

            session_text = f"أفضل أداء لديك في {best_session['session']} مع نسبة نجاح {best_session['win_rate']}%." if best_session else "لم يتم تحديد أفضل وقت بعد."
            market_text = f"أفضل سوق لديك هو {best_market['market']} مع نسبة نجاح {best_market['win_rate']}%." if best_market else "لم يتم تحديد أفضل سوق بعد."
            mistakes_text = ", ".join(mistakes) if mistakes else "لا توجد أخطاء متكررة واضحة بعد."
            advice = "وقف الخسارة لديك متوازن حالياً، استمر في ضبط حجم المخاطرة حسب خطة التداول." if ideal_risk <= 1.7 else "قد يكون من الأفضل تقليل المخاطرة إلى حوالي 1.7% أو أقل إذا كنت تخسر بشكل متقطع."

            return {
                "best_session": session_text,
                "best_market": market_text,
                "common_mistakes": mistakes,
                "ideal_risk": round(ideal_risk, 1),
                "recommendation": advice,
                "summary": f"{session_text} {market_text} الأخطاء المتكررة: {mistakes_text}. انصحك باستخدام نسبة مخاطرة حوالي {round(ideal_risk,1)}% لكل صفقة."
            }
        finally:
            db.close()

smart_journal = SmartJournal()
