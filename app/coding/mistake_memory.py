"""
Mistake Memory and Retrieval System for RoboBuddy (Methods 2 & 3).
Includes Exact Logical Mistake Cache (SQLite) and Embedding-based Semantic RAG Retrieval.
Keeps mistake history persistent across application restarts.
"""

import json
import math
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "mistakes"
DB_PATH = DATA_DIR / "mistake_cache.db"


class MistakeMemory:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder = None
        self._init_db()
        self._seed_common_mistakes()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mistakes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_signature TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    experiment_name TEXT,
                    code_pattern TEXT,
                    why_incorrect TEXT,
                    hint_english TEXT,
                    hint_hinglish TEXT,
                    embedding_json TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signature ON mistakes(error_signature)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON mistakes(category)")

    @staticmethod
    def normalize_code(code_snippet: str) -> str:
        """
        Normalize code by abstracting variable names, spaces, and quotes so that
        'if number > 10:' and 'if value > 10:' produce equivalent normalized signatures.
        """
        code = code_snippet.strip().lower()
        # Normalize quotes
        code = re.sub(r"['\"]", '"', code)
        # Normalize whitespace
        code = re.sub(r"\s+", " ", code)
        # Common variable normalization for simple patterns
        # Replace variable names that are not keywords
        keywords = {
            "if", "elif", "else", "for", "in", "while", "def", "return", "print",
            "range", "len", "input", "int", "float", "str", "list", "dict",
            "and", "or", "not", "is", "true", "false", "none"
        }
        tokens = re.split(r"(\W+)", code)
        normalized = []
        var_map = {}
        var_counter = 1
        for tok in tokens:
            if re.match(r"^[a-zA-Z_]\w*$", tok):
                if tok in keywords:
                    normalized.append(tok)
                else:
                    if tok not in var_map:
                        var_map[tok] = f"var_{var_counter}"
                        var_counter += 1
                    normalized.append(var_map[tok])
            else:
                normalized.append(tok)
        return "".join(normalized)

    def _compute_vector(self, text: str) -> list[float]:
        """
        Compute lightweight character n-gram / term frequency vector for semantic similarity.
        Safe, fast, and does not block the UI or depend on large GPU model loading.
        """
        words = re.findall(r"\w+", text.lower())
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        # Also include 3-grams
        for i in range(len(text) - 2):
            ng = text[i:i+3].lower()
            freq[ng] = freq.get(ng, 0) + 0.5
        norm = math.sqrt(sum(v * v for v in freq.values())) or 1.0
        return {k: v / norm for k, v in freq.items()}

    @staticmethod
    def _cosine_similarity(vec1: dict, vec2: dict) -> float:
        if not vec1 or not vec2:
            return 0.0
        common_keys = set(vec1.keys()) & set(vec2.keys())
        return sum(vec1[k] * vec2[k] for k in common_keys)

    def find_exact(self, code_snippet: str) -> dict | None:
        """
        Method 2: Exact Logical Mistake Cache lookup based on normalized code signature.
        """
        sig = self.normalize_code(code_snippet)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, category, why_incorrect, hint_english, hint_hinglish, occurrence_count "
                "FROM mistakes WHERE error_signature = ?",
                (sig,),
            )
            row = cursor.fetchone()
            if row:
                m_id, cat, why, he, hh, count = row
                conn.execute(
                    "UPDATE mistakes SET occurrence_count = occurrence_count + 1 WHERE id = ?",
                    (m_id,),
                )
                return {
                    "id": m_id,
                    "category": cat,
                    "why_incorrect": why,
                    "hint_english": he,
                    "hint_hinglish": hh,
                    "occurrence_count": count + 1,
                    "source": "exact_cache",
                }
        return None

    def find_semantic(self, code_snippet: str, context: str = "", threshold: float = 0.82) -> dict | None:
        """
        Method 3: Embedding-based semantic similarity search.
        Finds logically equivalent mistakes even if variable names or structures differ.
        """
        query_sig = self.normalize_code(code_snippet)
        query_vec = self._compute_vector(f"{query_sig} {context}")

        best_match = None
        best_score = 0.0

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, category, why_incorrect, hint_english, hint_hinglish, embedding_json FROM mistakes")
            for m_id, cat, why, he, hh, emb_json in cursor.fetchall():
                if not emb_json:
                    continue
                try:
                    db_vec = json.loads(emb_json)
                    score = self._cosine_similarity(query_vec, db_vec)
                    if score > best_score:
                        best_score = score
                        best_match = {
                            "id": m_id,
                            "category": cat,
                            "why_incorrect": why,
                            "hint_english": he,
                            "hint_hinglish": hh,
                            "score": score,
                            "source": "semantic_rag",
                        }
                except Exception:
                    continue

        if best_match and best_score >= threshold:
            print(f"[MISTAKE_MEMORY] Semantic match found (similarity={best_score:.2f})", flush=True)
            return best_match
        return None

    def save_mistake(
        self,
        code_snippet: str,
        category: str,
        experiment_name: str,
        why_incorrect: str,
        hint_english: str,
        hint_hinglish: str,
    ):
        """
        Save a new mistake discovered by Gemini or analysis into memory for future instant retrieval.
        """
        sig = self.normalize_code(code_snippet)
        vec = self._compute_vector(f"{sig} {category} {why_incorrect}")
        emb_json = json.dumps(vec)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mistakes (
                    error_signature, category, experiment_name, code_pattern,
                    why_incorrect, hint_english, hint_hinglish, embedding_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(error_signature) DO UPDATE SET
                    occurrence_count = occurrence_count + 1,
                    hint_english = excluded.hint_english,
                    hint_hinglish = excluded.hint_hinglish
                """,
                (sig, category, experiment_name, code_snippet, why_incorrect, hint_english, hint_hinglish, emb_json),
            )
            print(f"[MISTAKE_MEMORY] Saved new mistake to cache: '{category}'", flush=True)

    def _seed_common_mistakes(self):
        """Seed initial well-known logical mistakes for beginner experiments."""
        seeds = [
            (
                "if var_1 > 10 : print ( \"small\" )",
                "Reversed Condition Logic",
                "Conditional Statements",
                "The greater-than sign is used instead of less-than when checking for small numbers.",
                "Check the comparison operator on this line. You used '>', which checks if the value is greater than 10. Think about whether you intended to check if it is smaller.",
                "Line par comparison operator ko dhyan se dekho. Tumne '>' use kiya hai jo check karta hai ki value 10 se badi hai ya nahi. Agar choti value check karni thi toh kaunsa operator aana chahiye?",
            ),
            (
                "for var_1 in range ( 1 , 10 ) :",
                "Off-by-One Loop Range",
                "Loops and Patterns",
                "range(1, 10) stops at 9, not 10.",
                "Remember how Python's range(start, stop) function works. The stop value is exclusive, so range(1, 10) only goes up to 9. If you need 10 to be included, adjust the stop value.",
                "Python ke range(start, stop) function ko yaad karo. Stop value include nahi hoti, isliye range(1, 10) sirf 9 tak chalega. Agar 10 bhi chahiye toh stop value ko adjust karo.",
            ),
            (
                "var_1 = input ( \"enter\" ) ; var_2 = var_1 + 5",
                "String to Integer Type Error",
                "Operators and Type Conversion",
                "input() returns a string; adding an integer causes a TypeError.",
                "The input() function always returns text (a string). In Python, you cannot directly add an integer to a string. You need to convert the input into an int or float first.",
                "input() function hamesha string return karta hai. Python mein string ke sath number directly add nahi ho sakta. Pehle input ko int() ya float() mein convert karo.",
            ),
            (
                "while var_1 > 0 : print ( var_1 )",
                "Infinite Loop (Missing Decrement)",
                "Loops and Patterns",
                "The loop counter is never decremented inside the while loop.",
                "Look closely at the while loop. Notice that the condition variable never changes inside the loop body. This will create an infinite loop. Make sure you update the counter.",
                "Apne while loop ko dekho. Loop ke andar counter variable change hi nahi ho raha hai. Aise toh loop kabhi band hi nahi hoga! Loop ke andar counter ko update karo.",
            ),
        ]
        with self._connect() as conn:
            for pat, cat, exp, why, he, hh in seeds:
                sig = self.normalize_code(pat)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM mistakes WHERE error_signature = ?", (sig,))
                if not cursor.fetchone():
                    vec = self._compute_vector(f"{sig} {cat} {why}")
                    conn.execute(
                        """
                        INSERT INTO mistakes (
                            error_signature, category, experiment_name, code_pattern,
                            why_incorrect, hint_english, hint_hinglish, embedding_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (sig, cat, exp, pat, why, he, hh, json.dumps(vec)),
                    )
