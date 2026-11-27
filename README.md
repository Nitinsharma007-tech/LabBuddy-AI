# 🤖 RoboBuddy AI — Desktop Programming Tutor

RoboBuddy is a floating AI desktop companion that acts as a personal programming lab instructor. It guides students step by step through laboratory programming experiments, verifies their understanding before opening a coding workspace in VS Code, observes their live code in real time, and teaches them how to debug their own mistakes using a 4-tier Socratic hint system — **never providing ready-to-copy code**.

---

## 🚀 Key Features

### 1. 🌐 Dual-Language Manager (English & Hinglish)
- **Startup Language Choice**: Greets the user: *"Hello! Welcome back. Which language would you prefer today, English or Hindi?"*
- **Natural Hinglish**: Conversational Hinglish for Indian students with technical programming keywords preserved verbatim (`for`, `while`, `def`, `class`, `print`, etc.).
- **Voice Switching**: Switch languages anytime by speaking: *"Hindi mode on karo"*, *"Switch to English"*, etc.
- **Multilingual Speech Recognition & TTS**: Deepgram Multilingual STT combined with dynamic Edge-TTS voice pairing (`hi-IN-MadhurNeural` for Hinglish, `en-US-AndrewMultilingualNeural` for English).

### 2. 🧪 Structured Experiment Teaching & Understanding Confirmation Loop
- **Step-by-Step Pedagogy**:
  1. Relatable real-world analogy.
  2. Core concepts & logic.
  3. Step-by-step algorithm.
  4. Expected input/output.
- **Understanding Confirmation**: Asks *"Did you understand the experiment, or do you need me to explain anything again?"* (Hinglish: *"Experiment samajh aa gaya ya kisi part ko dobara explain karun?"*).
- **Adaptive Re-Explanation**: If the student does not understand, RoboBuddy re-explains using simpler terms and a completely new analogy without repeating itself. Workspace is never created until the student confirms understanding.

### 3. 📂 Dedicated Workspace Creation & VS Code Integration
- Generates `experiments/<Course>/<Experiment_Folder>/` with `main.py` and `experiment_info.json`.
- Automatically opens the workspace and starter file in VS Code using safe subprocess argument lists.
- Preserves existing student code (never overwrites).

### 4. 👁️ Live Background Code Monitoring & Debouncing
- Watches only the active experiment directory in a dedicated background `QThread`.
- Debounces file events (2–3 second quiet period) to avoid interrupting active typing.
- Pinpoints changed lines and surrounding AST context.

### 5. 🧠 4-Level Error Identification & Retrieval Pipeline
```text
Code Change Detected (Stable)
            │
            ▼
LEVEL 1: Local Regex & AST Syntax Parsing
(Zero API latency; catches missing colons, indentation, typos, operator issues)
            │ [If no syntax error]
            ▼
LEVEL 2: Exact Logical Mistake Cache
(Fast SQLite lookup by normalized code pattern)
            │ [If no exact cache match]
            ▼
LEVEL 3: Semantic RAG Vector Retrieval
(Finds equivalent mistakes with different variable names via cosine similarity)
            │ [If no semantic match]
            ▼
LEVEL 4: Gemini 2.5 Flash Socratic Fallback
(Diagnoses novel reasoning mistakes & persists to mistake cache)
```

### 6. 🎓 Strict Socratic Teaching Rule (NEVER GIVES READY-TO-COPY CODE)
- Never provides complete solutions, replacement blocks, or full functions.
- Progressive 4-tier hints:
  - **Hint 1**: Pinpoints line number & error category.
  - **Hint 2**: Explains the underlying programming concept.
  - **Hint 3**: Asks a guiding question to trigger self-discovery.
  - **Hint 4**: Clarifies the rule in simple terms and prompts the student to edit and retry.

---

## 🛠️ Technology Stack

| Component | Library / Framework |
|---|---|
| Desktop GUI | PySide6 (Qt for Python) |
| Voice Input (STT) | SoundDevice + Deepgram WebSocket (`flux-general-multi`) |
| Voice Output (TTS) | Edge-TTS + Qt QMediaPlayer (`en-US` & `hi-IN` neural voices) |
| LLM Brain | Google GenAI SDK (`gemini-2.5-flash`) |
| Local Vector / Cache | SQLite3 + Normalized Vector Similarity |
| Syllabus Parsing | PyMuPDF (fitz) + python-docx |

---

## 💻 How to Run

### 1. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Configure Environment Variables
Create or verify `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

### 3. Run RoboBuddy Companion
```powershell
python -m app.robot_main
```

### 4. Run Course Management Dashboard
```powershell
python -m app.main
```

### 5. Run Automated Pipeline Test
```powershell
python tests/test_pipeline
```
