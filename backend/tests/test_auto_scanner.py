import unittest

from services.auto_scanner import AutoScanner, MARKETS


class TestAutoScanner(unittest.TestCase):
    def test_market_list_contains_18_markets(self):
        self.assertEqual(len(MARKETS), 18)
        expected = {
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "EURGBP",
            "XAUUSD", "XAGUSD",
            "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD",
            "US30", "US100", "SPX500"
        }
        self.assertEqual(set(MARKETS), expected)

    def test_tier_market_coverage(self):
        scanner = AutoScanner()
        all_tier_markets = set(scanner.TIER1_MARKETS + scanner.TIER2_MARKETS + scanner.TIER3_MARKETS)
        self.assertEqual(all_tier_markets, set(MARKETS))
        self.assertEqual(len(scanner.TIER1_MARKETS), 4)
        self.assertEqual(len(scanner.TIER2_MARKETS), 9)
        self.assertEqual(len(scanner.TIER3_MARKETS), 5)

    def test_binance_symbol_mapping(self):
        scanner = AutoScanner()
        self.assertEqual(scanner._map_binance_symbol("BTCUSD"), "BTCUSDT")
        self.assertEqual(scanner._map_binance_symbol("ETHUSD"), "ETHUSDT")
        self.assertEqual(scanner._map_binance_symbol("SOLUSD"), "SOLUSDT")
        self.assertEqual(scanner._map_binance_symbol("BNBUSD"), "BNBUSDT")
        self.assertEqual(scanner._map_binance_symbol("XRPUSD"), "XRPUSDT")
        self.assertEqual(scanner._map_binance_symbol("EURUSD"), "EURUSD")


if __name__ == "__main__":
    unittest.main()
