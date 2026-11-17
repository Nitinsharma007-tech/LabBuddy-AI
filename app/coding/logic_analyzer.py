"""
Logic Analyzer for RoboBuddy.
Implements the 4-Level Error Identification Pipeline:
  Level 1: Local Regex & AST Syntax Analyzer (Instant, Zero API)
  Level 2: Exact Logical Mistake Cache (SQLite)
  Level 3: Embedding-based Semantic RAG Retrieval
  Level 4: Gemini API Fallback for New Logical Mistakes
Enforces the Strict Socratic Teaching Rule: NEVER GIVE READY-TO-COPY CODE.
"""

from app.coding.syntax_analyzer import SyntaxAnalyzer
from app.coding.mistake_memory import MistakeMemory


class AnalysisResult:
    def __init__(
        self,
        has_error: bool,
        category: str = "",
        line_number: int = 1,
        hint: str = "",
        level: int = 1,
        source: str = "none",
        code_context: str = "",
    ):
        self.has_error = has_error
        self.category = category
        self.line_number = line_number
        self.hint = hint
        self.level = level
        self.source = source
        self.code_context = code_context


class LogicAnalyzer:
    def __init__(self, gemini_assistant=None, language_manager=None):
        self.syntax_analyzer = SyntaxAnalyzer()
        self.mistake_memory = MistakeMemory()
        self.gemini_assistant = gemini_assistant
        self.language_manager = language_manager

        # Track hints provided per line to progress: Hint 1 -> Hint 2 -> Hint 3
        self.line_hint_history = {}

    def get_language(self) -> str:
        if self.language_manager:
            return self.language_manager.language
        return "english"

    def analyze_code(
        self,
        code_text: str,
        experiment_name: str = "",
        experiment_objective: str = "",
        changed_line_hint: str = "",
        changed_line_number: int = 1,
    ) -> AnalysisResult:
        """
        Run the 4-stage error identification hierarchy.
        """
        if not code_text or not code_text.strip():
            return AnalysisResult(has_error=False)

        lang = self.get_language()
        is_hinglish = "hind" in lang.lower() or "hing" in lang.lower()

        # =========================================================================
        # LEVEL 1: Local Regex & AST Syntax Analysis
        # =========================================================================
        syntax_issue = self.syntax_analyzer.analyze(code_text)
        if syntax_issue:
            hint = syntax_issue.get_hint(lang)
            print(f"[ANALYZER] Level 1 (Local Syntax) caught: {syntax_issue.category} at line {syntax_issue.line_number}", flush=True)
            return AnalysisResult(
                has_error=True,
                category=syntax_issue.category,
                line_number=syntax_issue.line_number,
                hint=hint,
                level=1,
                source="level1_syntax",
                code_context=syntax_issue.raw_line,
            )

        # If syntax is completely clean, inspect for logical mistakes
        target_line = changed_line_hint.strip()
        target_lineno = changed_line_number

        # If changed line is not specified, scan lines for logical patterns
        if not target_line:
            lines = [l for l in code_text.splitlines() if l.strip() and not l.strip().startswith("#")]
            target_line = lines[-1] if lines else ""
            target_lineno = len(code_text.splitlines())

        if not target_line:
            return AnalysisResult(has_error=False)

        # Determine hint progression level
        current_level = self.line_hint_history.get(target_lineno, 0) + 1
        self.line_hint_history[target_lineno] = current_level

        # =========================================================================
        # LEVEL 2: Exact Logical Mistake Cache
        # =========================================================================
        cached = self.mistake_memory.find_exact(target_line)
        if cached:
            hint = cached["hint_hinglish"] if is_hinglish else cached["hint_english"]
            formatted_hint = f"Line {target_lineno}: {hint}"
            print(f"[ANALYZER] Level 2 (Exact Cache) matched: '{cached['category']}'", flush=True)
            return AnalysisResult(
                has_error=True,
                category=cached["category"],
                line_number=target_lineno,
                hint=formatted_hint,
                level=current_level,
                source="level2_exact_cache",
                code_context=target_line,
            )

        # =========================================================================
        # LEVEL 3: Embedding-based Semantic RAG Retrieval
        # =========================================================================
        semantic_match = self.mistake_memory.find_semantic(target_line, context=experiment_objective, threshold=0.84)
        if semantic_match:
            hint = semantic_match["hint_hinglish"] if is_hinglish else semantic_match["hint_english"]
            formatted_hint = f"Line {target_lineno}: {hint}"
            print(f"[ANALYZER] Level 3 (Semantic RAG) matched: '{semantic_match['category']}'", flush=True)
            return AnalysisResult(
                has_error=True,
                category=semantic_match["category"],
                line_number=target_lineno,
                hint=formatted_hint,
                level=current_level,
                source="level3_semantic_rag",
                code_context=target_line,
            )

        # =========================================================================
        # LEVEL 4: Gemini API Fallback for New Logical Mistakes
        # =========================================================================
        if self.gemini_assistant:
            try:
                gemini_hint = self.gemini_assistant.analyze_logical_mistake(
                    experiment_name=experiment_name,
                    experiment_objective=experiment_objective,
                    code_context=code_text,
                    changed_line=target_line,
                    line_number=target_lineno,
                    hint_level=min(current_level, 3),
                )
                print(f"[ANALYZER] Level 4 (Gemini API) evaluated logical issue at line {target_lineno}", flush=True)

                # Persist the newly discovered logical mistake to memory
                self.mistake_memory.save_mistake(
                    code_snippet=target_line,
                    category="Logical Analysis",
                    experiment_name=experiment_name,
                    why_incorrect="Identified logical inconsistency during code analysis",
                    hint_english=gemini_hint if not is_hinglish else "Verify your logical condition and loop ranges.",
                    hint_hinglish=gemini_hint if is_hinglish else "Apni logic aur condition ko verify karo.",
                )

                return AnalysisResult(
                    has_error=True,
                    category="Logical Guidance",
                    line_number=target_lineno,
                    hint=gemini_hint,
                    level=current_level,
                    source="level4_gemini",
                    code_context=target_line,
                )
            except Exception as e:
                print(f"[ANALYZER] Gemini analysis error: {e}", flush=True)

        return AnalysisResult(has_error=False)
