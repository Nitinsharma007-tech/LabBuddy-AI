"""
Master Robot Controller for RoboBuddy.
Orchestrates the floating companion UI, multilingual voice layer, Socratic teaching agent,
understanding confirmation loop, workspace creation, and live code monitoring.
"""

import difflib
import json
import re
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from app.brain.gemini import GeminiAssistant
from app.brain.language_manager import LanguageManager
from app.brain.teaching_agent import TeachingAgent
from app.coding.code_monitor import CodeMonitor
from app.coding.logic_analyzer import LogicAnalyzer
from app.coding.vscode_manager import VSCodeManager
from app.coding.workspace_manager import WorkspaceManager
from app.voice.listener import VoiceListener
from app.voice.speaker import LabBuddySpeaker

BASE_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = BASE_DIR / "course_workspaces"


class AskWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, func, *args, parent=None):
        super().__init__(parent)
        self.func = func
        self.args = args

    def run(self):
        try:
            result = self.func(*self.args)
            self.completed.emit(str(result))
        except Exception as error:
            self.failed.emit(str(error))


class StreamAskWorker(QThread):
    chunk_received = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, stream_func, *args, parent=None):
        super().__init__(parent)
        self.stream_func = stream_func
        self.args = args

    def run(self):
        try:
            parts = []
            for chunk in self.stream_func(*self.args):
                if chunk:
                    parts.append(chunk)
                    self.chunk_received.emit(chunk)
            self.completed.emit("".join(parts).strip())
        except Exception as error:
            self.failed.emit(str(error))


