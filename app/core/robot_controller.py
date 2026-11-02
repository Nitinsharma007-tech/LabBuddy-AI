import json







import re







import difflib







from pathlib import Path



from app.brain.teaching_agent import TeachingAgent
from app.brain.understanding import UnderstandingEngine











from PySide6.QtCore import QObject, QThread, Signal, QTimer















from app.brain.gemini import GeminiAssistant







from app.voice.listener import VoiceListener







from app.voice.speaker import LabBuddySpeaker























BASE_DIR = Path(__file__).resolve().parents[2]







WORKSPACE_DIR = BASE_DIR / "course_workspaces"























class AskWorker(QThread):















    completed = Signal(str)







    failed = Signal(str)















    def __init__(self, assistant, question, parent=None):







        super().__init__(parent)







        self.assistant = assistant







        self.question = question















    def run(self):







        try:







            answer = self.assistant.ask(self.question)







            self.completed.emit(answer)







        except Exception as error:







            self.failed.emit(str(error))























class RobotController(QObject):















    def __init__(self, robot_window, parent=None):







        super().__init__(parent)















        self.robot = robot_window















        self.assistant = None



        self.teaching_agent = None
        # Load the semantic engine only when the first voice command arrives.
        # This keeps the robot window/startup greeting from failing during model loading.
        self.understanding = None







        self.worker = None



        self.listener = None















        self.courses = []







        self.selected_course = None







        self.selected_experiment = None















        # Conversation stages:







        # awaiting_course, awaiting_experiment, teaching







        self.stage = "awaiting_course"







        self.next_action = None















        self.last_transcript = ""







        self.current_transcript = ""







        self.spoken_text = ""















        self.display_words = []







        self.display_index = 0







        self.current_sentence = ""















        self.lesson_id = 0







        self.closing = False















        self.speaker = LabBuddySpeaker(self)















        self.display_timer = QTimer(self)







        self.display_timer.setInterval(85)







        self.display_timer.timeout.connect(self.show_next_word)















        # Speaker signals







        self.speaker.sentence_started.connect(







            self.on_sentence_started







        )







        self.speaker.speech_finished.connect(







            self.on_speech_finished







        )







        self.speaker.speech_error.connect(







            self.on_speech_error







        )















        # Robot signals







        self.robot.listen_requested.connect(







            self.start_listening







        )







        self.robot.idle_requested.connect(







            self.go_idle







        )







        self.robot.exit_requested.connect(







            self.exit_assistant







        )







        self.robot.experiment_selected.connect(







            self.on_experiment_card_selected







        )















        # Start the syllabus-aware greeting after the UI appears.







        QTimer.singleShot(700, self.start_session)















    # ==========================================







    # SYLLABUS READER







    # ==========================================















    def load_courses(self):















        self.courses = []















        if not WORKSPACE_DIR.exists():







            return















        for metadata_file in WORKSPACE_DIR.glob("*/course.json"):















            try:







                with metadata_file.open("r", encoding="utf-8") as file:







                    course = json.load(file)















                course["workspace"] = str(metadata_file.parent)















                if isinstance(course.get("experiments"), list):







                    self.courses.append(course)















            except (OSError, json.JSONDecodeError) as error:







                print(







                    f"Could not load {metadata_file}: {error}"







                )















        return self.courses















    def format_experiments(self, course):















        experiments = course.get("experiments", [])















        if not experiments:







            return "No experiments were identified in this syllabus."















        lines = []















        for experiment in experiments:















            if not isinstance(experiment, dict):







                continue















            number = experiment.get("number", "?")







            title = experiment.get("title", "Untitled experiment")















            lines.append(







                f"Experiment {number}: {title}"







            )















        return "\n".join(lines)















    # ==========================================







    # STARTUP AND GREETING







    # ==========================================



















    def start_session(self):



        if self.closing:



            return







        self.load_courses()







        # Keep the first available course ready in the background.



        # Do not open its experiment list automatically.



        if self.courses:



            self.selected_course = self.courses[0]



            self.selected_experiment = None







        self.stage = "ready"







        if not self.courses:



            message = (



                "Hello! I'm LabBuddy, your personal AI lab teacher. "



                "What would you like to do today? "



                "You can ask me a programming question or explore a course. "



                "I haven't found an uploaded syllabus yet, but I can still help."



            )



        else:



            course_name = self.selected_course.get(



                "name", "your course"



            )







            message = (



                "Hello! Welcome back to LabBuddy. "



                "I'm ready to help you learn. "



                "Would you like to explore your experiments, "



                "start a particular topic, or ask me a doubt? "



                f"I have your {course_name} course ready. "



                "What shall we do today?"



            )







        self.speak_prompt(message, next_action="listen")



















    def ask_for_experiment(self):















        if not self.selected_course:







            return















        self.selected_experiment = None















        course_name = self.selected_course.get(







            "name", "your selected course"







        )















        experiments = self.selected_course.get(







            "experiments", []







        )















        self.stage = "awaiting_experiment"















        if not experiments:















            self.stage = "teaching"















            self.speak_prompt(







                f"I've loaded your {course_name} syllabus, "







                "but couldn't identify any experiments. "







                "You can still ask me questions about the syllabus. "







                "What would you like to learn?",







                next_action="listen"







            )















            return















        # Display the large experiment selection window.







        self.robot.show_experiment_dialog(







            course_name,







            experiments







        )















        valid_count = len([







            item for item in experiments







            if isinstance(item, dict)







        ])















        message = (







            f"Hello! I've loaded your {course_name} syllabus. "







            f"I found {valid_count} experiments. "







            "The complete experiment list is now open on your screen. "







            "You can select an experiment by clicking it, "







            "or simply tell me its number, name, or topic. "







            "Which experiment would you like to learn today?"







        )















        self.speak_prompt(







            message,







            next_action="listen"







        )















    # ==========================================







    # SPEECH AND MICROPHONE







    # ==========================================















    def speak_prompt(self, message, next_action=None):















        if self.closing:







            return















        self.next_action = next_action















        self.display_timer.stop()







        self.robot.set_state("speaking")







        self.robot.show_bubble(message)















        self.speaker.speak(message)















    def start_listening(self):















        if self.closing:







            return















        if self.robot.state in (







            "listening", "thinking", "speaking"







        ):







            return















        if self.listener and self.listener.isRunning():







            return















        if self.worker and self.worker.isRunning():







            return















        self.speaker.stop()







        self.display_timer.stop()















        self.last_transcript = ""







        self.current_transcript = ""







        self.spoken_text = ""















        self.robot.set_state("listening")















        self.robot.show_bubble(







            "I'm listening. Go ahead!"







        )















        self.listener = VoiceListener(self)















        self.listener.partial_transcript.connect(







            self.on_partial_transcript







        )















        self.listener.final_transcript.connect(







            self.on_final_transcript







        )















        self.listener.listener_error.connect(







            self.on_listener_error







        )















        self.listener.listening_started.connect(







            lambda: self.robot.set_state("listening")







            if not self.closing else None







        )















        self.listener.listening_stopped.connect(







            self.on_listening_stopped







        )















        self.listener.start()















    def on_partial_transcript(self, text):















        if self.closing or not text.strip():







            return















        self.current_transcript = text.strip()















        combined = " ".join(







            part for part in (







                self.last_transcript,







                self.current_transcript







            ) if part







        )















        self.robot.show_transcript(combined)















    def on_final_transcript(self, text):















        if self.closing or not text.strip():







            return















        self.last_transcript = (







            self.last_transcript + " " + text.strip()







        ).strip()















        self.current_transcript = ""















        self.robot.show_transcript(self.last_transcript)















        question = self.last_transcript















        # Handle course selection.







        if self.stage == "awaiting_course":







            self.stop_listening()







            self.handle_course_selection(question)







            return















        # Handle experiment selection.







        if self.stage == "awaiting_experiment":







            self.stop_listening()







            self.handle_experiment_selection(question)







            return















        # Route every normal voice command through local semantic classification.
        self.stop_listening()
        self.classify_and_route(question)
        return















    def classify_and_route(self, question):
        """Classify speech locally, then dispatch to one explicit action."""
        try:
            if self.understanding is None:
                print("[LABBUDDY] Loading semantic understanding engine...")
                self.understanding = UnderstandingEngine()

            experiments = (
                self.selected_course.get("experiments", [])
                if self.selected_course else []
            )
            result = self.understanding.process(
                question,
                experiments=experiments,
                selected_experiment=self.selected_experiment
            )
            intent = result.get("intent", "unclear")
            print(
                f"[INTENT] {intent} | "
                f"confidence={result.get('confidence', 0):.3f} | "
                f"source={result.get('source', 'unknown')}"
            )
            print("[INTENT] Matched transcript:", question)

        except Exception as error:
            print("[UNDERSTANDING ERROR]", error)
            # Semantic classification must not prevent ordinary doubt handling.
            self.ask_on_gemini(question)
            return

        handlers = {
            "show_syllabus": self.handle_show_syllabus,
            "start_experiment": lambda: self.handle_start_experiment(question, result),
            "question": lambda: self.handle_doubt(question),
            "continue_lesson": self.handle_continue_lesson,
            "change_experiment": self.handle_change_experiment,
            "greeting": self.handle_greeting,
            "stop_or_idle": self.go_idle,
        }

        handler = handlers.get(intent)
        if handler:
            handler()
        else:
            # If the sentence is not confidently classified, treat it as a doubt.
            self.handle_doubt(question)

    def handle_show_syllabus(self):
        """Open the experiment/syllabus selection window."""
        self.stop_listening()
        self.ask_for_experiment()

    def handle_start_experiment(self, question, result):
        """Start a semantically matched experiment, or show choices."""
        experiment = result.get("experiment")
        if experiment is None:
            candidates = result.get("candidates", [])
            if candidates:
                experiment = candidates[0].get("experiment")

        if experiment:
            self.stop_listening()
            self.selected_experiment = experiment
            self.start_experiment_lesson()
        else:
            # A generic request such as 'I want to start an experiment'.
            self.handle_show_syllabus()

    def handle_doubt(self, question):
        """Send a programming doubt to Gemini through the existing ask pipeline."""
        self.ask_on_gemini(question)

    def ask_on_gemini(self, question):
        """Keep Gemini behind one clear function for all teaching/Q&A requests."""
        self.ask(question)

    def handle_continue_lesson(self):
        if not self.selected_experiment:
            self.speak_prompt(
                "We haven't started an experiment yet. "
                "Would you like to see the experiment list?",
                next_action="listen"
            )
            return
        self.ask_on_gemini("Continue explaining the current experiment from where we stopped.")

    def handle_change_experiment(self):
        self.handle_show_syllabus()

    def handle_greeting(self):
        self.speak_prompt(
            "Hello! I'm ready. Would you like to explore an experiment "
            "or ask me a programming doubt?",
            next_action="listen"
        )

    def stop_listening(self):















        if self.listener and self.listener.isRunning():







            self.listener.stop_listening()















    def on_listening_stopped(self):















        if self.robot.state == "listening":







            self.robot.set_state("idle")















    def on_listener_error(self, message):















        if self.closing:







            return















        self.robot.set_state("error")















        self.robot.show_bubble(







            "Microphone / Deepgram error:\n" + message







        )















    # ==========================================







    # COURSE SELECTION







    # ==========================================















    def normalize(self, text):















        text = text.lower()







        text = re.sub(r"[^a-z0-9\s]", " ", text)















        return " ".join(text.split())















    def handle_course_selection(self, transcript):















        transcript = self.normalize(transcript)















        # Number-based selection: "course 2", "number 2", etc.







        number_match = re.search(







            r"\b(?:course|number|option)?\s*(\d+)\b",







            transcript







        )















        if number_match:















            index = int(number_match.group(1)) - 1















            if 0 <= index < len(self.courses):







                self.selected_course = self.courses[index]







                self.ask_for_experiment()







                return















        # Name-based selection.







        course_names = [







            self.normalize(







                course.get("name", "")







            )







            for course in self.courses







        ]















        for index, name in enumerate(course_names):















            if name and (







                name in transcript or transcript in name







            ):







                self.selected_course = self.courses[index]







                self.ask_for_experiment()







                return















        matches = difflib.get_close_matches(







            transcript,







            course_names,







            n=1,







            cutoff=0.45







        )















        if matches:















            index = course_names.index(matches[0])







            self.selected_course = self.courses[index]







            self.ask_for_experiment()







            return















        self.speak_prompt(







            "Sorry, I couldn't identify that course. "







            "Please say the course name or its number.",







            next_action="listen"







        )















    # ==========================================







    # EXPERIMENT SELECTION







    # ==========================================















    def on_experiment_card_selected(self, number):















        if self.closing or not self.selected_course:







            return















        self.stop_listening()















        experiments = self.selected_course.get(







            "experiments", []







        )















        for experiment in experiments:















            if not isinstance(experiment, dict):







                continue















            try:







                if int(experiment.get("number")) == int(number):















                    self.selected_experiment = experiment















                    self.robot.close_experiment_dialog()















                    self.start_experiment_lesson()







                    return















            except (TypeError, ValueError):







                continue























    def number_words_to_digits(self, text):















        number_words = {







            "zero": "0",







            "one": "1",







            "first": "1",







            "two": "2",







            "second": "2",







            "three": "3",







            "third": "3",







            "four": "4",







            "fourth": "4",







            "five": "5",







            "fifth": "5",







            "six": "6",







            "sixth": "6",







            "seven": "7",







            "seventh": "7",







            "eight": "8",







            "eighth": "8",







            "nine": "9",







            "ninth": "9",







            "ten": "10",







            "tenth": "10",







            "eleven": "11",







            "eleventh": "11",







            "twelve": "12",







            "twelfth": "12",







        }















        result = text.lower()















        for word, digit in number_words.items():















            result = re.sub(







                rf"\b{word}\b",







                digit,







                result







            )















        return result























    def handle_experiment_selection(self, transcript):















        if not self.selected_course:







            self.start_session()







            return















        experiments = [







            item







            for item in self.selected_course.get("experiments", [])







            if isinstance(item, dict)







        ]















        if not experiments:







            return















        original_transcript = transcript















        transcript = self.number_words_to_digits(







            transcript







        )















        normalized = self.normalize(transcript)















        # ----------------------------------







        # 1. EXPERIMENT NUMBER RECOGNITION







        # ----------------------------------















        number_match = re.search(







            r"\b(?:experiment|experiments|exp|number|no|option)?\s*(\d{1,2})\b",







            normalized







        )















        if number_match:















            requested_number = int(number_match.group(1))















            for experiment in experiments:















                try:







                    experiment_number = int(







                        experiment.get("number")







                    )















                    if experiment_number == requested_number:















                        self.selected_experiment = experiment















                        self.robot.close_experiment_dialog()















                        self.start_experiment_lesson()







                        return















                except (TypeError, ValueError):







                    continue















        # ----------------------------------







        # 2. COMMON EXPERIMENT ALIASES







        # ----------------------------------















        aliases = {















            1: [







                "python basics",







                "basic python",







                "python introduction",







                "python setup",







                "input output"







            ],















            2: [







                "operators",







                "type conversion",







                "data types"







            ],















            3: [







                "conditions",







                "conditional statements",







                "if else",







                "even odd",







                "largest number"







            ],















            4: [







                "loops",







                "loop",







                "patterns",







                "pattern printing",







                "multiplication table",







                "factorial"







            ],















            5: [







                "strings",







                "string",







                "string basics",







                "palindrome",







                "reverse string",







                "vowels",







                "character frequency"







            ],















            6: [







                "lists",







                "list",







                "tuples",







                "tuple",







                "sets",







                "set",







                "dictionary",







                "dictionaries",







                "collections"







            ],















            7: [







                "functions",







                "function",







                "recursion",







                "fibonacci"







            ],















            8: [







                "file handling",







                "files",







                "exception handling"







            ],















            9: [







                "oops",







                "oop",







                "object oriented",







                "classes",







                "objects",







                "inheritance"







            ],















            10: [







                "numpy",







                "arrays",







                "array operations"







            ],















            11: [







                "pandas",







                "dataframe",







                "data analysis"







            ],















            12: [







                "matplotlib",







                "visualization",







                "visualisation",







                "graphs",







                "plots",







                "plotting"







            ]







        }















        for number, phrases in aliases.items():















            matched = any(







                self.normalize(phrase) in normalized







                for phrase in phrases







            )















            if matched:















                for experiment in experiments:















                    try:







                        if int(experiment.get("number")) == number:















                            self.selected_experiment = experiment















                            self.robot.close_experiment_dialog()















                            self.start_experiment_lesson()







                            return















                    except (TypeError, ValueError):







                        continue















        # ----------------------------------







        # 3. PARTIAL TITLE / DESCRIPTION MATCH







        # ----------------------------------















        stop_words = {







            "i", "we", "you", "the", "a", "an",







            "to", "do", "want", "would", "like",







            "lets", "let", "can", "could", "will",







            "study", "learn", "start", "please",







            "about", "with", "for", "of", "and",







            "experiment", "experiments", "exp",







            "number", "this", "that", "one",







            "today", "me", "shall"







        }















        query_tokens = {







            token







            for token in normalized.split()







            if token not in stop_words and len(token) > 1







        }















        scored_experiments = []















        for experiment in experiments:















            title = self.normalize(







                str(experiment.get("title", ""))







            )















            description = self.normalize(







                str(experiment.get("description", ""))







            )















            concepts = self.normalize(







                str(experiment.get("concepts", ""))







            )















            title_tokens = set(title.split())















            all_tokens = set(







                (title + " " + description + " " + concepts).split()







            )















            title_overlap = len(query_tokens & title_tokens)















            total_overlap = len(query_tokens & all_tokens)















            score = (







                title_overlap * 3







                + total_overlap







            )















            if title and title in normalized:







                score += 10















            scored_experiments.append(







                (score, experiment)







            )















        scored_experiments.sort(







            key=lambda item: item[0],







            reverse=True







        )















        if scored_experiments:















            best_score, best_experiment = scored_experiments[0]















            second_score = (







                scored_experiments[1][0]







                if len(scored_experiments) > 1







                else 0







            )















            if best_score >= 2 and (







                best_score - second_score >= 1







            ):















                self.selected_experiment = best_experiment















                self.robot.close_experiment_dialog()















                self.start_experiment_lesson()







                return















        # ----------------------------------







        # 4. NO CONFIDENT MATCH







        # ----------------------------------















        self.speak_prompt(







            f"I heard: {original_transcript}. "







            "I couldn't confidently identify the experiment. "







            "Please say its number, a few words from its name, "







            "or select it from the experiment window.",







            next_action="listen"







        )















        # ==========================================







        # START EXPERIMENT LESSON







        # ==========================================















    def start_experiment_lesson(self):















        course = self.selected_course







        experiment = self.selected_experiment















        if not course or not experiment:







            return







        self.robot.close_experiment_dialog()















        self.stage = "teaching"















        title = experiment.get(







            "title", "Selected experiment"







        )















        message = (







            f"Excellent choice! Let's learn "







            f"{title}. I'll explain it step by step. "







            "Let's begin!"







        )















        self.speak_prompt(







            message,







            next_action="teach_experiment"







        )















    def build_experiment_question(self):















        course = self.selected_course







        experiment = self.selected_experiment















        syllabus_text = course.get(







            "syllabus_text", ""







        )















        # Keep the context bounded.







        syllabus_text = syllabus_text[:12000]















        experiment_context = ""















        if experiment:















            experiment_context = f"""







Selected experiment:







Number: {experiment.get('number', '')}







Title: {experiment.get('title', '')}







Description: {experiment.get('description', '')}







Key concepts: {experiment.get('concepts', '')}







"""















        return f"""







You are LabBuddy, a patient programming and laboratory teacher.















Teach the student using the following uploaded syllabus context.















Course: {course.get('name', '')}







Syllabus file: {course.get('filename', '')}















{experiment_context}















Uploaded syllabus content:







{syllabus_text}















Teaching instructions:







1\\\. Focus on the selected experiment.







2\\\. Explain its aim and objectives.







3\\\. Explain the theory in simple language.







4\\\. Explain the required concepts.







5\\\. Give the algorithm or procedure.







6\\\. Provide practical code when relevant.







7\\\. Explain the code step by step.







8\\\. Explain expected output.







9\\\. Include common mistakes and important viva questions.







10\\\. Use simple, friendly, voice-friendly language.







11\\\. Do not invent syllabus requirements.







12\\\. If information is missing from the syllabus, clearly say so.















Start teaching the selected experiment now.







"""















    # ==========================================







    # GEMINI







    # ==========================================















    def ask(self, question):







        if self.closing or not question.strip():



            return







        if self.worker and self.worker.isRunning():



            return







        self.stop_listening()







        self.lesson_id += 1



        self.spoken_text = ""







        self.robot.set_state("thinking")







        self.robot.show_bubble(



            "I'm preparing a step-by-step lesson for you..."



        )







        # Initialize Gemini only once.



        if self.assistant is None:







            try:



                self.assistant = GeminiAssistant()







            except Exception as error:



                self.on_error(str(error))



                return







        # Initialize Teaching Agent only once.



        if self.teaching_agent is None:







            self.teaching_agent = TeachingAgent(



                self.assistant



            )







        # Synchronize the active lesson without resetting



        # its history on every question.



        if self.selected_course and self.selected_experiment:







            self.teaching_agent.set_lesson(



                self.selected_course,



                self.selected_experiment



            )







        # Teaching Agent now builds the syllabus-aware prompt.



        self.worker = AskWorker(



            self.teaching_agent,



            question,



            self



        )







        self.worker.completed.connect(self.on_answer)



        self.worker.failed.connect(self.on_error)







        self.worker.finished.connect(



            self.on_worker_finished



        )







        self.worker.finished.connect(



            self.worker.deleteLater



        )







        self.worker.start()















    def on_worker_finished(self):















        self.worker = None















    # ==========================================







    # TEACHER MODE AND EDGE TTS







    # ==========================================















    def on_answer(self, answer):















        if self.closing or not answer.strip():







            return















        self.robot.set_state("speaking")







        self.spoken_text = ""















        self.robot.show_answer(







            "Let me explain this to you step by step..."







        )















        self.speaker.speak(answer)















    def on_sentence_started(self, index, sentence):















        if self.closing:







            return















        self.current_sentence = sentence







        self.display_words = sentence.split()







        self.display_index = 0















        self.display_timer.stop()















        if self.spoken_text:







            self.spoken_text += "\n\n"















        self.display_timer.start()















    def show_next_word(self):















        if self.display_index >= len(self.display_words):







            self.display_timer.stop()







            return















        self.display_index += 1















        current_sentence = " ".join(







            self.display_words[:self.display_index]







        )















        visible_text = (







            self.spoken_text + current_sentence







        )















        self.robot.show_answer(visible_text)















        if self.display_index == len(self.display_words):















            self.spoken_text += current_sentence







            self.display_timer.stop()















    def on_speech_finished(self):















        if self.closing:







            return















        self.display_timer.stop()















        action = self.next_action







        self.next_action = None















        if action == "listen":















            self.robot.set_state("idle")















            QTimer.singleShot(







                400,







                self.start_listening







            )







            return















        if action == "teach_experiment":















            self.next_action = None















            self.ask(







                "Please begin teaching me the selected experiment."







            )







            return















        self.robot.set_state("idle")















        self.robot.show_bubble(







            "I'm ready! Click me whenever you want to "







            "continue learning or ask another question."







        )























    def on_speech_error(self, message):















        if self.closing:







            return















        self.display_timer.stop()















        self.robot.set_state("idle")















        self.robot.show_bubble(







            "I prepared your lesson, but voice playback "







            "is temporarily unavailable.\n\n"







            "You can still read the explanation above "







            "and click me to continue learning."







        )















        print("Edge TTS playback error:", message)















    # ==========================================







    # IDLE MODE







    # ==========================================















    def go_idle(self):















        if self.closing:







            return















        self.lesson_id += 1















        self.stop_listening()







        self.speaker.stop()















        self.display_timer.stop()















        self.last_transcript = ""







        self.current_transcript = ""







        self.spoken_text = ""







        self.next_action = None















        self.robot.hide_bubble()







        self.robot.set_state("idle")















    # ==========================================







    # ERRORS







    # ==========================================















    def on_error(self, message):















        if self.closing:







            return















        self.display_timer.stop()







        self.robot.set_state("error")















        self.robot.show_bubble(







            "Assistant error:\n" + message







        )















    # ==========================================







    # EXIT







    # ==========================================















    def exit_assistant(self):















        if self.closing:







            return















        self.closing = True







        self.lesson_id += 1















        self.display_timer.stop()















        self.stop_listening()







        self.speaker.stop()















        worker = self.worker















        if worker is not None:















            try:







                if worker.isRunning():







                    worker.wait(3000)







            except RuntimeError:







                pass















        self.robot.close()
