import requests
import base64
import urllib.parse
from typing import Optional, Dict, Any
from config import settings
import time
import logging
import json
import os
from threading import Lock

logger = logging.getLogger(__name__)


class TradingViewService:
    SCREENSHOT_PROVIDER = "https://image.thum.io/get/width/1200/crop/700/"
    GEMINI_ENDPOINT = getattr(settings, 'GEMINI_API_URL', 'https://api.gemini.com/v1/vision/analyze')
    STATS_FILE = os.path.join(os.path.dirname(__file__), 'provider_stats.json')
    _stats_lock = Lock()

    def __init__(self):
        self._load_stats()

    def _load_stats(self):
        try:
            with self._stats_lock:
                if os.path.exists(self.STATS_FILE):
                    with open(self.STATS_FILE, 'r', encoding='utf-8') as f:
                        self.provider_stats = json.load(f)
                else:
                    self.provider_stats = {
                        'gemini': {'calls': 0, 'success': 0, 'fail': 0, 'avg_latency_ms': 0, 'consecutive_failures': 0},
                        'deepseek': {'calls': 0, 'success': 0, 'fail': 0, 'avg_latency_ms': 0, 'consecutive_failures': 0},
                        'openrouter': {'calls': 0, 'success': 0, 'fail': 0, 'avg_latency_ms': 0, 'consecutive_failures': 0}
                    }
        except Exception:
            self.provider_stats = {}

    def _save_stats(self):
        try:
            with self._stats_lock:
                with open(self.STATS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.provider_stats, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception('Failed to save provider stats')

    def _update_stats(self, provider: str, latency_ms: float, success: bool):
        try:
            s = self.provider_stats.setdefault(provider, {'calls': 0, 'success': 0, 'fail': 0, 'avg_latency_ms': 0, 'consecutive_failures': 0})
            s['calls'] = s.get('calls', 0) + 1
            if success:
                s['success'] = s.get('success', 0) + 1
                s['consecutive_failures'] = 0
            else:
                s['fail'] = s.get('fail', 0) + 1
                s['consecutive_failures'] = s.get('consecutive_failures', 0) + 1
            prev_avg = s.get('avg_latency_ms', 0)
            calls = s['calls']
            s['avg_latency_ms'] = ((prev_avg * (calls - 1)) + latency_ms) / calls if calls else latency_ms
            # persist
            self._save_stats()
        except Exception:
            logger.exception('Failed to update provider stats')

    def fetch_chart_snapshot(self, url: str) -> bytes:
        if not url:
            raise ValueError("TradingView URL is required")
        snapshot_url = self.SCREENSHOT_PROVIDER + url
        response = requests.get(snapshot_url, timeout=25)
        response.raise_for_status()
        return response.content

    def _call_with_retries(self, method: str, url: str, headers: Dict[str, str], json_payload: Dict[str, Any], max_attempts: int = 2) -> Dict[str, Any]:
        # returns dict with keys: success(bool), status_code, latency_ms, response (json/text/None), error
        attempt = 0
        backoff = 1.0
        last_err = None
        while attempt < max_attempts:
            attempt += 1
            start = time.time()
            try:
                r = requests.post(url, json=json_payload, headers=headers, timeout=30)
                latency_ms = (time.time() - start) * 1000.0
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                if 200 <= r.status_code < 300:
                    return {'success': True, 'status_code': r.status_code, 'latency_ms': latency_ms, 'response': body}
                else:
                    last_err = f'HTTP {r.status_code} {getattr(r, "text", "")}'
                    logger.warning('Provider returned non-2xx: %s %s', url, r.status_code)
                    return {'success': False, 'status_code': r.status_code, 'latency_ms': latency_ms, 'response': body, 'error': last_err}
            except Exception as exc:
                latency_ms = (time.time() - start) * 1000.0
                last_err = str(exc)
                logger.warning('Request attempt %s failed for %s: %s', attempt, url, exc)
                if attempt < max_attempts:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return {'success': False, 'status_code': None, 'latency_ms': latency_ms, 'response': None, 'error': last_err}

    def _normalize_response(self, raw_response: Any, provider_name: str) -> Dict[str, Any]:
        # Normalize various provider outputs into unified structure
        out = {
            'provider': provider_name,
            'analysis': {
                'recommendation': '',
                'note': '',
                'confidence': 0,
                'pair': None,
                'timeframe': None,
                'levels': None,
                'support_resistance': None,
                'trend': None,
                'signals': None
            },
            'raw': raw_response
        }

        # If raw_response is a dict, search for common fields
        if isinstance(raw_response, dict):
            r = raw_response
            # nested under 'analysis' sometimes
            if 'analysis' in r and isinstance(r['analysis'], dict):
                r = r['analysis']

            # text fields
            note = r.get('note') or r.get('summary') or r.get('text') or r.get('description') or r.get('result')
            if isinstance(note, dict):
                # try common inner
                note = note.get('note') or note.get('summary') or str(note)
            out['analysis']['note'] = str(note) if note else ''

            # recommendation
            rec = r.get('recommendation') or r.get('action') or r.get('result')
            out['analysis']['recommendation'] = rec if rec else out['analysis']['note'][:120]

            # confidence
            conf = r.get('confidence') or r.get('score') or r.get('confidence_score')
            try:
                if conf is not None:
                    val = float(conf)
                    if val <= 1:
                        val = val * 100
                    out['analysis']['confidence'] = int(max(0, min(100, round(val))))
            except Exception:
                out['analysis']['confidence'] = 0

            # structural fields
            out['analysis']['pair'] = r.get('pair') or r.get('symbol') or r.get('market')
            out['analysis']['timeframe'] = r.get('timeframe') or r.get('tf')
            out['analysis']['levels'] = r.get('levels') or r.get('support_levels') or r.get('resistance_levels')
            out['analysis']['support_resistance'] = r.get('support_resistance') or r.get('sr')
            out['analysis']['trend'] = r.get('trend') or r.get('direction')
            out['analysis']['signals'] = r.get('signals') or r.get('indicators')

            return out

        # If raw_response is text
        if isinstance(raw_response, str):
            text = raw_response.strip()
            out['analysis']['note'] = text
            out['analysis']['recommendation'] = text[:120]
            out['analysis']['confidence'] = 0
            return out

        # Unknown type
        out['analysis']['note'] = 'لم يتم الحصول على تحليل مفصل من المزود.'
        out['analysis']['recommendation'] = 'محايد'
        out['analysis']['confidence'] = 0
        return out

    def analyze_with_gemini(self, image_bytes: bytes) -> Dict[str, Any]:
        # Prepare payload
        payload = {
            'image_base64': base64.b64encode(image_bytes).decode('utf-8'),
            'instructions': 'حلل لقطة شاشة TradingView وقدم توصية سوقية، مستويات دعم ومقاومة، واتجاه عام.'
        }

        providers = []
        # Determine preferred order dynamically based on stats
        stats = getattr(self, 'provider_stats', None) or {}
        # compute simple score = success_rate / (avg_latency_ms + 1)
        def score(p):
            s = stats.get(p, {})
            calls = s.get('calls', 0)
            success = s.get('success', 0)
            avg = s.get('avg_latency_ms', 0) or 1
            success_rate = (success / calls) if calls else 0
            penalty = 0
            if s.get('consecutive_failures', 0) >= 2:
                penalty = 0.5
            return (success_rate + 0.01) / (avg + 1) - penalty

        candidates = ['gemini', 'deepseek', 'openrouter']
        providers = sorted(candidates, key=lambda x: score(x), reverse=True)

        # Build endpoints/keys
        gem_key = getattr(settings, 'GEMINI_API_KEY', None)
        deepseek_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', None)

        # mapping provider -> (url, headers, payload)
        provider_calls = {
            'gemini': (f"{self.GEMINI_ENDPOINT}?key={gem_key}", {'Content-Type': 'application/json'}, payload) if gem_key else None,
            'deepseek': ('https://api.deepseek.ai/v1/vision/analyze', {'Authorization': f'Bearer {deepseek_key}', 'Content-Type': 'application/json'}, {'image_base64': payload['image_base64'], 'prompt': payload['instructions']}) if deepseek_key else None,
            'openrouter': ('https://api.openrouter.ai/v1/vision/analyze', {'Authorization': f'Bearer {openrouter_key}', 'Content-Type': 'application/json'}, {'image': payload['image_base64'], 'instructions': payload['instructions']}) if openrouter_key else None
        }

        fallback_note = 'Gemini/DeepSeek/OpenRouter غير متاحة أو فشلت. تم إرجاع تحليل احتياطي.'

        # iterate providers
        for prov in providers:
            call_info = provider_calls.get(prov)
            if not call_info:
                continue
            url, headers, body = call_info
            logger.debug('Attempting provider %s url=%s', prov, url)
            res = self._call_with_retries('POST', url, headers, body, max_attempts=2)
            latency = res.get('latency_ms', 0) or 0
            success = res.get('success', False)
            status = res.get('status_code')
            resp = res.get('response')
            # update stats
            self._update_stats(prov, latency, success)

            # logging metadata
            meta = {'provider_used': prov, 'provider_latency_ms': int(latency), 'provider_status_code': status, 'fallback_used': False}

            if success and resp is not None:
                normalized = self._normalize_response(resp, prov)
                # attach metadata for internal use
                normalized.update(meta)
                return normalized

            # provider failed -> continue to next
            logger.warning('Provider %s failed: %s', prov, res.get('error'))

        # all providers failed -> fallback
        fallback = {'analysis': {'recommendation': 'محايد', 'note': fallback_note, 'confidence': 0}, 'raw': None, 'provider': 'fallback', 'provider_used': None, 'provider_latency_ms': 0, 'provider_status_code': None, 'fallback_used': True}
        return fallback

    def fetch_and_analyze(self, url: str) -> Dict:
        image_bytes = self.fetch_chart_snapshot(url)
        return self.analyze_with_gemini(image_bytes)

    def detect_chart_details(self, image_bytes: bytes) -> Dict:
        payload = {
            'image_base64': base64.b64encode(image_bytes).decode('utf-8'),
            'instructions': 'حلل هذه الصورة للشارت واستخرج: الزوج التجاري (مثل XAU/USD, EUR/USD), الفريم الزمني (مثل 1H, 4H, Daily). أعد الإجابة بتنسيق JSON فقط.'
        }
        # Try providers in order
        providers = ['gemini', 'deepseek', 'openrouter']
        calls = {
            'gemini': (f"{self.GEMINI_ENDPOINT}?key={getattr(settings, 'GEMINI_API_KEY', None)}", {'Content-Type': 'application/json'}, payload),
            'deepseek': ('https://api.deepseek.ai/v1/vision/analyze', {'Authorization': f'Bearer {getattr(settings, "DEEPSEEK_API_KEY", None)}', 'Content-Type': 'application/json'}, {'image_base64': payload['image_base64'], 'prompt': payload['instructions']}),
            'openrouter': ('https://api.openrouter.ai/v1/vision/analyze', {'Authorization': f'Bearer {getattr(settings, "OPENROUTER_API_KEY", None)}', 'Content-Type': 'application/json'}, {'image': payload['image_base64'], 'instructions': payload['instructions']})
        }

        for prov in providers:
            call_info = calls.get(prov)
            if not call_info:
                continue
            url, headers, body = call_info
            res = self._call_with_retries('POST', url, headers, body, max_attempts=2)
            latency = res.get('latency_ms', 0) or 0
            success = res.get('success', False)
            status = res.get('status_code')
            resp = res.get('response')
            self._update_stats(prov, latency, success)
            if success and resp is not None:
                # try extract fields
                data = resp if isinstance(resp, dict) else {}
                pair = data.get('pair') or data.get('symbol') or data.get('market')
                timeframe = data.get('timeframe') or data.get('tf')
                confidence = data.get('confidence') or data.get('score') or 0
                try:
                    confidence = int(float(confidence))
                except Exception:
                    confidence = 0
                return {'pair': pair or 'UNKNOWN', 'timeframe': timeframe or 'UNKNOWN', 'confidence': confidence}

        return {'pair': 'UNKNOWN', 'timeframe': 'UNKNOWN', 'confidence': 0, 'note': 'لم يتمكن أي مزود من تحليل الصورة.'}


# Module-level instance for convenience (used by other services)
try:
    tradingview_service = TradingViewService()
except Exception:
    # If initialization fails, provide a fallback object with compatible methods
    class _FallbackTV:
        def get_price_from_twelvedata(self, symbol: str) -> Optional[float]:
            return None

        def get_symbol_price(self, symbol: str) -> Optional[float]:
            return None

        def fetch_chart_snapshot(self, url: str) -> bytes:
            raise RuntimeError('TradingViewService not initialized')

    tradingview_service = _FallbackTV()

    def get_price_from_twelvedata(self, symbol: str) -> Optional[float]:
        """Try to fetch a simple price from TwelveData API if configured. Returns None on failure."""
        key = getattr(settings, 'TWELVEDATA_API_KEY', None) or os.getenv('TWELVEDATA_API_KEY')
        if not key or not symbol:
            return None
        try:
            params = {"symbol": symbol, "format": "JSON", "apikey": key}
            r = requests.get("https://api.twelvedata.com/price", params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            price = data.get("price") or data.get("close")
            if price is None:
                return None
            return float(price)
        except Exception:
            return None

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Resolve a symbol price using available providers. Prefer TwelveData, fallback to Yahoo Finance."""
        if not symbol:
            return None

        # Try TwelveData first
        try:
            p = self.get_price_from_twelvedata(symbol)
            if p is not None:
                return p
        except Exception:
            pass

        # Fallback to Yahoo Finance quote endpoint
        try:
            q = urllib.parse.quote(symbol, safe='')
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={q}"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            body = resp.json()
            results = body.get("quoteResponse", {}).get("result", [])
            if not results:
                return None
            item = results[0]
            price = item.get("regularMarketPrice") or item.get("bid") or item.get("ask") or item.get("lastPrice")
            if price is None:
                return None
            return float(price)
        except Exception:
            return None