# 🤖 LabBuddy AI — Your AI Lab Partner

LabBuddy AI is an intelligent laboratory syllabus management application designed for students. It helps students organize their laboratory courses, upload academic syllabi, automatically extract syllabus content, and identify practical experiments.

The desktop application provides a simple course management dashboard. The actual experiment learning experience is intended to be handled through a separate AI-powered voice assistant.

---

## ✨ Features

### 📚 Course Management
- Add multiple laboratory courses.
- Upload course syllabi in PDF, DOCX, and TXT formats.
- Edit course names.
- View course information.
- Delete courses with confirmation.
- Automatically save course information locally.
- Retain courses after restarting the application.

### 📄 Syllabus Processing
- Extract text from PDF documents.
- Extract paragraphs and tables from DOCX documents.
- Read TXT syllabus files.
- Automatically identify experiment numbers and titles.
- Display extracted experiments.
- View the original extracted syllabus content.

### 🖥️ Desktop Application
- Modern dark-themed dashboard.
- Built using Python and PySide6.
- Course statistics and experiment counts.
- Simple and user-friendly interface.
- Local course data storage.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| PySide6 | Desktop graphical interface |
| PyMuPDF | PDF text extraction |
| python-docx | Word document processing |
| JSON | Local course information storage |
| Git & GitHub | Version control |

---

## 📁 Project Structure

```text
LabBuddy-AI/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │
│   ├── ui/
│   │   ├── dashboard.py
│   │   ├── course_details.py
│   │   ├── experiment_page.py
│   │
│   ├── syllabus/
│   │   ├── parser.py
│   │   └── experiment_extractor.py
│   │
│   ├── environment/
│   │
│   ├── brain/
│   │
│   ├── voice/
│   │
│   └── database/
│
├── course_workspaces/
│   └── Each course has its own folder
│       └── course.json
│
├── assets/
│
├── data/
│
├── requirements.txt
├── README.md
└── .gitignore
```

*Note: Some directories are reserved for future AI assistant development.*

---

# 🚀 Installation and Setup

Follow these instructions to run LabBuddy AI on your computer.

## 1. Prerequisites

Install the following software:

- Python 3.11 or 3.12
- Git
- Visual Studio Code (recommended)

Check whether Python is installed:

```bash
python --version
```

Check Git:

```bash
git --version
```

If these commands are not recognized, install Python and Git first.

Python: https://www.python.org/downloads/

Git: https://git-scm.com/downloads

## 2. Clone the GitHub Repository

Open a terminal and execute:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Move into the project directory:

```bash
cd LabBuddy-AI
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the actual GitHub repository URL.

## 3. Create a Virtual Environment

A virtual environment keeps project dependencies separate from other Python projects.

### Windows (PowerShell)

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

## 5. Install Project Dependencies

Install all dependencies using:

```bash
python -m pip install -r requirements.txt
```

If you are installing dependencies individually:

```bash
python -m pip install PySide6
python -m pip install python-dotenv
python -m pip install PyMuPDF
python -m pip install python-docx
```

## 6. Run LabBuddy AI

From the project root, execute:

```bash
python -m app.main
```

The LabBuddy AI desktop dashboard should now launch.

---

# 📖 How to Use LabBuddy AI

### Step 1 — Launch the Application

Run the application using:

```bash
python -m app.main
```

### Step 2 — Add a Course

- Click **Add Course**.
- Enter your course name.
- Select the syllabus file.

Supported file formats:

- `.pdf`
- `.docx`
- `.txt`

### Step 3 — Automatic Syllabus Processing

LabBuddy AI extracts the syllabus text and identifies experiment headings.

### Step 4 — Manage Your Courses

From the dashboard, you can:

- View Details — View course information, extracted syllabus, and experiments.
- Edit — Change the course name.
- Delete — Remove the course and its saved workspace.

### Step 5 — Access Your Saved Courses

Course information is stored locally inside:

```text
course_workspaces/
```

Each course has its own folder containing its `course.json` file.

---

# 🔄 Git and GitHub Commands

If you are contributing to the project, use the following commands.

### Check Repository Status

```bash
git status
```

### Add Changes

```bash
git add .
```

### Commit Changes

```bash
git commit -m "Describe your changes"
```

### Push Changes to GitHub

```bash
git push
```

### Pull Latest Changes

```bash
git pull
```

---

# 🧹 Important Notes

1. Always activate the virtual environment before running the application.
2. Install dependencies using the active virtual environment.
3. Do not upload your virtual environment folder to GitHub.
4. Do not commit API keys, passwords, or other secrets.
5. Course data is stored locally on the computer.
6. Keep backups of important course workspaces.
7. Scanned PDFs may require OCR support, which is not currently included.
8. Experiment extraction currently relies on recognizable experiment heading patterns.

---

# 🛣️ Future Enhancements

The broader LabBuddy AI project is planned to include:

- AI-powered voice assistant.
- English, Hindi, and Hinglish interaction.
- Speech recognition using Deepgram.
- AI reasoning using Google Gemini.
- Text-to-speech using Edge TTS.
- Personalized experiment explanations.
- Interactive voice-based doubt solving.
- Separate Python environments for individual courses.

These are planned extensions and are not all implemented in the current desktop application.

---

# 👨‍💻 Development

Contributions, suggestions, and improvements are welcome.

For development:

```bash
git checkout -b feature/your-feature-name
```

After making changes:

```bash
git add .
git commit -m "Add your feature description"
git push -u origin feature/your-feature-name
```

You can then open a Pull Request on GitHub.

---

**LabBuddy AI — Learn smarter. Experiment better.** 🤖

*Developed as an AI-powered laboratory learning and course management project.*