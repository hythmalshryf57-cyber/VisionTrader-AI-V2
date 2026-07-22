import os
import sys

# ensure project root on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.risk_calculator import RiskCalculator
from backend.services.mt5_service import MT5Service

# Parameters from user
account_balance = 10000.0
base_risk_percent = 1.0
confidence = 40
entry_price = 2350.00
stop_loss = 2340.00

rc = RiskCalculator()
mt5_service = MT5Service()
adjusted = rc.adjusted_risk(confidence, base_risk_percent)
# replicate TradeManager lot multiplier logic
if confidence >= 90:
    lot_multiplier = 1.0
elif confidence >= 60:
    lot_multiplier = 0.5
else:
    lot_multiplier = 0.25

trade_size = rc.calculate_position_size(
    account_balance=account_balance,
    entry_price=entry_price,
    stop_loss=stop_loss,
    risk_percent=adjusted,
)

position_size_before = trade_size.get('position_size', 0.0)
position_size_final = round(position_size_before * lot_multiplier, 6)
final_volume = mt5_service.normalize_volume('XAUUSD', position_size_final)

# Synthetic recent price data for swing and liquidity testing
price_history = [
    {'open': 2340.5, 'high': 2342.0, 'low': 2338.5, 'close': 2341.0},
    {'open': 2341.0, 'high': 2343.5, 'low': 2340.0, 'close': 2342.5},
    {'open': 2342.5, 'high': 2344.0, 'low': 2341.5, 'close': 2343.0},
    {'open': 2343.0, 'high': 2345.5, 'low': 2342.0, 'close': 2344.8},
    {'open': 2344.8, 'high': 2345.0, 'low': 2341.0, 'close': 2342.2},
    {'open': 2342.2, 'high': 2344.0, 'low': 2340.0, 'close': 2343.2},
    {'open': 2343.2, 'high': 2346.0, 'low': 2342.0, 'close': 2345.8},
    {'open': 2345.8, 'high': 2347.0, 'low': 2344.0, 'close': 2346.4},
    {'open': 2346.4, 'high': 2347.5, 'low': 2345.0, 'close': 2347.0},
    {'open': 2347.0, 'high': 2348.0, 'low': 2345.5, 'close': 2346.0},
    {'open': 2346.0, 'high': 2346.5, 'low': 2343.0, 'close': 2344.0},
    {'open': 2344.0, 'high': 2345.5, 'low': 2342.5, 'close': 2343.5},
    {'open': 2343.5, 'high': 2346.8, 'low': 2342.8, 'close': 2346.0},
    {'open': 2346.0, 'high': 2347.8, 'low': 2344.0, 'close': 2346.9},
    {'open': 2346.9, 'high': 2349.0, 'low': 2346.0, 'close': 2348.5},
    {'open': 2348.5, 'high': 2350.0, 'low': 2347.2, 'close': 2349.1},
    {'open': 2349.1, 'high': 2351.5, 'low': 2348.0, 'close': 2350.5},
    {'open': 2350.5, 'high': 2353.0, 'low': 2349.0, 'close': 2352.0},
    {'open': 2352.0, 'high': 2354.0, 'low': 2350.0, 'close': 2353.8},
    {'open': 2353.8, 'high': 2355.0, 'low': 2352.0, 'close': 2354.7},
    {'open': 2354.7, 'high': 2355.8, 'low': 2353.0, 'close': 2355.5},
    {'open': 2355.5, 'high': 2357.0, 'low': 2354.0, 'close': 2356.2},
    {'open': 2356.2, 'high': 2357.5, 'low': 2355.0, 'close': 2356.8},
    {'open': 2356.8, 'high': 2358.0, 'low': 2355.5, 'close': 2357.0},
    {'open': 2357.0, 'high': 2358.8, 'low': 2356.0, 'close': 2358.5},
    {'open': 2358.5, 'high': 2360.0, 'low': 2357.2, 'close': 2359.0},
    {'open': 2359.0, 'high': 2361.0, 'low': 2358.0, 'close': 2360.5},
    {'open': 2360.5, 'high': 2362.0, 'low': 2359.0, 'close': 2361.3},
    {'open': 2361.3, 'high': 2363.0, 'low': 2360.0, 'close': 2362.5},
    {'open': 2362.5, 'high': 2364.0, 'low': 2361.0, 'close': 2363.8},
    {'open': 2363.8, 'high': 2365.0, 'low': 2362.0, 'close': 2364.0},
    {'open': 2364.0, 'high': 2366.0, 'low': 2363.0, 'close': 2365.5},
    {'open': 2365.5, 'high': 2367.0, 'low': 2364.0, 'close': 2366.0},
    {'open': 2366.0, 'high': 2367.5, 'low': 2365.0, 'close': 2366.8},
    {'open': 2366.8, 'high': 2368.0, 'low': 2365.5, 'close': 2367.0},
    {'open': 2367.0, 'high': 2368.8, 'low': 2366.0, 'close': 2368.5},
    {'open': 2368.5, 'high': 2370.0, 'low': 2367.2, 'close': 2369.0},
    {'open': 2369.0, 'high': 2371.0, 'low': 2368.0, 'close': 2370.5},
    {'open': 2370.5, 'high': 2372.0, 'low': 2369.0, 'close': 2371.5},
    {'open': 2371.5, 'high': 2373.0, 'low': 2370.0, 'close': 2372.0},
    {'open': 2372.0, 'high': 2374.0, 'low': 2371.0, 'close': 2373.0},
    {'open': 2373.0, 'high': 2374.5, 'low': 2371.5, 'close': 2374.0},
    {'open': 2374.0, 'high': 2375.0, 'low': 2372.5, 'close': 2373.8},
    {'open': 2373.8, 'high': 2375.5, 'low': 2372.0, 'close': 2375.0},
    {'open': 2375.0, 'high': 2376.0, 'low': 2373.8, 'close': 2374.8},
    {'open': 2374.8, 'high': 2376.5, 'low': 2373.0, 'close': 2375.5},
    {'open': 2375.5, 'high': 2377.0, 'low': 2374.0, 'close': 2376.0},
    {'open': 2376.0, 'high': 2378.0, 'low': 2375.0, 'close': 2377.2},
    {'open': 2377.2, 'high': 2378.5, 'low': 2376.0, 'close': 2378.0},
    {'open': 2378.0, 'high': 2379.0, 'low': 2377.0, 'close': 2378.8},
]
liquidity_levels = [2355.0, 2360.0, 2365.0, 2370.0, 2375.0]

estimates = rc.estimate_tp_sl(
    entry_price=entry_price,
    recommendation='شراء',
    price_history=price_history,
    liquidity_levels=liquidity_levels,
)

print('Simulation for XAUUSD')
print('Account balance:', account_balance)
print('Base risk percent:', base_risk_percent)
print('Confidence:', confidence)
print('Entry price:', entry_price)
print('Stop loss:', stop_loss)
print('----')
print('adjusted_risk (percent):', adjusted)
print('lot_multiplier:', lot_multiplier)
print('position_size before multiplier:', position_size_before)
print('Final position_size (after multiplier):', position_size_final)
print('Final MT5 lot volume:', final_volume)
print('risk_amount:', trade_size.get('risk_amount'))
print('stop_distance:', trade_size.get('stop_distance'))
print('----')
print('estimated_stop_loss:', estimates['stop_loss'])
print('estimated_take_profit:', estimates['take_profit'])
print('volatility_estimate:', estimates['volatility_estimate'])
print('note:', estimates['note'])
