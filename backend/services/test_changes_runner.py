import traceback
import sys
import os


if __name__ == "__main__":
    # Ensure project root is on sys.path so `backend` package can be imported
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)
    # Also ensure backend/ is on sys.path because many modules use top-level imports like `from database import ...`
    backend_dir = os.path.abspath(os.path.join(proj_root, "backend"))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    try:
        # Provide minimal env vars expected by config/Settings during import
        os.environ.setdefault("SECRET_KEY", "test-secret")
        os.environ.setdefault("MASTER_ENCRYPTION_KEY", "test-master-key")
        # Indicate development mode so database module may fallback to SQLite for local tests
        os.environ.setdefault("ENV", "development")

        from backend.services import agent_manager, auto_scanner, mt5_service, controlled_deployer
        print("imports OK")

        am = agent_manager.AgentManager()
        print("agents:", len(am.agents))

        # Force DeepSeek and fallback to fail and ensure analyze returns neutral Arabic message
        ab = agent_manager.AgentBase("Test", "role")
        def bad_call(prompt):
            raise Exception("fail")
        ab._call_deepseek = bad_call
        ab._fallback = lambda prompt: (_ for _ in ()).throw(Exception("fallback fail"))
        res = ab.analyze({})
        print("ab.analyze:", res)

        mts = mt5_service.mt5_service
        print("mt5 connect:", mts.connect())
        print("mt5 account:", mts.get_account_info())

        asvc = auto_scanner.auto_scanner
        print("EURUSD market ref:", asvc._market_price_reference("EURUSD"))

        print("request_approval:", controlled_deployer.request_approval("s", {"sharpe_ratio":3.0, "win_rate_pct":50}, "new", None))

    except Exception as e:
        print("ERROR during test:", e)
        traceback.print_exc()
    else:
        print("TESTS OK")
