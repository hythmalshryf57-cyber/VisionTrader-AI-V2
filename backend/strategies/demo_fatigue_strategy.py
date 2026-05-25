# Demo strategy used for Strategy Fatigue test

def generate_signal(price, **kwargs):
    if price > kwargs.get('high', price):
        return 'SELL', price * 0.99
    if price < kwargs.get('low', price):
        return 'BUY', price * 1.01
    return 'NEUTRAL', None
