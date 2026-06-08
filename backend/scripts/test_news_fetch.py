from importlib import import_module
import sys
sys.path.insert(0, '..')
try:
    mod = import_module('backend.services.news_adapter')
    adapter = getattr(mod, 'news_adapter', None)
    if adapter is None:
        adapter = mod.NewsAdapter()
    news = adapter._fetch_all_news()
    print('Fetched', len(news), 'items')
    for n in news[:10]:
        print('-', n.source, n.published, (n.title or '')[:120])
except Exception as e:
    print('ERROR', e)
