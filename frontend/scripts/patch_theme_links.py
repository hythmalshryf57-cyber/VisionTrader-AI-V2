from pathlib import Path
files = [
    'frontend/dashboard.html', 'frontend/journal.html', 'frontend/daily-report.html', 'frontend/history.html',
    'frontend/calendar.html', 'frontend/heatmap.html', 'frontend/academy.html', 'frontend/service-health.html',
    'frontend/realtime.html', 'frontend/api-docs.html', 'frontend/price-alerts.html', 'frontend/tv-chart.html',
    'frontend/strategy_factory.html', 'frontend/strategy-battle.html', 'frontend/evolution.html',
    'frontend/admin-engine.html', 'frontend/admin.html', 'frontend/settings.html', 'frontend/backtest.html'
]
link = '    <link rel="stylesheet" href="css/upload-theme.css">\n'
for file in files:
    path = Path(file)
    if not path.exists():
        print('MISSING', file)
        continue
    text = path.read_text(encoding='utf-8')
    if 'href="css/upload-theme.css"' in text:
        print('SKIP', file)
        continue
    if 'href="css/style.css"' in text:
        text = text.replace('href="css/style.css">', 'href="css/style.css">\n' + link, 1)
        path.write_text(text, encoding='utf-8')
        print('PATCH style', file)
        continue
    if '</head>' in text:
        text = text.replace('</head>', link + '</head>', 1)
        path.write_text(text, encoding='utf-8')
        print('PATCH head', file)
        continue
    print('NO CHANGE', file)