class AnalysisWorker(QThread):
    analysis_ready = Signal(object)

    def __init__(self, analyzer, code, exp_name, exp_obj, changed_line, lineno, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.code = code
        self.exp_name = exp_name
        self.exp_obj = exp_obj
        self.changed_line = changed_line
        self.lineno = lineno

    def run(self):
        try:
            result = self.analyzer.analyze_code(
                code_text=self.code,
                experiment_name=self.exp_name,
                experiment_objective=self.exp_obj,
                changed_line_hint=self.changed_line,
                changed_line_number=self.lineno,
            )
            self.analysis_ready.emit(result)
        except Exception as e:
            print(f"[CONTROLLER] AnalysisWorker failed: {e}", flush=True)


class RobotController(QObject):
    def __init__(self, robot_window, parent=None):
        super().__init__(parent)
        self.robot = robot_window

        # Core subsystems
        self.language_manager = LanguageManager()
        self.assistant = None
        self.teaching_agent = None
        self.workspace_manager = WorkspaceManager()
        self.logic_analyzer = None
        self.code_monitor = None
        self.speaker = LabBuddySpeaker(self)
        self.listener = None

        self.courses = []
        self.selected_course = None
        self.selected_experiment = None
        self.active_workspace_path = None

        # State Machine:
        # 'awaiting_language', 'awaiting_course', 'awaiting_experiment',
        # 'teaching_explanation', 'awaiting_understanding', 'workspace_active'
        self.stage = "awaiting_language"
        self.next_action = None
        self.closing = False

        # Live speech tracking
        self.spoken_text = ""
        self.display_words = []
        self.display_index = 0
        self.current_sentence = ""

        # Typing animation timer for speech bubble
        self.display_timer = QTimer(self)
        self.display_timer.setInterval(45)
        self.display_timer.timeout.connect(self.show_next_word)

        # Worker threads
        self.ask_worker = None
        self.analysis_worker = None
        self._stream_started = False
        self._stream_next_action = None
        self._stream_append_uq = False
        self._stream_next_stage = None

        self._init_subsystems()
        self._connect_signals()

        # Start initial startup greeting
        QTimer.singleShot(700, self.start_session)

    def _init_subsystems(self):
        try:
            self.assistant = GeminiAssistant(language=self.language_manager.language)
        except Exception as e:
            print(f"[CONTROLLER] Gemini notice: {e}", flush=True)
            self.assistant = None

        self.teaching_agent = TeachingAgent(self.assistant, self.language_manager)
        self.logic_analyzer = LogicAnalyzer(self.assistant, self.language_manager)

    def _connect_signals(self):
        # UI triggers
        self.robot.listen_requested.connect(self.start_listening)
        self.robot.idle_requested.connect(self.go_idle)
        self.robot.exit_requested.connect(self.exit_assistant)
        self.robot.experiment_selected.connect(self.on_experiment_card_selected)

        # Speaker events
        self.speaker.sentence_started.connect(self.on_sentence_started)
        self.speaker.speech_finished.connect(self.on_speech_finished)
        self.speaker.speech_error.connect(self.on_speech_error)

    def load_courses(self):
        self.courses = []
        if not WORKSPACE_DIR.exists():
            return
        for path in sorted(WORKSPACE_DIR.iterdir()):
            if path.is_dir():
                course_json = path / "course.json"
                if course_json.exists():
                    try:
                        data = json.loads(course_json.read_text(encoding="utf-8"))
                        data["workspace"] = str(path)
                        self.courses.append(data)
                    except Exception:
                        pass

    def start_session(self):
        """Phase 1 greeting: Ask user for language preference."""
        if self.closing:
            return
        self.load_courses()
        if self.courses:
            self.selected_course = self.courses[0]

        self.stage = "awaiting_language"
        greeting = self.language_manager.get_greeting_prompt()
        self.speak_prompt(greeting, next_action="listen")

    def speak_prompt(self, message: str, next_action: str = None):
        if self.closing:
            return
        self.next_action = next_action
        self.spoken_text = message
        self.robot.set_state("speaking")
        self.robot.show_answer(message)
        # Match Edge-TTS voice to current active language
        self.speaker.set_voice(self.language_manager.voice)
        self.speaker.speak(message)

    def start_listening(self):
        if self.closing:
            return
        self.speaker.stop()
        self.robot.set_state("listening")

        if self.listener is None:
            self.listener = VoiceListener(self)
            self.listener.partial_transcript.connect(self.on_partial_transcript)
            self.listener.final_transcript.connect(self.on_final_transcript)
            self.listener.listening_stopped.connect(self.on_listening_stopped)
            self.listener.listener_error.connect(self.on_listener_error)

        if not self.listener.isRunning():
            self.listener.start()

    def on_partial_transcript(self, text: str):
        if text.strip():
            self.robot.show_transcript(text)

    def on_final_transcript(self, text: str):
        transcript = (text or "").strip()
        print(f"[VOICE] Final transcript: '{transcript}'", flush=True)

        if not transcript:
            self.robot.set_state("idle")
            return

        self.robot.show_transcript(transcript)

        # 1. Global language switch voice command check
        detected_lang = self.language_manager.detect_language_switch(transcript)
        if detected_lang and self.stage != "awaiting_language":
            self.set_language_mode(detected_lang)
            msg = self.language_manager.get_language_switched_message(detected_lang)
            self.speak_prompt(msg, next_action="listen")
            return

        # 2. Route by active stage
        if self.stage == "awaiting_language":
            self.handle_language_selection(transcript)
        elif self.stage == "awaiting_course":
            self.handle_course_selection(transcript)
        elif self.stage == "awaiting_experiment":
            self.handle_experiment_selection(transcript)
        elif self.stage == "awaiting_understanding":
            self.handle_understanding_confirmation(transcript)
        else:
            # Active session / doubts / workspace active
            self.handle_user_query(transcript)

    def set_language_mode(self, lang: str):
        self.language_manager.set_language(lang)
        if self.assistant:
            self.assistant.set_language(self.language_manager.language)
        self.speaker.set_voice(self.language_manager.voice)
        print(f"[CONTROLLER] Language mode active: {self.language_manager.language}", flush=True)

    def handle_language_selection(self, transcript: str):
        t = transcript.lower()
        if "hind" in t or "hing" in t:
            self.set_language_mode(LanguageManager.HINGLISH)
            msg = (
                "Namaste! Ab hum Hinglish mein baat karenge. "
                "Maine aapka course load kar liya hai. "
                "Batao, kaunsa experiment start karna hai? "
                "Ya fir main experiment list dikhaun?"
            )
        else:
            self.set_language_mode(LanguageManager.ENGLISH)
            msg = (
                "Great! We will continue in English. "
                "I have your practical course ready. "
                "Which experiment would you like to learn today? "
                "You can also ask me to show the experiment list."
            )
        self.stage = "awaiting_experiment"
        self.speak_prompt(msg, next_action="listen")

    def handle_experiment_selection(self, transcript: str):
        t = transcript.lower()

        # Check if user wants to see the visual experiment list dialog
        if any(w in t for w in ["show", "list", "view", "dialog", "open syllabus", "experiments"]):
            if self.selected_course and self.selected_course.get("experiments"):
                self.robot.show_experiment_dialog(
                    self.selected_course.get("name", "Course"),
                    self.selected_course.get("experiments", []),
                )
                prompt = (
                    "Maine experiment list screen par open kar di hai. "
                    "Kisi bhi card par click karo ya mujhe experiment number batao."
                    if self.language_manager.language == LanguageManager.HINGLISH
                    else "I have opened the experiment cards. Select one or tell me the experiment number."
                )
                self.speak_prompt(prompt)
                return

        # Check for numeric experiment selection (e.g. "experiment 1", "number two", "pehla experiment")
        matched_exp = self._match_experiment_from_text(transcript)
        if matched_exp:
            self.on_experiment_card_selected(matched_exp.get("number", 1))
            return

        # If user asked a general doubt or greeting
        self.handle_user_query(transcript)

    def _match_experiment_from_text(self, text: str):
        if not self.selected_course:
            return None
        experiments = self.selected_course.get("experiments", [])
        if not experiments:
            return None

        lowered = text.lower().strip()
        exp_by_num = {int(exp.get("number", 0)): exp for exp in experiments}

        # 1. Check for digits (prefer a digit right after "experiment" or "number" if multiple)
        explicit_digit = re.search(r"\b(?:experiment|exp|number|no\.?)\s*(\d+)\b", lowered)
        if explicit_digit:
            val = int(explicit_digit.group(1))
            if val in exp_by_num:
                return exp_by_num[val]

        num_match = re.search(r"\b(\d+)\b", lowered)
        if num_match:
            val = int(num_match.group(1))
            if val in exp_by_num:
                return exp_by_num[val]

        # 2. Unambiguous word number matching (exclude English verb "do" from matching 2)
        word_map = {
            "one": 1, "first": 1, "pehla": 1, "ek": 1,
            "two": 2, "second": 2, "doosra": 2, "dusra": 2,
            "three": 3, "third": 3, "teesra": 3, "teen": 3,
            "four": 4, "fourth": 4, "chautha": 4, "chaar": 4,
            "five": 5, "fifth": 5, "paanchwa": 5, "paanch": 5, "panch": 5,
            "six": 6, "sixth": 6, "chhatha": 6, "chhe": 6,
            "seven": 7, "seventh": 7, "saatwa": 7, "saat": 7,
            "eight": 8, "eighth": 8, "aathwa": 8, "aath": 8,
            "nine": 9, "ninth": 9, "nauwa": 9, "nau": 9,
            "ten": 10, "tenth": 10, "daswa": 10, "das": 10,
        }
        for w, num in word_map.items():
            if re.search(rf"\b{w}\b", lowered) and num in exp_by_num:
                return exp_by_num[num]

        # 3. Hindi "do" (2) only when used as an experiment number, never as the English verb "do"
        if 2 in exp_by_num and (
            lowered == "do"
            or re.search(r"\b(?:experiment|number|no\.?)\s+do\b", lowered)
            or re.search(r"\bdo\s+(?:number|experiment)\b", lowered)
        ):
            return exp_by_num[2]

        # 4. Fuzzy title matching
        titles = [exp.get("title", "") for exp in experiments]
        matches = difflib.get_close_matches(text, titles, n=1, cutoff=0.45)
        if matches:
            for exp in experiments:
                if exp.get("title") == matches[0]:
                    return exp

        return None

    def on_experiment_card_selected(self, number: int):
        """User chose an experiment via click or voice."""
        if not self.selected_course:
            return
        for exp in self.selected_course.get("experiments", []):
            if int(exp.get("number", 0)) == int(number):
                self.selected_experiment = exp
                break

        if not self.selected_experiment:
            return

        self.robot.close_experiment_dialog()
        title = self.selected_experiment.get("title", f"Experiment {number}")
        print(f"[CONTROLLER] Selected Experiment {number}: {title}", flush=True)

        # Set lesson in teaching agent
        self.teaching_agent.set_lesson(self.selected_course, self.selected_experiment)

        # Begin step-by-step teaching explanation
        self.stage = "teaching_explanation"
        self.robot.set_state("thinking")
        self.robot.show_bubble(f"Preparing lesson for Experiment {number}: {title}...")

        # Run Gemini streaming in background -> immediate TTS
        self._start_streaming_response(
            self.teaching_agent.explain_experiment_stream,
            False,
            next_action="listen",
            append_understanding_question=True,
            next_stage="awaiting_understanding",
        )

    def on_teaching_explanation_ready(self, explanation: str):
        self.stage = "awaiting_understanding"
        # Append the explicit understanding confirmation question
        question = self.language_manager.get_understanding_question()
        full_message = f"{explanation}\n\n{question}"
        self.speak_prompt(full_message, next_action="listen")

    def handle_understanding_confirmation(self, transcript: str):
        decision = self.teaching_agent.check_understanding_response(transcript)
        print(f"[CONTROLLER] Understanding response classified as: '{decision}'", flush=True)

        if decision == "understood":
            # Student confirmed understanding -> proceed to create and open workspace
            self.create_and_open_workspace()

        elif decision == "not_understood":
            # Student did not understand -> re-explain with simpler analogy and smaller steps
            self.robot.set_state("thinking")
            re_prompt = (
                "Koi baat nahi, main isko aur aasan tareeqe se samjhata hoon..."
                if self.language_manager.language == LanguageManager.HINGLISH
                else "No problem! Let me explain this in simpler terms with another example..."
            )
            self.robot.show_bubble(re_prompt)

            self._start_streaming_response(
                self.teaching_agent.explain_experiment_stream,
                True,
                next_action="listen",
                append_understanding_question=True,
                next_stage="awaiting_understanding",
            )

        else:
            # User asked a doubt or specific question
            self.handle_user_query(transcript)

    def create_and_open_workspace(self):
        """Creates the experiment directory, starter files, opens VS Code, and starts CodeMonitor."""
        if not self.selected_course or not self.selected_experiment:
            return

        # 1. Create workspace folder and starter files
        workspace_path = self.workspace_manager.create_experiment_workspace(
            self.selected_course,
            self.selected_experiment,
        )
        self.active_workspace_path = workspace_path

        # 2. Open workspace in VS Code and open terminal
        VSCodeManager.open_workspace(workspace_path, open_file="main.py")

        # 3. Transition message
        ready_message = self.language_manager.get_workspace_ready_message()
        self.speak_prompt(ready_message)

        # 4. Start background live code monitor
        self.start_code_monitor(workspace_path)
        self.stage = "workspace_active"

    def start_code_monitor(self, workspace_path: Path):
        if self.code_monitor and self.code_monitor.isRunning():
            self.code_monitor.stop()
            self.code_monitor.wait(1000)

        self.code_monitor = CodeMonitor(workspace_path, debounce_seconds=2.2, parent=self)
        self.code_monitor.analysis_started.connect(self.on_code_analysis_started)
        self.code_monitor.code_changed.connect(self.on_code_changed)
        self.code_monitor.start()
        print(f"[CONTROLLER] Live Code Monitor active on {workspace_path}", flush=True)

    def on_code_analysis_started(self, file_path: str):
        if not self.closing:
            self.robot.set_state("analyzing")

    def on_code_changed(self, file_path: str, content: str, changed_line: str, lineno: int):
        """Stable code modification detected. Run the 4-level mistake analysis."""
        if self.closing:
            return

        exp_name = self.selected_experiment.get("title", "") if self.selected_experiment else "Experiment"
        exp_obj = self.selected_experiment.get("description", "") if self.selected_experiment else ""

        self.analysis_worker = AnalysisWorker(
            self.logic_analyzer,
            content,
            exp_name,
            exp_obj,
            changed_line,
            lineno,
            self,
        )
        self.analysis_worker.analysis_ready.connect(self.on_analysis_result)
        self.analysis_worker.start()

    def on_analysis_result(self, result):
        if self.closing or not result:
            return

        if result.has_error:
            # Mistake found! Provide Socratic hint
            self.robot.set_state("error")
            self.robot.show_hint(result.category, result.line_number, result.hint)
            # Speak the hint without interrupting if already speaking
            if self.speaker.player.playbackState() != self.speaker.player.PlaybackState.PlayingState:
                self.speaker.speak(result.hint)
        else:
            # Code is clean and valid
            self.robot.set_state("idle")
            self.robot.status.setText("Code looking good! Keep going.")

    def handle_user_query(self, question: str):
        if not self.assistant:
            self.on_worker_error("Gemini assistant is not configured. Check GEMINI_API_KEY in .env.")
            return
        self.robot.set_state("thinking")
        in_understanding = self.stage == "awaiting_understanding"
        self._start_streaming_response(
            self.assistant.ask_stream,
            question,
            next_action="listen" if in_understanding else "idle",
            append_understanding_question=in_understanding,
        )

    def _start_streaming_response(
        self,
        stream_func,
        *args,
        next_action: str = "idle",
        append_understanding_question: bool = False,
        next_stage: str = None,
    ):
        self._stream_started = False
        self._stream_next_action = next_action
        self._stream_append_uq = append_understanding_question
        self._stream_next_stage = next_stage

        self.ask_worker = StreamAskWorker(stream_func, *args, parent=self)
        self.ask_worker.chunk_received.connect(self._on_stream_chunk)
        self.ask_worker.completed.connect(self._on_stream_completed)
        self.ask_worker.failed.connect(self.on_worker_error)
        self.ask_worker.start()

    def _on_stream_chunk(self, chunk: str):
        if self.closing:
            return
        if not self._stream_started:
            self._stream_started = True
            self.next_action = self._stream_next_action
            self.robot.set_state("speaking")
            self.robot.show_answer("")
            self.speaker.start_stream(voice=self.language_manager.voice)
        self.speaker.push_text(chunk)

    def _on_stream_completed(self, full_text: str):
        if self.closing:
            return
        if self._stream_next_stage:
            self.stage = self._stream_next_stage

        if not self._stream_started:
            self.speak_prompt(full_text, next_action=self._stream_next_action)
            return

        if self._stream_append_uq:
            q = self.language_manager.get_understanding_question()
            full_text = f"{full_text}\n\n{q}" if full_text else q
            self.speaker.push_text(f" {q}")

        self.spoken_text = full_text
        self.speaker.finish_stream()

    def on_general_answer_ready(self, answer: str):
        if self.stage == "awaiting_understanding":
            # If in understanding check, append question again
            q = self.language_manager.get_understanding_question()
            answer = f"{answer}\n\n{q}"
            self.speak_prompt(answer, next_action="listen")
        else:
            self.speak_prompt(answer, next_action="idle")

    def on_worker_error(self, error: str):
        self.robot.set_state("error")
        msg = f"Sorry, I encountered an issue: {error}"
        self.robot.show_bubble(msg, "⚠️ ERROR")
        self.speaker.speak(msg)

    # -------------------------------------------------------------------------
    # Word-by-Word Subtitle Display in Speech Bubble
    # -------------------------------------------------------------------------
    def on_sentence_started(self, index: int, sentence: str):
        self.current_sentence = sentence
        self.display_words = sentence.split()
        self.display_index = 0
        self.display_timer.start()

    def show_next_word(self):
        if self.display_index < len(self.display_words):
            self.display_index += 1
            visible = " ".join(self.display_words[:self.display_index])
            self.robot.bubble_text.setText(visible)
        else:
            self.display_timer.stop()

    def on_speech_finished(self):
        self.display_timer.stop()
        if self.spoken_text:
            self.robot.bubble_text.setText(self.spoken_text)

        action = self.next_action
        self.next_action = None

        if action == "listen":
            self.start_listening()
        else:
            self.robot.set_state("idle")

    def on_speech_error(self, message: str):
        self.display_timer.stop()
        self.robot.set_state("idle")
        print(f"[SPEECH_ERROR] {message}", flush=True)

    def on_listening_stopped(self):
        if self.robot.state == "listening":
            self.robot.set_state("idle")

    def on_listener_error(self, message: str):
        self.robot.set_state("error")
        self.robot.show_bubble(f"Microphone notice: {message}", "🎤 AUDIO")

    def go_idle(self):
        self.speaker.stop()
        if self.listener and self.listener.isRunning():
            self.listener.stop_listening()
        self.robot.set_state("idle")
        self.robot.hide_bubble()

    def exit_assistant(self):
        self.closing = True
        self.go_idle()
        if self.code_monitor and self.code_monitor.isRunning():
            self.code_monitor.stop()
            self.code_monitor.wait(1000)
        self.robot.close()
