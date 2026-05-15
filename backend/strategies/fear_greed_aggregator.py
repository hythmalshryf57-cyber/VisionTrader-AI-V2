"""
═══════════════════════════════════════════════════════════════════════════════
FEAR & GREED AGGREGATOR - مجمع مؤشرات الخوف والطمع
المدرسة الموحدة: تجميع كل مصادر الخوف والطمع في مؤشر واحد
═══════════════════════════════════════════════════════════════════════════════

هذا ليس استراتيجية مستقلة. هذا "مجمع" (Aggregator).

يجمع البيانات من:
1. Social Sentiment Strategy (مشاعر حقيقية من Twitter/Reddit)
2. Psychological Engineering Strategy (مشاعر ضمنية من السعر)
3. Regime Detection Strategy (حالة السوق)

ويقدم:
- مؤشر خوف وطمع موحد (Weighted Fear & Greed Index)
- إشارة Contrarian ذكية (عكس القطيع مع تأكيد)
- تحذير من تطرف المشاعر

الاستخدام:
- في Voting Engine: استخدم F&G Index كمرشح إضافي
- ليس له توصية مستقلة
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class UnifiedFearGreedIndex:
    """مؤشر خوف وطمع موحد من كل المصادر"""
    unified_index: float  # 0-100
    social_sentiment_fg: Optional[float]  # من Social Sentiment
    psychological_fg: Optional[float]  # من Psychological Engineering
    regime_bias: Optional[float]  # من Regime Detection (0=خوف, 100=طمع)
    weighted_confidence: float  # ثقة المؤشر الموحد
    sources_used: List[str]
    contrarian_signal: str  # 'buy', 'sell', 'none'
    contrarian_strength: float
    warning: str


class FearGreedAggregator:
    """
    مجمع مؤشرات الخوف والطمع من كل الاستراتيجيات.
    
    هذا ليس استراتيجية NLP. هذا Aggregator.
    """
    
    def __init__(self):
        self.fg_history = deque(maxlen=100)
    
    def aggregate(self, social_sentiment_result: Dict = None,
                  psychological_result: Dict = None,
                  regime_result: Dict = None) -> UnifiedFearGreedIndex:
        """
        تجميع كل مصادر الخوف والطمع في مؤشر واحد
        """
        sources_used = []
        fg_values = []
        weights = []
        
        # 1. من Social Sentiment (وزن 40% - بيانات حقيقية)
        social_fg = None
        if social_sentiment_result:
            try:
                sent_data = social_sentiment_result.get('sentiment_data', {})
                if sent_data and 'sentiment_score' in sent_data:
                    score = sent_data['sentiment_score']
                    if hasattr(score, 'fear_greed_index'):
                        social_fg = score.fear_greed_index
                    elif hasattr(score, 'overall_sentiment'):
                        social_fg = (score.overall_sentiment + 1) * 50
                
                if social_fg is not None:
                    fg_values.append(social_fg)
                    weights.append(0.4)
                    sources_used.append('social_sentiment')
            except Exception as e:
                logger.debug(f"تعذر استخراج Social F&G: {e}")
        
        # 2. من Psychological Engineering (وزن 35% - ضمني + API)
        psych_fg = None
        if psychological_result:
            try:
                emotion_data = psychological_result.get('emotion_data', {})
                if emotion_data and 'emotion' in emotion_data:
                    emotion = emotion_data['emotion']
                    if hasattr(emotion, 'greed_index') and hasattr(emotion, 'fear_index'):
                        # تحويل greed/fear إلى F&G
                        psych_fg = emotion.greed_index * 50 + (1 - emotion.fear_index) * 50
                    elif hasattr(emotion, 'fused_sentiment'):
                        psych_fg = (emotion.fused_sentiment + 1) * 50
                
                if psych_fg is not None:
                    fg_values.append(psych_fg)
                    weights.append(0.35)
                    sources_used.append('psychological')
            except Exception as e:
                logger.debug(f"تعذر استخراج Psychological F&G: {e}")
        
        # 3. من Regime Detection (وزن 25% - سياق السوق)
        regime_bias = None
        if regime_result:
            try:
                regime_data = regime_result.get('regime_data', {})
                if regime_data and 'regime' in regime_data:
                    regime = regime_data['regime']
                    if hasattr(regime, 'regime_type'):
                        rt = regime.regime_type
                        # تحويل النظام إلى F&G
                        if hasattr(rt, 'value'):
                            rt_val = rt.value
                        else:
                            rt_val = str(rt)
                        
                        if 'BULL' in rt_val.upper():
                            regime_bias = 75.0
                        elif 'BEAR' in rt_val.upper():
                            regime_bias = 25.0
                        elif 'RANGE' in rt_val.upper():
                            regime_bias = 50.0
                        elif 'ACCUMULATION' in rt_val.upper():
                            regime_bias = 35.0
                        elif 'DISTRIBUTION' in rt_val.upper():
                            regime_bias = 65.0
                        else:
                            regime_bias = 50.0
                
                if regime_bias is not None:
                    fg_values.append(regime_bias)
                    weights.append(0.25)
                    sources_used.append('regime')
            except Exception as e:
                logger.debug(f"تعذر استخراج Regime F&G: {e}")
        
        # حساب المؤشر الموحد
        if fg_values:
            total_weight = sum(weights)
            if total_weight > 0:
                unified = sum(v * w for v, w in zip(fg_values, weights)) / total_weight
            else:
                unified = 50.0
            
            confidence = min(1.0, len(sources_used) / 3 + 0.3)
        else:
            unified = 50.0
            confidence = 0.1
        
        # إشارة Contrarian
        contrarian_signal = 'none'
        contrarian_strength = 0.0
        
        if unified < 20 and len(sources_used) >= 2:
            contrarian_signal = 'buy'
            contrarian_strength = min(1.0, (20 - unified) / 20)
        elif unified > 80 and len(sources_used) >= 2:
            contrarian_signal = 'sell'
            contrarian_strength = min(1.0, (unified - 80) / 20)
        
        # تحذير
        warning = ""
        if len(sources_used) < 2:
            warning = "⚠️ بيانات محدودة - مؤشر أقل موثوقية"
        elif unified < 15:
            warning = "خوف شديد جداً - فرصة شراء نادرة"
        elif unified > 85:
            warning = "طمع شديد جداً - خطر بيع نادر"
        
        # تحديث التاريخ
        self.fg_history.append(unified)
        
        return UnifiedFearGreedIndex(
            unified_index=unified,
            social_sentiment_fg=social_fg,
            psychological_fg=psych_fg,
            regime_bias=regime_bias,
            weighted_confidence=confidence,
            sources_used=sources_used,
            contrarian_signal=contrarian_signal,
            contrarian_strength=contrarian_strength,
            warning=warning,
        )
    
    def get_filter_multiplier(self, unified_fg: float) -> float:
        """
        يحول F&G Index إلى معامل مرشح للاستراتيجيات الأخرى
        
        خوف شديد (0-20): تضخيم إشارات الشراء (1.3x)، تضعيف البيع (0.7x)
        طمع شديد (80-100): تضخيم إشارات البيع (1.3x)، تضعيف الشراء (0.7x)
        محايد (40-60): لا تأثير (1.0x)
        """
        if unified_fg < 20:
            return 1.3  # تضخيم الشراء
        elif unified_fg < 40:
            return 1.1
        elif unified_fg < 60:
            return 1.0
        elif unified_fg < 80:
            return 0.9
        else:
            return 0.7  # تضعيف الشراء (تضخيم البيع = 1.3)
    
    def analyze(self, chart_data: Dict) -> Dict:
        """
        تحليل موحد (للاستخدام في Voting Engine)
        """
        # هذا المجمع لا يحلل البيانات مباشرة
        # بل يستخدم نتائج الاستراتيجيات الأخرى
        
        social_result = chart_data.get('social_sentiment_result')
        psych_result = chart_data.get('psychological_result')
        regime_result = chart_data.get('regime_result')
        
        fg_index = self.aggregate(social_result, psych_result, regime_result)
        
        filter_mult = self.get_filter_multiplier(fg_index.unified_index)
        
        return {
            "recommendation": "مرشح",  # ليس توصية مستقلة
            "confidence": int(fg_index.weighted_confidence * 100),
            "reason": f"F&G موحد: {fg_index.unified_index:.0f} | " + \
                      f"مصادر: {', '.join(fg_index.sources_used)} | " + \
                      f"مرشح: {filter_mult:.2f}x",
            "fear_greed_index": fg_index,
            "filter_multiplier": filter_mult,
            "contrarian_signal": fg_index.contrarian_signal,
            "warning": fg_index.warning,
        }


def create_nlp_sentiment_strategy():
    """
    إنشاء مجمع الخوف والطمع الموحد
    
    ملاحظة: هذا ليس استراتيجية NLP Sentiment.
    هذا Fear & Greed Aggregator.
    """
    return FearGreedAggregator()