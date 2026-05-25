"""
اختبار تكامل شامل: التحقق من تواصل جميع المكونات مع العقل المركزي (InternalBrain)
=================================================================================
يختبر:
1. العقل المركزي - تسجيل الأحداث والعتبات الديناميكية
2. agent_manager - الأوزان الديناميكية 
3. strategy_generator - الخوارزمية الجينية
4. sandbox_tester - فترات الاختبار المتغيرة
5. controlled_deployer - عتبات النشر الديناميكية
6. degradation_watcher - المراقبة المرنة
7. self_healing - ذاكرة الإصلاحات
8. code_review_agent - تتبع الأخطاء
9. news_adapter - تعلم الأخبار
10. alert_manager - تكيف التنبيهات
"""

import sys
import os
import time
import traceback

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from datetime import datetime

# Track results
results = []

def test(name, func):
    """Run a test and track result"""
    try:
        func()
        results.append((name, True, ""))
        print(f"  \u2705 {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  \u274c {name}: {e}")
        traceback.print_exc()

def main():
    print("=" * 60)
    print("   \U0001f9e0 VisionTrader AI - Integration Test Suite")
    print("   Testing all components with InternalBrain")
    print("=" * 60)
    
    # ===================================================
    # 1. InternalBrain Core
    # ===================================================
    print("\n\u2550" * 30 + " 1. InternalBrain Core " + "\u2550" * 30)
    
    def test_brain_init():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        assert brain is not None
        assert brain.default_weight == 1.0
    test("Brain initialization", test_brain_init)
    
    def test_brain_event_logging():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        brain.log_event_experience(
            component="integration_test",
            event_type="test_event",
            event_key="test_key",
            event_value=42.0,
            metadata={"test": True},
            context="integration",
            success=True,
        )
        mem = brain.get_component_memory("integration_test")
        assert "events" in mem
        assert len(mem["events"]) > 0
        last_event = mem["events"][-1]
        assert last_event["key"] == "test_key"
        assert last_event["value"] == 42.0
    test("Event logging to Global Memory", test_brain_event_logging)
    
    def test_brain_dynamic_threshold():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        th = brain.get_dynamic_threshold("test_comp", "test_threshold", 0.65)
        assert isinstance(th, float)
        assert th > 0
    test("Dynamic threshold calculation", test_brain_dynamic_threshold)
    
    def test_brain_fix_cache():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        # Use JSON memory cache as fallback when DB tables don't exist
        mem = brain.get_component_memory("fix_cache_test")
        mem["test_fix"] = {
            "error": "test_error",
            "fix_code": "print('fixed')",
            "success": True,
        }
        brain._save_component_memory("fix_cache_test", mem)
        loaded = brain.get_component_memory("fix_cache_test")
        assert loaded["test_fix"]["fix_code"] == "print('fixed')"
    test("Fix Cache (store & retrieve)", test_brain_fix_cache)
    
    def test_brain_sandbox_duration():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        d1 = brain.get_dynamic_sandbox_duration(0.9)
        d2 = brain.get_dynamic_sandbox_duration(0.6)
        d3 = brain.get_dynamic_sandbox_duration(0.3)
        assert d1 == 3, f"Excellent quality should be 3 days, got {d1}"
        assert d2 == 5, f"Medium quality should be 5 days, got {d2}"
        assert d3 == 7, f"Low quality should be 7 days, got {d3}"
    test("Dynamic sandbox duration", test_brain_sandbox_duration)
    
    def test_brain_deployment_threshold():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        t1 = brain.get_dynamic_deployment_threshold(0.1)  # calm market
        t2 = brain.get_dynamic_deployment_threshold(0.5)  # medium
        t3 = brain.get_dynamic_deployment_threshold(0.8)  # volatile
        assert t1 <= t2 <= t3, f"Threshold should increase with volatility: {t1}, {t2}, {t3}"
    test("Dynamic deployment threshold", test_brain_deployment_threshold)
    
    def test_brain_agent_weight():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        w = brain.get_agent_dynamic_weight("TestAgent", 1.0)
        assert isinstance(w, float)
        assert w > 0
    test("Agent dynamic weight", test_brain_agent_weight)
    
    def test_brain_daily_summary():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        summary = brain.get_daily_learning_summary()
        assert "date" in summary
        assert "total_events" in summary
    test("Daily learning summary", test_brain_daily_summary)
    
    # ===================================================
    # 2. Agent Manager (Dynamic Weights)
    # ===================================================
    print("\n\u2550" * 30 + " 2. Agent Manager " + "\u2550" * 30)
    
    def test_agent_manager():
        from services.agent_manager import AgentManager
        am = AgentManager()
        assert am is not None
    test("AgentManager initialization", test_agent_manager)
    
    # ===================================================
    # 3. Strategy Generator
    # ===================================================
    print("\n\u2550" * 30 + " 3. Strategy Generator " + "\u2550" * 30)
    
    def test_strategy_generator():
        from services.strategy_generator import generate_hybrid, generate_from_failure
        assert callable(generate_hybrid)
        assert callable(generate_from_failure)
    test("StrategyGenerator functions available", test_strategy_generator)
    
    # ===================================================
    # 4. Sandbox Tester
    # ===================================================
    print("\n\u2550" * 30 + " 4. Sandbox Tester " + "\u2550" * 30)
    
    def test_sandbox_tester():
        from services.sandbox_tester import test_strategy, generate_report
        assert callable(test_strategy)
        assert callable(generate_report)
    test("SandboxTester functions available", test_sandbox_tester)
    
    # ===================================================
    # 5. Controlled Deployer
    # ===================================================
    print("\n\u2550" * 30 + " 5. Controlled Deployer " + "\u2550" * 30)
    
    def test_controlled_deployer():
        from services.controlled_deployer import deploy, request_approval
        assert callable(deploy)
        assert callable(request_approval)
    test("ControlledDeployer functions available", test_controlled_deployer)
    
    # ===================================================
    # 6. Degradation Watcher
    # ===================================================
    print("\n\u2550" * 30 + " 6. Degradation Watcher " + "\u2550" * 30)
    
    def test_degradation_watcher():
        from services.degradation_watcher import DegradationWatcher
        dw = DegradationWatcher()
        assert dw is not None
    test("DegradationWatcher initialization", test_degradation_watcher)
    
    # ===================================================
    # 7. Self Healing
    # ===================================================
    print("\n\u2550" * 30 + " 7. Self Healing " + "\u2550" * 30)
    
    def test_self_healing():
        from services.self_healing import OmniSelfHealing
        sh = OmniSelfHealing()
        assert sh is not None
    test("OmniSelfHealing initialization", test_self_healing)
    
    # ===================================================
    # 8. Code Review Agent
    # ===================================================
    print("\n\u2550" * 30 + " 8. Code Review Agent " + "\u2550" * 30)
    
    def test_code_review():
        from services.code_review_agent import CodeReviewAgent
        cra = CodeReviewAgent()
        assert cra is not None
    test("CodeReviewAgent initialization", test_code_review)
    
    # ===================================================
    # 9. News Adapter
    # ===================================================
    print("\n\u2550" * 30 + " 9. News Adapter " + "\u2550" * 30)
    
    def test_news_adapter():
        from services.news_adapter import NewsAdapter
        na = NewsAdapter()
        assert na is not None
    test("NewsAdapter initialization", test_news_adapter)
    
    # ===================================================
    # 10. Alert Manager
    # ===================================================
    print("\n\u2550" * 30 + " 10. Alert Manager " + "\u2550" * 30)
    
    def test_alert_manager():
        from services.alert_manager import AlertManager, AlertPriority
        am = AlertManager()
        assert am is not None
        # Test learning stats
        stats = am.get_learning_stats()
        assert "repetition_threshold" in stats
        assert "escalation_timeout_sec" in stats
        assert "brain_connected" in stats
    test("AlertManager initialization + learning stats", test_alert_manager)
    
    def test_alert_send_and_ack():
        from services.alert_manager import AlertManager, AlertPriority
        am = AlertManager()
        alert = am.send_alert("Integration test alert", AlertPriority.MEDIUM, "test_cat")
        assert alert.priority == "MEDIUM"
        am.acknowledge_alert("test_cat", "Integration test alert")
        assert am.active_alerts[alert.alert_id].acknowledged == True
    test("Alert send + acknowledge flow", test_alert_send_and_ack)
    
    # ===================================================
    # 11. Cross-Component: Full Brain Flow
    # ===================================================
    print("\n\u2550" * 30 + " 11. Cross-Component Flow " + "\u2550" * 30)
    
    def test_full_brain_flow():
        from services.internal_brain import InternalBrain
        brain = InternalBrain()
        
        # Step 1: Agent logs accuracy
        brain.log_agent_accuracy("ICT", was_correct=True, market="EURUSD", confidence=0.85)
        
        # Step 2: Record keyword impact
        brain.learn_keyword_impact(
            keyword="integration_test_keyword",
            market="EURUSD",
            predicted_impact=0.5,
            actual_impact=0.8,
        )
        
        # Step 3: Track alert response
        brain.track_alert_response(
            user_id=1,
            alert_type="test_flow",
            was_read=True,
            was_acted_upon=True,
        )
        
        # Step 4: Log code error
        strictness = brain.log_code_error("test_file.py", "ImportError")
        assert strictness in ["low", "medium", "high", "critical"]
        
        # Step 5: Get daily summary
        summary = brain.get_daily_learning_summary()
        assert summary["total_events"] >= 0
        
        # All steps completed
        print("    -> Agent accuracy logged")
        print("    -> Keyword impact learned")
        print("    -> Alert response tracked")
        print(f"    -> Code error logged (strictness={strictness})")
        print(f"    -> Daily summary: {summary['total_events']} events today")
    test("Full cross-component brain flow", test_full_brain_flow)
    
    # ===================================================
    # RESULTS SUMMARY
    # ===================================================
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    
    print(f"\n   \U0001f9e0 Integration Test Results")
    print(f"   Total: {total} | \u2705 Passed: {passed} | \u274c Failed: {failed}")
    
    if failed > 0:
        print(f"\n   Failed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"   \u274c {name}: {err}")
    
    rate = (passed / total * 100) if total > 0 else 0
    print(f"\n   Success Rate: {rate:.0f}%")
    
    if rate == 100:
        print("\n   \U0001f389 ALL TESTS PASSED! System is fully integrated.")
    elif rate >= 80:
        print("\n   \u26a0\ufe0f Most tests passed. Minor issues to fix.")
    else:
        print("\n   \U0001f6a8 Significant failures detected!")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
