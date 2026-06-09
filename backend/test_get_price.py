import os, json
# Minimal env to allow config initialization
os.environ.setdefault('SECRET_KEY', 'A'*32)
os.environ.setdefault('MASTER_ENCRYPTION_KEY', 'B'*32)
os.environ.setdefault('ADMIN_EMAIL', 'admin@example.com')
os.environ.setdefault('ADMIN_PASSWORD', 'adminpass')
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 'dummy_token')

from main import get_market_price

if __name__ == '__main__':
    print(json.dumps(get_market_price('XAUUSD'), ensure_ascii=False))
