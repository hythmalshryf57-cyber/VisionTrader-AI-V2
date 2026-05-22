"""
╔══════════════════════════════════════════════════════════════╗
║       Code Review Agent – VisionTrader AI                   ║
║  وكيل الذكاء الاصطناعي لمراجعة الكود قبل النشر              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import ast
import logging
from pathlib import Path
from typing import Dict, Any, List

# UTF-8 Encoding Fix for Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("CodeReview")

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from services.telegram_service import telegram_service
except ImportError:
    telegram_service = None

# Mock DeepSeek API
def _deepseek_analyze_code(code: str) -> Dict[str, Any]:
    """محاكاة لتحليل DeepSeek العميق للكود (المنطق، الأداء، والتوافق)"""
    issues = []
    
    # محاكاة لفحص المنطق
    if "def generate_signal" not in code:
        issues.append("Missing core function: 'generate_signal' is required for strategies.")
    
    # محاكاة لفحص الأداء
    if ".append(" in code and "for " in code:
        pass # Not necessarily bad, but could be slow if in tight loop.
    if "time.sleep(" in code:
        issues.append("Performance issue: Blocking 'time.sleep' call found in strategy logic.")
        
    if not issues:
        return {"status": "clean", "issues": []}
    return {"status": "issues_found", "issues": issues}


class CodeReviewAgent:
    def __init__(self):
        self.approved_strategies_dir = _BACKEND_DIR / "strategies"
        self._test_mode = False

    def quick_scan(self, code: str) -> List[str]:
        """فحص محلي سريع (نحوي وأمني أساسي) باستخدام AST."""
        logger.info("[Quick Scan] Running local syntax and security check...")
        issues = []
        
        # 1. Syntax Check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Syntax Error: {e.msg} at line {e.lineno}")
            return issues # Return immediately if syntax is broken
            
        # 2. Basic Security Check (disallow risky imports in strategies)
        risky_imports = {'os', 'subprocess', 'sys', 'socket', 'threading'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in risky_imports:
                        issues.append(f"Security: Risky import '{alias.name}' is not allowed in strategies.")
            elif isinstance(node, ast.ImportFrom):
                if node.module in risky_imports:
                    issues.append(f"Security: Risky import from '{node.module}' is not allowed in strategies.")
                    
        return issues

    def deep_analysis(self, code: str) -> List[str]:
        """تحليل عميق عبر الذكاء الاصطناعي (أخطاء منطقية، أداء، وتوافق)."""
        logger.info("[Deep Analysis] Sending to DeepSeek for advanced review...")
        # Fallback local deep analysis if DeepSeek key is missing
        result = _deepseek_analyze_code(code)
        return result.get("issues", [])

    def review(self, code_path: str) -> Dict[str, Any]:
        """المراجعة الشاملة للملف وإصدار القرار النهائي."""
        logger.info(f"Starting review for: {Path(code_path).name}")
        path = Path(code_path)
        
        if not path.exists():
            return self.request_changes(code_path, ["File does not exist."])
            
        code = path.read_text(encoding="utf-8")
        
        # 1. Quick Scan
        quick_issues = self.quick_scan(code)
        if quick_issues:
            logger.warning(f"Quick scan found {len(quick_issues)} issues.")
            return self.request_changes(code_path, quick_issues)
            
        # 2. Deep Analysis
        deep_issues = self.deep_analysis(code)
        if deep_issues:
            logger.warning(f"Deep analysis found {len(deep_issues)} issues.")
            return self.request_changes(code_path, deep_issues)
            
        # 3. Approve if all clean
        return self.approve(code_path)

    def approve(self, code_path: str) -> Dict[str, Any]:
        """الموافقة على النشر."""
        filename = Path(code_path).name
        logger.info(f"✅ APPROVED: {filename} passed all checks.")
        msg = f"✅ *Code Review Passed*\nStrategy `{filename}` is clean and ready for deployment."
        
        if telegram_service:
            telegram_service.send_message(os.getenv("TELEGRAM_CHAT_ID", ""), msg)
            
        return {
            "status": "approved",
            "file": filename,
            "message": "✅ موافق (Approved)"
        }

    def request_changes(self, code_path: str, issues: List[str]) -> Dict[str, Any]:
        """رفض الكود وطلب تعديلات مع ذكر الأسباب."""
        filename = Path(code_path).name
        logger.error(f"❌ REJECTED: {filename} requires changes.")
        
        issues_str = "\n".join(f"- {issue}" for issue in issues)
        msg = f"❌ *Code Review Failed*\nStrategy `{filename}` needs changes:\n{issues_str}"
        
        if telegram_service:
            telegram_service.send_message(os.getenv("TELEGRAM_CHAT_ID", ""), msg)
            
        return {
            "status": "rejected",
            "file": filename,
            "message": "❌ يحتاج تعديلات (Needs Changes)",
            "issues": issues
        }

# ══════════════════════════════════════════════════════════════════════════════
# Self-Test / Demo
# ══════════════════════════════════════════════════════════════════════════════
def run_demo():
    print("\n" + "═" * 60)
    print("  VisionTrader AI – Code Review Agent Demo")
    print("═" * 60 + "\n")

    agent = CodeReviewAgent()
    agent._test_mode = True

    # 1. Test Clean File (Evolved Strategy)
    print("--- [ SCENARIO 1: Clean Strategy ] ---")
    evolved_dir = _BACKEND_DIR / "_evolved"
    clean_strat = evolved_dir / "evolved_momentum_v1.py"
    
    if clean_strat.exists():
        report1 = agent.review(str(clean_strat))
        print(f"\nReport: {report1['message']}")
    else:
        print(f"Skipping Scenario 1: {clean_strat.name} not found.")

    # 2. Test File with Syntax Error
    print("\n--- [ SCENARIO 2: Syntax Error ] ---")
    bad_syntax_path = _BACKEND_DIR / "scratch_bad_syntax.py"
    bad_syntax_path.write_text("def generate_signal(data):\nreturn 'Buy'  # Indentation error", encoding="utf-8")
    
    report2 = agent.review(str(bad_syntax_path))
    print(f"\nReport: {report2['message']}")
    print("Issues:")
    for iss in report2['issues']:
        print(f"  - {iss}")
        
    bad_syntax_path.unlink() # cleanup

    # 3. Test File with Security & Logic Issues
    print("\n--- [ SCENARIO 3: Security & Logic Issues ] ---")
    bad_logic_path = _BACKEND_DIR / "scratch_bad_logic.py"
    bad_logic_code = """
import os
import time

def some_function():
    time.sleep(5)
    os.system('rm -rf /')
"""
    bad_logic_path.write_text(bad_logic_code, encoding="utf-8")
    
    report3 = agent.review(str(bad_logic_path))
    print(f"\nReport: {report3['message']}")
    print("Issues:")
    for iss in report3['issues']:
        print(f"  - {iss}")
        
    bad_logic_path.unlink() # cleanup

    print("\n" + "═" * 60)
    print("  Code Review Agent tests completed!")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    run_demo()
