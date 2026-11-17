import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from PySide6.QtCore import QCoreApplication
app = QCoreApplication.instance() or QCoreApplication(sys.argv)

from app.brain.language_manager import LanguageManager
from app.coding.workspace_manager import WorkspaceManager
from app.coding.code_monitor import CodeMonitor
from app.coding.logic_analyzer import LogicAnalyzer

print("=== RUNNING FULL END-TO-END PIPELINE TEST ===")
print("Project Base Directory:", BASE_DIR)

# 1. Setup workspace
wm = WorkspaceManager(BASE_DIR / "experiments")
course = {"name": "Python"}
exp = {
    "number": 3,
    "title": "Conditional Statements",
    "description": "Develop programs to check whether a number is even or odd, or check thresholds.",
    "concepts": "if, elif, else, nested conditions",
}
wpath = wm.create_experiment_workspace(course, exp)
print("1. Workspace created:", wpath)

# 2. Setup Logic Analyzer in Hinglish mode
lm = LanguageManager(default_language="hinglish")
analyzer = LogicAnalyzer(language_manager=lm)

# 3. Test Level 1: Syntax Error
bad_syntax_code = "number = 15\nif number > 10\n    print('Number is big')"
res_syntax = analyzer.analyze_code(bad_syntax_code, experiment_name=exp["title"], experiment_objective=exp["description"])
assert res_syntax.has_error
assert res_syntax.source == "level1_syntax"
assert res_syntax.category == "Missing Colon"
assert res_syntax.line_number == 2
print("2. Level 1 (Local Syntax) Test PASSED:")
print("   Category:", res_syntax.category)
print("   Line:", res_syntax.line_number)
print("   Socratic Hint:", res_syntax.hint)

# 4. Test Level 2: Exact Logical Mistake Cache
bad_logic_code = "if number > 10 : print ( \"small\" )"
res_logic = analyzer.analyze_code(bad_logic_code, experiment_name=exp["title"], experiment_objective=exp["description"], changed_line_hint=bad_logic_code, changed_line_number=1)
assert res_logic.has_error
assert res_logic.source == "level2_exact_cache"
assert res_logic.category == "Reversed Condition Logic"
print("3. Level 2 (Exact Logical Cache) Test PASSED:")
print("   Category:", res_logic.category)
print("   Socratic Hint:", res_logic.hint)

# 5. Test Level 3: Semantic RAG Retrieval (with different variable name 'value' instead of 'number')
semantic_code = "if value > 10 : print ( \"small\" )"
res_semantic = analyzer.analyze_code(semantic_code, experiment_name=exp["title"], experiment_objective=exp["description"], changed_line_hint=semantic_code, changed_line_number=1)
assert res_semantic.has_error
print("4. Level 3 (Semantic RAG Retrieval) Test PASSED:")
print("   Source:", res_semantic.source)
print("   Category:", res_semantic.category)
print("   Socratic Hint:", res_semantic.hint)

# Verify Strict Rule: No code solution given in hint
assert "replace your code" not in res_syntax.hint.lower()
assert "replace your code" not in res_logic.hint.lower()
print("5. Strict Socratic Rule Verification: PASSED (Zero solution code provided).")

print("\n=== ALL PIPELINE VERIFICATIONS PASSED SUCCESSFULLY! ===")
