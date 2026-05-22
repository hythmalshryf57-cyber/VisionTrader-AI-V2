"""Mock failing strategy"""
def generate_signal(price, **kwargs):
    return 'BUY', price * 0.99
