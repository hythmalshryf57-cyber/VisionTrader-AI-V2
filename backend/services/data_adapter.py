import logging
import math
import re
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

KNOWN_PATTERN_KEYWORDS = [
    'hammer', 'shooting star', 'engulfing', 'doji', 'morning star', 'evening star',
    'head and shoulders', 'double top', 'double bottom', 'trendline', 'channel',
    'flag', 'triangle', 'rectangle', 'wedge', 'cup and handle', 'breakout', 'reversal'
]

TREND_KEYWORDS = {
    'uptrend': 'صاعد',
    'bullish': 'صاعد',
    'downtrend': 'هابط',
    'bearish': 'هابط',
    'sideways': 'محايد',
    'range': 'محايد',
    'consolidation': 'محايد'
}

LEVEL_KEYWORDS = ['support', 'resistance', 'pivot', 'level']


class DataAdapter:
    def normalize_input(self, visual_context: List[Dict[str, Any]], market: str) -> Dict[str, Any]:
        chart_data = {
            'opens': [],
            'highs': [],
            'lows': [],
            'closes': [],
            'volumes': [],
            'timestamps': [],
            'support_levels': [],
            'resistance_levels': [],
            'swing_highs': [],
            'swing_lows': [],
            'candle_patterns': [],
            'trend': None,
            'trend_strength': None,
            'source_types': [],
            'raw_text': [],
            'image_paths': []
        }
        issues: List[str] = []

        for entry in visual_context:
            if not isinstance(entry, dict):
                continue
            if 'source' in entry:
                chart_data['source_types'].append(entry['source'])
            if 'images' in entry and entry['images']:
                chart_data['source_types'].append('image')
            if 'image_path' in entry and entry['image_path']:
                chart_data['image_paths'].append(entry['image_path'])
            if 'visual_description' in entry and entry['visual_description']:
                chart_data['raw_text'].append(entry['visual_description'])
            if 'description' in entry and entry['description']:
                chart_data['raw_text'].append(entry['description'])
            if 'text' in entry and entry['text']:
                chart_data['raw_text'].append(entry['text'])

            if 'ohlcv' in entry and isinstance(entry['ohlcv'], dict):
                self._merge_series(chart_data, entry['ohlcv'])
                chart_data['source_types'].append('ohlcv')
            if 'chart_data' in entry and isinstance(entry['chart_data'], dict):
                self._merge_series(chart_data, entry['chart_data'])
                chart_data['source_types'].append('chart_data')
            if 'candles' in entry and isinstance(entry['candles'], list):
                self._merge_candles(chart_data, entry['candles'])
                chart_data['source_types'].append('candles')
            if 'social' in entry and isinstance(entry['social'], dict):
                chart_data['raw_text'].append(str(entry['social']))
                chart_data['source_types'].append('social')

        if chart_data['raw_text']:
            text = ' '.join(chart_data['raw_text'])
            self._extract_levels_from_text(chart_data, text)
            self._extract_patterns_from_text(chart_data, text)
            self._extract_trend_from_text(chart_data, text)
            self._parse_ohlcv_from_text(chart_data, text)

        self._infer_missing_series(chart_data)
        self._populate_timestamp_series(chart_data)
        self._compute_swings(chart_data)
        self._normalize_levels(chart_data)

        quality_score = self._evaluate_quality(chart_data)
        valid = len(chart_data['closes']) >= 2 and quality_score >= 0.3

        if not valid:
            issues.append('Data adapter could not build a valid OHLCV structure from the provided input.')

        return {
            'chart_data': chart_data,
            'valid': valid,
            'quality_score': quality_score,
            'issues': issues,
            'market': market,
            'raw_context': visual_context,
            'generated_at': datetime.utcnow().isoformat()
        }

    def _merge_series(self, chart_data: Dict[str, Any], source: Dict[str, Any]) -> None:
        for key in ('opens', 'highs', 'lows', 'closes', 'volumes', 'timestamps'):
            if key in source and isinstance(source[key], list):
                if len(source[key]) > len(chart_data[key]):
                    chart_data[key] = source[key][:]

    def _merge_candles(self, chart_data: Dict[str, Any], candles: List[Dict[str, Any]]) -> None:
        opens, highs, lows, closes, volumes, timestamps = [], [], [], [], [], []
        for candle in candles:
            if not isinstance(candle, dict):
                continue
            try:
                opens.append(float(candle.get('open', candle.get('o', 0.0))))
                highs.append(float(candle.get('high', candle.get('h', 0.0))))
                lows.append(float(candle.get('low', candle.get('l', 0.0))))
                closes.append(float(candle.get('close', candle.get('c', 0.0))))
                volumes.append(float(candle.get('volume', candle.get('v', 0.0))))
                timestamps.append(candle.get('timestamp') or candle.get('time') or candle.get('date'))
            except (TypeError, ValueError):
                continue
        if len(closes) >= 2 and len(closes) > len(chart_data['closes']):
            chart_data['opens'] = opens
            chart_data['highs'] = highs
            chart_data['lows'] = lows
            chart_data['closes'] = closes
            chart_data['volumes'] = volumes
            chart_data['timestamps'] = timestamps

    def _extract_levels_from_text(self, chart_data: Dict[str, Any], text: str) -> None:
        lowered = text.lower()
        for keyword in LEVEL_KEYWORDS:
            pattern = re.compile(rf'{keyword}s?\s*(?:at|near|around|around)?\s*([0-9]+(?:\.[0-9]+)?)', re.I)
            for match in pattern.finditer(lowered):
                value = float(match.group(1))
                if 'support' in keyword:
                    chart_data['support_levels'].append(value)
                else:
                    chart_data['resistance_levels'].append(value)
        numbers = self._extract_numeric_values(text)
        if len(numbers) >= 2 and not chart_data['support_levels'] and not chart_data['resistance_levels']:
            chart_data['support_levels'] = sorted(numbers[:2])
            chart_data['resistance_levels'] = sorted(numbers[-2:], reverse=True)

    def _extract_patterns_from_text(self, chart_data: Dict[str, Any], text: str) -> None:
        lowered = text.lower()
        patterns = []
        for keyword in KNOWN_PATTERN_KEYWORDS:
            if keyword in lowered:
                patterns.append(keyword)
        chart_data['candle_patterns'] = patterns

    def _extract_trend_from_text(self, chart_data: Dict[str, Any], text: str) -> None:
        lowered = text.lower()
        for token, value in TREND_KEYWORDS.items():
            if token in lowered:
                chart_data['trend'] = value
                break

    def _parse_ohlcv_from_text(self, chart_data: Dict[str, Any], text: str) -> None:
        bars = []
        patterns = [
            r'open\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)',
            r'high\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)',
            r'low\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)',
            r'close\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)',
            r'volume\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)'
        ]
        o, h, l, c, v = [], [], [], [], []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                try:
                    value = float(match.group(1))
                except ValueError:
                    continue
                if 'open' in match.re.pattern:
                    o.append(value)
                elif 'high' in match.re.pattern:
                    h.append(value)
                elif 'low' in match.re.pattern:
                    l.append(value)
                elif 'close' in match.re.pattern:
                    c.append(value)
                elif 'volume' in match.re.pattern:
                    v.append(value)
        if c and not chart_data['closes']:
            chart_data['opens'] = o or [c[0]]
            chart_data['highs'] = h or c[:]
            chart_data['lows'] = l or c[:]
            chart_data['closes'] = c
            chart_data['volumes'] = v or [0.0] * len(c)

    def _infer_missing_series(self, chart_data: Dict[str, Any]) -> None:
        closes = chart_data['closes']
        if closes and not chart_data['opens']:
            chart_data['opens'] = [closes[0]] + closes[:-1]
        if closes and not chart_data['highs']:
            chart_data['highs'] = [max(cl, op) for cl, op in zip(closes, chart_data['opens'])]
        if closes and not chart_data['lows']:
            chart_data['lows'] = [min(cl, op) for cl, op in zip(closes, chart_data['opens'])]
        if closes and not chart_data['volumes']:
            chart_data['volumes'] = [0.0] * len(closes)

        lengths = [len(chart_data[key]) for key in ('opens', 'highs', 'lows', 'closes', 'volumes')]
        if len(set(lengths)) == 1 and lengths[0] >= 2:
            return
        if chart_data['closes']:
            size = len(chart_data['closes'])
            chart_data['opens'] = chart_data['opens'][:size] + [chart_data['closes'][0]] * max(0, size - len(chart_data['opens']))
            chart_data['highs'] = chart_data['highs'][:size] + chart_data['closes'][:] if len(chart_data['highs']) < size else chart_data['highs'][:size]
            chart_data['lows'] = chart_data['lows'][:size] + chart_data['closes'][:] if len(chart_data['lows']) < size else chart_data['lows'][:size]
            chart_data['volumes'] = chart_data['volumes'][:size] + [0.0] * max(0, size - len(chart_data['volumes']))

    def _populate_timestamp_series(self, chart_data: Dict[str, Any]) -> None:
        if chart_data['timestamps'] and len(chart_data['timestamps']) == len(chart_data['closes']):
            return
        base = datetime.utcnow()
        interval = timedelta(minutes=1)
        if len(chart_data['closes']) >= 60:
            interval = timedelta(minutes=5)
        chart_data['timestamps'] = [(base - interval * (len(chart_data['closes']) - i - 1)).isoformat() for i in range(len(chart_data['closes']))]

    def _compute_swings(self, chart_data: Dict[str, Any]) -> None:
        closes = chart_data['closes']
        highs = chart_data['highs']
        lows = chart_data['lows']
        if len(closes) < 3:
            return
        swing_highs, swing_lows = [], []
        for i in range(1, len(closes) - 1):
            if closes[i] > closes[i - 1] and closes[i] > closes[i + 1]:
                swing_highs.append({'index': i, 'price': closes[i], 'time': chart_data['timestamps'][i] if i < len(chart_data['timestamps']) else None})
            if closes[i] < closes[i - 1] and closes[i] < closes[i + 1]:
                swing_lows.append({'index': i, 'price': closes[i], 'time': chart_data['timestamps'][i] if i < len(chart_data['timestamps']) else None})
        chart_data['swing_highs'] = swing_highs
        chart_data['swing_lows'] = swing_lows

    def _normalize_levels(self, chart_data: Dict[str, Any]) -> None:
        chart_data['support_levels'] = sorted(set(chart_data['support_levels']))[:5]
        chart_data['resistance_levels'] = sorted(set(chart_data['resistance_levels']), reverse=True)[:5]

    def _evaluate_quality(self, chart_data: Dict[str, Any]) -> float:
        base = 0.0
        if len(chart_data['closes']) >= 10:
            base += 0.5
        elif len(chart_data['closes']) >= 3:
            base += 0.2
        if chart_data['source_types']:
            base += 0.2
        if chart_data['support_levels'] or chart_data['resistance_levels'] or chart_data['candle_patterns'] or chart_data['trend']:
            base += 0.2
        return min(1.0, base)

    def _extract_numeric_values(self, text: str) -> List[float]:
        values = []
        for match in re.finditer(r'([0-9]+(?:\.[0-9]+)?)', text):
            try:
                values.append(float(match.group(1)))
            except ValueError:
                continue
        return values
