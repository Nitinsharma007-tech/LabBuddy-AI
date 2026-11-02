
import sqlite3
from pathlib import Path

import faiss
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_DIR = BASE_DIR / "app" / "database"

SQLITE_PATH = DATABASE_DIR / "understanding.db"
FAISS_PATH = DATABASE_DIR / "understanding.index"


class VectorStore:

    def __init__(self, encoder):
        """
        encoder: Existing SentenceTransformer model.
        """

        self.encoder = encoder
        self.dimension = encoder.get_sentence_embedding_dimension()

        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

        self._initialize_database()
        self.index = self._load_index()

    # --------------------------------------------------
    # DATABASE
    # --------------------------------------------------

    def _connect(self):
        return sqlite3.connect(SQLITE_PATH)

    def _initialize_database(self):

        with self._connect() as connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS examples (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    text TEXT NOT NULL,

                    intent TEXT NOT NULL,

                    experiment_id INTEGER,

                    source TEXT DEFAULT 'preset',

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_examples_intent
                ON examples(intent)
            """)

    # --------------------------------------------------
    # EMBEDDINGS
    # --------------------------------------------------

    def _encode(self, text):

        embedding = self.encoder.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return np.asarray(embedding, dtype=np.float32)

    # --------------------------------------------------
    # FAISS INDEX
    # --------------------------------------------------

    def _create_index(self):

        base_index = faiss.IndexFlatIP(self.dimension)

        return faiss.IndexIDMap2(base_index)

    def _load_index(self):

        if FAISS_PATH.exists():

            try:
                loaded_index = faiss.read_index(str(FAISS_PATH))

                if loaded_index.d != self.dimension:
                    raise ValueError("Embedding dimension mismatch")

                with self._connect() as connection:
                    database_count = connection.execute(
                        "SELECT COUNT(*) FROM examples"
                    ).fetchone()[0]

                if loaded_index.ntotal == database_count:
                    print(
                        f"Loaded FAISS index: "
                        f"{loaded_index.ntotal} examples"
                    )
                    return loaded_index

            except Exception as error:
                print(f"Could not load FAISS index: {error}")

        print("Building FAISS index from SQLite...")

        self.index = self._create_index()
        self.rebuild_index()

        return self.index

    def rebuild_index(self):

        self.index = self._create_index()

        with self._connect() as connection:

            rows = connection.execute("""
                SELECT id, text
                FROM examples
                ORDER BY id
            """).fetchall()

        if rows:

            texts = [row[1] for row in rows]
            ids = np.asarray(
                [row[0] for row in rows],
                dtype=np.int64
            )

            embeddings = self.encoder.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )

            embeddings = np.asarray(
                embeddings,
                dtype=np.float32
            )

            self.index.add_with_ids(embeddings, ids)

        self._save_index()

        print(
            f"FAISS index rebuilt: {self.index.ntotal} examples"
        )

    def _save_index(self):

        faiss.write_index(
            self.index,
            str(FAISS_PATH)
        )

    # --------------------------------------------------
    # ADD EXAMPLES
    # --------------------------------------------------

    def add_example(
        self,
        text,
        intent,
        experiment_id=None,
        source="preset"
    ):

        text = text.strip()
        intent = intent.strip()

        if not text or not intent:
            raise ValueError("Text and intent cannot be empty.")

        with self._connect() as connection:

            existing = connection.execute("""
                SELECT id
                FROM examples
                WHERE text = ?
                AND intent = ?
                AND experiment_id IS ?
            """, (text, intent, experiment_id)).fetchone()

            if existing:
                return {
                    "success": False,
                    "message": "Example already exists.",
                    "id": existing[0]
                }

            cursor = connection.execute("""
                INSERT INTO examples
                (text, intent, experiment_id, source)
                VALUES (?, ?, ?, ?)
            """, (
                text,
                intent,
                experiment_id,
                source
            ))

            record_id = cursor.lastrowid

        try:

            embedding = self._encode(text)

            self.index.add_with_ids(
                embedding,
                np.asarray([record_id], dtype=np.int64)
            )

            self._save_index()

        except Exception:

            # SQLite remains the source of truth.
            # A later rebuild will restore the FAISS index.
            self.rebuild_index()
            raise

        return {
            "success": True,
            "message": "Example added successfully.",
            "id": record_id
        }

    # --------------------------------------------------
    # SEMANTIC SEARCH
    # --------------------------------------------------

    def search(self, query, top_k=5):

        query = query.strip()

        if not query:
            return []

        if self.index.ntotal == 0:
            return []

        query_embedding = self._encode(query)

        scores, ids = self.index.search(
            query_embedding,
            min(top_k, self.index.ntotal)
        )

        results = []

        with self._connect() as connection:

            for score, record_id in zip(
                scores[0],
                ids[0]
            ):

                if record_id == -1:
                    continue

                row = connection.execute("""
                    SELECT id, text, intent,
                           experiment_id, source
                    FROM examples
                    WHERE id = ?
                """, (int(record_id),)).fetchone()

                if row:

                    results.append({
                        "id": row[0],
                        "text": row[1],
                        "intent": row[2],
                        "experiment_id": row[3],
                        "source": row[4],
                        "similarity": float(score)
                    })

        return results

    # --------------------------------------------------
    # DATABASE INFORMATION
    # --------------------------------------------------

    def count(self):

        with self._connect() as connection:

            return connection.execute(
                "SELECT COUNT(*) FROM examples"
            ).fetchone()[0]

    def get_all_examples(self):

        with self._connect() as connection:

            rows = connection.execute("""
                SELECT id, text, intent,
                       experiment_id, source
                FROM examples
                ORDER BY id
            """).fetchall()

        return [
            {
                "id": row[0],
                "text": row[1],
                "intent": row[2],
                "experiment_id": row[3],
                "source": row[4]
            }
            for row in rows
        ]
