import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.shadow_trader import ShadowTrader, _load_payloads

if __name__ == '__main__':
    st = ShadowTrader(user_id=1)
    rec1 = {'market':'EURUSD','direction':'buy','entry_price':1.1000,'price_history':[1.1000,1.1015,1.1020]}
    rec2 = {'market':'EURUSD','direction':'buy','entry_price':1.2000,'price_history':[1.2000,1.1980,1.1950]}

    t1 = st.create_shadow_recommendation(rec1)
    t2 = st.create_shadow_recommendation(rec2)
    print('Created shadow trades:', t1.id, t2.id)

    updated = st.track_shadow_performance()
    print('Tracked and updated trade ids:', updated)

    stats = st.get_shadow_stats()
    print('Stats:', stats)

    # inspect payloads file
    payloads = _load_payloads()
    print('Payload keys:', list(payloads.keys())[-5:])
