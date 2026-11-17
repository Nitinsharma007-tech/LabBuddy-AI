"""
Syntax Analyzer for RoboBuddy (Method 1: Local Regex & AST Parser).
Validates syntax via Python AST and pinpoints beginner mistakes with Regex patterns.
Produces strict Socratic hints in English or Hinglish without giving ready-made code solutions.
"""

import ast
import re


class SyntaxIssue:
    def __init__(self, line_number: int, category: str, hint_english: str, hint_hinglish: str, raw_line: str = ""):
        self.line_number = line_number
        self.category = category
        self.hint_english = hint_english
        self.hint_hinglish = hint_hinglish
        self.raw_line = raw_line

    def get_hint(self, language: str) -> str:
        if "hind" in language.lower() or "hing" in language.lower():
            return self.hint_hinglish
        return self.hint_english


class SyntaxAnalyzer:
    COLON_KEYWORDS = re.compile(
        r"^\s*(if\b|elif\b|else\b|for\b|while\b|def\b|class\b|try\b|except\b|finally\b|with\b)",
        re.IGNORECASE,
    )

    ASSIGNMENT_IN_CONDITION = re.compile(
        r"^\s*(?:if|elif|while)\s+[^=!<>]+\s*=\s*[^=]",
        re.IGNORECASE,
    )

    KEYWORD_TYPOS = {
        "whlie": "while",
        "wihle": "while",
        "fro": "for",
        "funtion": "def",
        "function": "def",
        "prnit": "print",
        "prnt": "print",
        "true": "True",
        "false": "False",
        "none": "None",
        "elsif": "elif",
        "elseif": "elif",
    }

    def analyze(self, code_text: str) -> SyntaxIssue | None:
        """
        Analyze code locally.
        Returns a SyntaxIssue if a syntax problem is found, else None.
        """
        if not code_text or not code_text.strip():
            return None

        # 1. Primary ground-truth check with Python's built-in AST parser
        syntax_err = None
        indent_err = None
        try:
            ast.parse(code_text)
            # Code is syntactically valid Python!
            return None
        except IndentationError as ie:
            indent_err = ie
        except SyntaxError as se:
            syntax_err = se

        lines = code_text.splitlines()
        target_lineno = 1
        if indent_err:
            target_lineno = indent_err.lineno or 1
        elif syntax_err:
            target_lineno = syntax_err.lineno or 1

        raw_line = lines[target_lineno - 1] if target_lineno <= len(lines) else ""
        stripped = raw_line.strip()

        # 2. Pinpoint with regex patterns on the affected line or surrounding lines
        # A. Missing Colon
        if self.COLON_KEYWORDS.match(stripped):
            clean = stripped.split("#")[0].strip()
            if ":" not in clean:
                match_kw = self.COLON_KEYWORDS.match(stripped).group(1)
                return SyntaxIssue(
                    line_number=target_lineno,
                    category="Missing Colon",
                    hint_english=(
                        f"I found a syntax mistake on line {target_lineno}. Your '{match_kw}' statement "
                        "is missing a colon (:) at the end. In Python, a colon is required before starting "
                        "an indented block. Check the end of your statement and add the colon."
                    ),
                    hint_hinglish=(
                        f"Line {target_lineno} par ek syntax mistake hai. Aapke '{match_kw}' statement ke end mein "
                        f"colon (:) missing hai. Python mein condition ya loop ke baad colon lagana zaroori "
                        f"hota hai taaki agla block start ho sake. Apni line {target_lineno} ko check karke colon lagao."
                    ),
                    raw_line=raw_line,
                )

        # B. Assignment instead of comparison
        if self.ASSIGNMENT_IN_CONDITION.match(stripped):
            return SyntaxIssue(
                line_number=target_lineno,
                category="Comparison Operator",
                hint_english=(
                    f"Look closely at line {target_lineno}. A single equals sign '=' is used for assigning values to variables. "
                    "For comparing equality in conditions, Python uses a double equals '=='. "
                    "Check your comparison operator."
                ),
                hint_hinglish=(
                    f"Line {target_lineno} par dhyan do. Single '=' assignment ke liye use hota hai, par do values ko compare "
                    "karne ke liye double '==' use kiya jata hai. Apne condition operator ko check karke theek karo."
                ),
                raw_line=raw_line,
            )

        # C. Keyword Typos
        words = re.findall(r"\b[a-zA-Z_]\w*\b", stripped)
        for word in words:
            low_word = word.lower()
            if low_word in self.KEYWORD_TYPOS and word != self.KEYWORD_TYPOS[low_word]:
                intended = self.KEYWORD_TYPOS[low_word]
                return SyntaxIssue(
                    line_number=target_lineno,
                    category="Keyword Typo",
                    hint_english=(
                        f"There seems to be a keyword typo on line {target_lineno}: '{word}'. "
                        f"In Python, keywords are case-sensitive and spelled specifically (like '{intended}'). "
                        "Check the spelling on this line."
                    ),
                    hint_hinglish=(
                        f"Line {target_lineno} par ek spelling ya keyword mistake lag rahi hai: '{word}'. "
                        f"Python mein keywords case-sensitive hote hain (jaise '{intended}'). "
                        "Apni spelling verify karo."
                    ),
                    raw_line=raw_line,
                )

        # D. General Indentation Error
        if indent_err:
            return SyntaxIssue(
                line_number=target_lineno,
                category="Indentation Error",
                hint_english=(
                    f"I found an IndentationError on line {target_lineno}. Python relies on consistent indentation "
                    "(typically 4 spaces) to define code blocks inside loops, conditions, and functions. "
                    "Make sure the lines inside your block are indented properly."
                ),
                hint_hinglish=(
                    f"Line {target_lineno} par IndentationError hai. Python mein code blocks (jaise loops ya if ke andar ka code) "
                    "4 spaces indent hone chahiye. Apne code ki spacing aur indentation check karo."
                ),
                raw_line=raw_line,
            )

        # E. General Syntax Error
        msg = syntax_err.msg if syntax_err else "invalid syntax"
        return SyntaxIssue(
            line_number=target_lineno,
            category="Syntax Error",
            hint_english=(
                f"I detected a syntax error on line {target_lineno}: {msg}. "
                "Check for unclosed parentheses, missing quotes, or misplaced commas around this line."
            ),
            hint_hinglish=(
                f"Line {target_lineno} par syntax error mila hai: {msg}. "
                "Check karo ki kahin brackets ya quotes open toh nahi chhoot gaye, ya koi comma miss ho gaya ho."
            ),
            raw_line=raw_line,
        )
