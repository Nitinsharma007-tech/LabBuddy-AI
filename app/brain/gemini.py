
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.brain.programming_prompt import PROGRAMMING_SYSTEM_PROMPT


class GeminiAssistant:

    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash"
        ).strip()

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Check your .env file."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.history = []

        # Compatible generation configuration.
        self.config = types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=900
        )

    def ask(self, question):

        question = (question or "").strip()

        if not question:
            return "Please ask me a programming question."

        conversation = []

        for message in self.history[-6:]:

            role = (
                "Student"
                if message["role"] == "user"
                else "LabBuddy"
            )

            conversation.append(
                f"{role}: {message['text']}"
            )

        conversation.append(
            f"Student: {question}"
        )

        prompt = (
            f"{PROGRAMMING_SYSTEM_PROMPT}\n\n"
            "Keep the answer focused, clear, and voice-friendly. "
            "Use short paragraphs and explain one idea at a time. "
            "Avoid unnecessary introductions.\n\n"
            "Conversation:\n"
            + "\n\n".join(conversation)
            + "\n\nLabBuddy:"
        )

        started = time.perf_counter()

        try:

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config
            )

            answer = (response.text or "").strip()

            elapsed_ms = (
                time.perf_counter() - started
            ) * 1000

            print(
                f"[LATENCY] Gemini complete: "
                f"{elapsed_ms:.0f} ms "
                f"(model={self.model})",
                flush=True
            )

            if not answer:
                return (
                    "I couldn't generate a response. "
                    "Please try asking in another way."
                )

            self.history.extend([
                {
                    "role": "user",
                    "text": question
                },
                {
                    "role": "assistant",
                    "text": answer
                }
            ])

            self.history = self.history[-8:]

            return answer

        except Exception as error:

            print(
                f"Gemini Error ({self.model}): {error}",
                flush=True
            )

            raise

    def clear_history(self):
        self.history.clear()
