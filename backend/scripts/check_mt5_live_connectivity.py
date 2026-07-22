import os
import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path so backend package imports work.
ROOT = Path(__file__).resolve().parents[1].parents[0]
sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.services.mt5_service import MT5Service


def main():
    print('=== MT5 Live Connectivity Check ===')
    print('Using settings:')
    print('  MT5_LOGIN:', settings.MT5_LOGIN)
    print('  MT5_SERVER:', settings.MT5_SERVER)

    svc = MT5Service()
    try:
        result = svc.connect(
            account=settings.MT5_LOGIN,
            password=settings.MT5_PASSWORD,
            server=settings.MT5_SERVER,
        )
    except Exception as exc:
        print('\nConnection result: FAILED')
        print('Exception during connect:')
        traceback.print_exc()
        return

    print('\nConnection result:')
    print('  raw:', result)
    print('  simulator_mode:', svc.simulator_mode)
    print('  connected:', svc.connected)

    print('\nAttempting live price fetch for XAUUSD...')
    try:
        price = svc.get_price('XAUUSD')
    except Exception as exc:
        print('Failed to get price:')
        traceback.print_exc()
        price = {}

    if price:
        print('Price response:')
        for key in ('symbol', 'bid', 'ask', 'time', 'status', 'warning'):
            if key in price:
                print(f'  {key}: {price[key]}')
    else:
        print('Price response: empty or unavailable.')

    contract_size = None
    try:
        contract_size = svc._get_contract_size('XAUUSD')
    except Exception as exc:
        print('Failed to get contract size:')
        traceback.print_exc()

    print('\nMT5 trade contract size for XAUUSD:', contract_size)

    print('\nFinal assessment:')
    if svc.simulator_mode:
        print('  SYSTEM MODE: Simulator / Offline mode (no live MT5 feed).')
    elif not svc.connected:
        print('  SYSTEM MODE: Not connected to MT5; likely offline or no terminal available.')
    elif price and price.get('status') != 'simulated':
        print('  SYSTEM MODE: Live MT5 market data retrieved successfully.')
    else:
        print('  SYSTEM MODE: Data appears simulated or fallback pricing was used.')


if __name__ == '__main__':
    main()
