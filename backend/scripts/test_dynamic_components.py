import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.self_healing import OmniSelfHealing
from services.code_review_agent import CodeReviewAgent
from services.news_adapter import NewsAdapter, NewsItem, ImpactLevel


def test_self_healing():
    print('\n=== Self-Healing Dynamic Test ===')
    healer = OmniSelfHealing()
    error_log = 'TimeoutError: Connection pool failed to re-establish to database after 30s'

    start1 = time.perf_counter()
    result1 = healer.heal_any(error_log, domain='backend')
    elapsed1 = time.perf_counter() - start1
    print(f'First fix result: {result1} | duration={elapsed1:.3f}s')

    start2 = time.perf_counter()
    result2 = healer.heal_any(error_log, domain='backend')
    elapsed2 = time.perf_counter() - start2
    print(f'Second fix result: {result2} | duration={elapsed2:.3f}s')
    print('Faster on repeat:', elapsed2 < elapsed1)


def test_code_review_agent():
    print('\n=== Code Review Agent Dynamic Test ===')
    memory_file = Path(__file__).resolve().parent.parent / '_evolved' / 'memory' / 'code_review_agent_memory.json'
    if memory_file.exists():
        memory_file.unlink()
    agent = CodeReviewAgent()
    scratch = Path(__file__).resolve().parent.parent / 'scratch' / 'dynamic_review_example.py'
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(
        'import os\nimport time\n\ndef generate_signal(data):\n    time.sleep(0.1)\n    return \'Buy\'\n',
        encoding='utf-8',
    )

    report1 = agent.review(str(scratch))
    print('First review:', report1)

    report2 = agent.review(str(scratch))
    print('Second review:', report2)

    scratch.unlink()


def test_news_adapter():
    print('\n=== News Adapter Dynamic Test ===')
    adapter = NewsAdapter()
    news = NewsItem(
        title='FED signals possible rate cut while inflation worries persist',
        source='GoogleNews',
        published='2026-05-23T12:00:00Z',
        url='https://example.com/news',
    )

    analyzed = adapter.analyze_impact(news)
    print('Initial analysis:', analyzed.impact, analyzed.confidence, analyzed.keywords)

    feedback = adapter.report_actual_news_impact(
        analyzed,
        price_before=100.0,
        price_after=98.3,
        market='USD',
    )
    print('Recorded actual impact:', feedback)

    analyzed_again = adapter.analyze_impact(news)
    print('Re-analysis after learning:', analyzed_again.impact, analyzed_again.confidence, analyzed_again.keywords)


if __name__ == '__main__':
    test_self_healing()
    test_code_review_agent()
    test_news_adapter()
