"""
Language Manager for RoboBuddy.
Manages English and Hinglish modes, voice selection, and localized responses.
"""

import re


class LanguageManager:
    ENGLISH = "english"
    HINGLISH = "hinglish"

    VOICES = {
        ENGLISH: "en-US-AndrewMultilingualNeural",
        HINGLISH: "hi-IN-MadhurNeural",
    }

    def __init__(self, default_language=ENGLISH):
        self.current_language = default_language

    def set_language(self, language: str):
        lang = language.strip().lower()
        if "hind" in lang or "hing" in lang:
            self.current_language = self.HINGLISH
        else:
            self.current_language = self.ENGLISH
        return self.current_language

    @property
    def language(self) -> str:
        return self.current_language

    @property
    def voice(self) -> str:
        return self.VOICES.get(self.current_language, self.VOICES[self.ENGLISH])

    def detect_language_switch(self, text: str) -> str | None:
        """
        Check if the user is asking to switch language.
        Returns the new language mode if detected, else None.
        """
        if not text:
            return None
        t = text.lower()

        # Hindi / Hinglish triggers
        hindi_patterns = [
            r"\bhindi\b",
            r"\bhinglish\b",
            r"hindi mein",
            r"hindi mode",
            r"hindi me",
            r"talk in hindi",
            r"speak in hindi",
            r"explain in hindi",
            r"hindi mein bolo",
            r"hindi mode on",
        ]
        for p in hindi_patterns:
            if re.search(p, t):
                return self.HINGLISH

        # English triggers
        english_patterns = [
            r"\benglish\b",
            r"english mode",
            r"talk in english",
            r"speak in english",
            r"explain in english",
            r"english mein",
            r"english mode on",
        ]
        for p in english_patterns:
            if re.search(p, t):
                return self.ENGLISH

        return None

    def get_greeting_prompt(self) -> str:
        return (
            "Hello! Welcome back. Which language would you prefer today, "
            "English or Hindi?"
        )

    def get_language_switched_message(self, new_lang: str) -> str:
        if new_lang == self.HINGLISH:
            return "Sure! Ab se main tumse Hinglish mein baat karunga. Batao, aaj kaunsa experiment seekhna hai?"
        return "Sure! Switching to English mode. Which experiment would you like to learn today?"

    def get_understanding_question(self) -> str:
        if self.current_language == self.HINGLISH:
            return "Experiment samajh aa gaya ya kisi part ko dobara explain karun?"
        return "Did you understand the experiment, or do you need me to explain anything again?"

    def get_workspace_ready_message(self) -> str:
        if self.current_language == self.HINGLISH:
            return (
                "Okay, ab tum coding start karo. Main parallel mein tumhara code "
                "analyse karta rahunga aur jab bhi koi mistake milegi, tumhe bataunga "
                "ki use kaise correct karna hai."
            )
        return (
            "Okay, start your coding. I will analyse your work in parallel and "
            "tell you whenever I find a mistake. I will guide you toward correcting it."
        )

    def get_re_explanation_prompt(self, experiment_title: str) -> str:
        if self.current_language == self.HINGLISH:
            return (
                f"Koi baat nahi! Chalo {experiment_title} ko aur aasan tareeqe se samajhte hain. "
                "Main ek practical example ke sath step-by-step explain karta hoon."
            )
        return (
            f"No problem! Let's understand {experiment_title} in simpler terms. "
            "I will break it down into smaller steps with an everyday example."
        )
