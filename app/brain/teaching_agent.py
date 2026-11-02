
import re


class TeachingAgent:

    def __init__(self, assistant):

        self.assistant = assistant

        # Active learning context
        self.course = None
        self.experiment = None

        self.current_topic = None
        self.current_lesson_step = 0

        self.last_question = None
        self.last_answer = None

        self.lesson_history = []

        self.awaiting_confirmation = False
    
    def set_lesson(self, course, experiment):

        # Do not reset context if the same lesson is already active.
        same_lesson = (
            self.course is not None
            and self.experiment is not None
            and self.course.get("name") == course.get("name")
            and self.experiment.get("number") == experiment.get("number")
        )

        if same_lesson:
            return

        self.course = course
        self.experiment = experiment

        self.current_topic = experiment.get("title", "")
        self.current_lesson_step = 0

        self.last_question = None
        self.last_answer = None

        self.lesson_history = []
        self.awaiting_confirmation = False
    # --------------------------------------------------
    # START A NEW LESSON
    # --------------------------------------------------

    def start_lesson(self, course, experiment):

        self.course = course
        self.experiment = experiment

        self.current_topic = experiment.get("title", "")
        self.current_lesson_step = 0

        self.last_question = None
        self.last_answer = None

        self.lesson_history = []

        self.awaiting_confirmation = False

        return self.ask(
            "Begin teaching me this experiment step by step."
        )

    # --------------------------------------------------
    # BUILD SYLLABUS CONTEXT
    # --------------------------------------------------

    def build_context(self):

        if not self.course or not self.experiment:
            return ""

        syllabus_text = self.course.get(
            "syllabus_text", ""
        )[:12000]

        concepts = self.experiment.get("concepts", [])

        if isinstance(concepts, list):
            concepts = ", ".join(map(str, concepts))

        return f"""
You are LabBuddy, a patient programming and laboratory teacher.

COURSE:
{self.course.get("name", "")}

SELECTED EXPERIMENT:
{self.experiment.get("number", "")}.
{self.experiment.get("title", "")}

EXPERIMENT DESCRIPTION:
{self.experiment.get("description", "")}

KEY CONCEPTS:
{concepts}

UPLOADED SYLLABUS:
{syllabus_text}
"""

    # --------------------------------------------------
    # DETECT FOLLOW-UP REQUESTS
    # --------------------------------------------------

    def detect_followup(self, question):

        text = question.lower().strip()

        patterns = {
            "continue": [
                "continue",
                "go ahead",
                "next part",
                "what next",
                "proceed",
                "move ahead"
            ],

            "example": [
                "another example",
                "give me an example",
                "show an example",
                "more examples"
            ],

            "repeat": [
                "repeat that",
                "say that again",
                "explain again",
                "repeat the explanation"
            ],

            "simplify": [
                "explain simply",
                "make it easier",
                "explain in simple words",
                "i don't understand"
            ]
        }

        for intent, phrases in patterns.items():

            if any(phrase in text for phrase in phrases):
                return intent

        return None

    # --------------------------------------------------
    # BUILD FOLLOW-UP INSTRUCTIONS
    # --------------------------------------------------

    def build_followup_instruction(self, question):

        followup = self.detect_followup(question)

        if followup == "continue":

            return """
Continue the current lesson from where you stopped.

Do not restart the experiment.
Explain the next logical concept.
Avoid repeating previously explained material.
"""

        if followup == "example":

            return """
Give another practical example of the current topic.

Explain the code and expected output step by step.
Do not restart the entire lesson.
"""

        if followup == "repeat":

            return """
Repeat and clarify your previous explanation.
Use simpler language and a different example if helpful.
"""

        if followup == "simplify":

            return """
Explain the current concept again using very simple language.
Use a beginner-friendly analogy and a small example.
"""

        return ""

    # --------------------------------------------------
    # ASK THE TEACHING MODEL
    # --------------------------------------------------

    def ask(self, question):

        if not question or not question.strip():
            return "Please tell me what you would like to learn."

        followup_instruction = (
            self.build_followup_instruction(question)
        )

        context = self.build_context()

        history = ""

        for item in self.lesson_history[-6:]:

            history += (
                f"\nStudent: {item['question']}\n"
                f"LabBuddy: {item['answer']}\n"
            )

        prompt = f"""
{context}

CURRENT LESSON STATE:

Current topic: {self.current_topic}
Lesson step: {self.current_lesson_step}

RECENT CONVERSATION:
{history}

TEACHING INSTRUCTIONS:

1. Teach like a patient programming teacher.
2. Use simple beginner-friendly language.
3. Explain concepts step by step.
4. Use practical Python examples where relevant.
5. Explain code and expected output.
6. Avoid repeating previous explanations unnecessarily.
7. Stay within the selected experiment when appropriate.
8. Do not invent syllabus requirements.
9. If syllabus information is missing, say so.
10. Use natural, voice-friendly language.

FOLLOW-UP INSTRUCTIONS:
{followup_instruction}

STUDENT'S LATEST MESSAGE:
{question}

Respond naturally as LabBuddy.
"""

        answer = self.assistant.ask(prompt)

        if not answer:
            return "I couldn't generate an explanation. Please try again."

        self.last_question = question
        self.last_answer = answer

        self.current_lesson_step += 1

        self.lesson_history.append({
            "question": question,
            "answer": answer
        })

        return answer

    # --------------------------------------------------
    # RESET LESSON
    # --------------------------------------------------

    def reset(self):

        self.course = None
        self.experiment = None

        self.current_topic = None
        self.current_lesson_step = 0

        self.last_question = None
        self.last_answer = None

        self.lesson_history = []

        self.awaiting_confirmation = False
