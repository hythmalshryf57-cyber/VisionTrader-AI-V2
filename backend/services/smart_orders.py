import datetime

class SmartOrdersService:
    def __init__(self):
        self.pending_orders = []

    def create_zone_order(self, market, zone_start, zone_end, total_lot):
        """
        Distributes lot across the zone.
        """
        orders = [
            {"price": zone_start, "lot": total_lot * 0.3},
            {"price": (zone_start + zone_end) / 2, "lot": total_lot * 0.3},
            {"price": zone_end, "lot": total_lot * 0.4}
        ]
        self.pending_orders.append({"type": "Zone", "market": market, "orders": orders})
        return orders

    def create_time_conditional_order(self, market, price, expiry_time):
        """
        Order that cancels if not triggered by expiry.
        """
        order = {
            "type": "TimeConditional",
            "market": market,
            "price": price,
            "expiry": expiry_time,
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        self.pending_orders.append(order)
        return order

    def create_ghost_order(self, market, price, side):
        """
        Stored server-side, executed as market order when price touched.
        """
        order = {
            "type": "Ghost",
            "market": market,
            "target_price": price,
            "side": side
        }
        self.pending_orders.append(order)
        return order

    def check_and_correct_orders(self, current_market_structure):
        """
        Self-correcting logic: if structure changes, cancel or adjust.
        """
        if current_market_structure == "Bearish" and any(o['type'] == "Zone" for o in self.pending_orders):
            # Example: Cancel buy zones if market turns bearish
            self.pending_orders = [o for o in self.pending_orders if o['type'] != "Zone"]
            return "Cancelled bullish zone orders due to market structure change."
        return "No corrections needed."
