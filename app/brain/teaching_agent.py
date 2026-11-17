"""
Teaching Agent for RoboBuddy.
Manages step-by-step experiment explanations, analogies, and the understanding confirmation loop.
"""

import re


class TeachingAgent:
    def __init__(self, assistant, language_manager):
        self.assistant = assistant
        self.language_manager = language_manager

        self.course = None
        self.experiment = None
        self.current_step = 0
        self.explanation_attempt = 1
        self.awaiting_confirmation = False

    def set_lesson(self, course: dict, experiment: dict):
        self.course = course
        self.experiment = experiment
        self.current_step = 0
        self.explanation_attempt = 1
        self.awaiting_confirmation = False

    def build_context(self) -> str:
        if not self.experiment:
            return ""
        title = self.experiment.get("title", "Programming Experiment")
        number = self.experiment.get("number", "")
        desc = self.experiment.get("description", "")
        concepts = self.experiment.get("concepts", "")
        return (
            f"Experiment {number}: {title}\n"
            f"Objective: {desc}\n"
            f"Key Concepts: {concepts}\n"
        )

    def explain_experiment(self, re_explain: bool = False) -> str:
        """
        Explain the experiment in a structured, beginner-friendly way.
        If re_explain is True, use simpler language and a new analogy.
        """
        if not self.experiment:
            return "Please select an experiment first."

        context = self.build_context()
        lang = self.language_manager.language
        is_hinglish = "hind" in lang.lower() or "hing" in lang.lower()

        if re_explain:
            self.explanation_attempt += 1
            if is_hinglish:
                instruction = (
                    "User ko pichla explanation samajh nahi aaya. "
                    "Ab ek bilkul alag, simple real-life everyday example ya analogy ke saath "
                    "bohot aasan Hinglish mein explain karo. "
                    "Dheere-dheere explain karo aur technical jargons ko simple words mein break down karo. "
                    "Pehle wali explanation bilkul repeat mat karo."
                )
            else:
                instruction = (
                    "The student did not understand the previous explanation. "
                    "Re-explain the experiment using a completely new, everyday practical analogy and simpler words. "
                    "Break down the logic into smaller, beginner-friendly steps. "
                    "Do not repeat the exact previous explanation."
                )
        else:
            if is_hinglish:
                instruction = (
                    "Yeh experiment ek beginner student ko step by step explain karo: "
                    "1. Real-world example / practical analogy jisse concept visually clear ho. "
                    "2. Core logic aur working mechanism. "
                    "3. Algorithm / step-by-step approach. "
                    "4. Expected input aur output. "
                    "Response natural Hinglish mein rakho aur voice ke liye concise aur clear banao."
                )
            else:
                instruction = (
                    "Explain this experiment step by step for a beginner student: "
                    "1. A relatable real-world example / analogy to make the concept intuitive. "
                    "2. The core logic and working mechanism. "
                    "3. The step-by-step algorithm. "
                    "4. Expected input and output. "
                    "Keep the response voice-friendly, clear, and structured."
                )

        prompt = (
            f"CONTEXT:\n{context}\n\n"
            f"TEACHING INSTRUCTION:\n{instruction}\n\n"
            "Remember: Never provide the complete solution code. Teach the concepts."
        )

        if not self.assistant:
            self.awaiting_confirmation = True
            if is_hinglish:
                return (
                    f"Chalo Experiment {self.experiment.get('number', 1)}: {self.experiment.get('title', '')} samajhte hain.\n\n"
                    f"Objective: {self.experiment.get('description', '')}\n"
                    f"Concepts: {self.experiment.get('concepts', '')}\n\n"
                    "Step 1: Pehle problem statement aur expected output ko samjho.\n"
                    "Step 2: Logic break down karo aur step-by-step algorithm socho.\n"
                    "Step 3: Code likhte waqt har line ka purpose clear rakho."
                )
            return (
                f"Let's learn Experiment {self.experiment.get('number', 1)}: {self.experiment.get('title', '')}.\n\n"
                f"Objective: {self.experiment.get('description', '')}\n"
                f"Concepts: {self.experiment.get('concepts', '')}\n\n"
                "Step 1: Understand the core objective and expected output.\n"
                "Step 2: Break down the logic into a step-by-step algorithm.\n"
                "Step 3: Write code incrementally while verifying each logical step."
            )

        response = self.assistant.ask(prompt)
        self.awaiting_confirmation = True
        return response

    def check_understanding_response(self, text: str) -> str:
        """
        Analyze whether the student understood the explanation.
        Returns:
            'understood' -> Student understood. Proceed to workspace.
            'not_understood' -> Student has doubts or needs re-explanation.
            'other' -> User asked an unrelated or specific question.
        """
        if not text:
            return "other"
        t = text.lower().strip()

        understood_patterns = [
            r"\byes\b",
            r"\byep\b",
            r"\byeah\b",
            r"\bhaan\b",
            r"\bha\b",
            r"samajh aa gaya",
            r"samajh gaya",
            r"samajh gayi",
            r"understood",
            r"clear hai",
            r"all clear",
            r"got it",
            r"i get it",
            r"no doubts",
            r"ready to code",
            r"start coding",
            r"lets code",
            r"chalo code karein",
            r"aage badho",
            r"proceed",
        ]
        for p in understood_patterns:
            if re.search(p, t):
                return "understood"

        not_understood_patterns = [
            r"\bno\b",
            r"\bnahi\b",
            r"\bna\b",
            r"explain again",
            r"samajh nahi aaya",
            r"samajh nahi aayi",
            r"dobara samjhao",
            r"dobara explain karo",
            r"repeat",
            r"once more",
            r"phir se batao",
            r"phir se explain karo",
            r"doubt hai",
            r"not clear",
            r"confused",
            r"did not understand",
            r"didn't understand",
            r"ye part clear nahi hua",
        ]
        for p in not_understood_patterns:
            if re.search(p, t):
                return "not_understood"

        return "other"
