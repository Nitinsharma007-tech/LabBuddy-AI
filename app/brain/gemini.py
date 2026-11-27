import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.brain.programming_prompt import get_system_prompt


class GeminiAssistant:
    def __init__(self, language="english"):
        load_dotenv()

        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

        self.client = genai.Client(api_key=self.api_key)
        self.language = language
        self.history = []

        config_kwargs = {
            "temperature": 0.3,
            "max_output_tokens": 900,
        }
        if "2.5" in self.model and hasattr(types, "ThinkingConfig"):
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        self.config = types.GenerateContentConfig(**config_kwargs)

    def set_language(self, language: str):
        self.language = language

    def _build_ask_prompt(self, question: str, custom_system_prompt: str = None) -> str:
        sys_prompt = custom_system_prompt or get_system_prompt(self.language)

        conversation = []
        for message in self.history[-6:]:
            role = "Student" if message["role"] == "user" else "RoboBuddy"
            conversation.append(f"{role}: {message['text']}")

        conversation.append(f"Student: {question}")

        return (
            f"{sys_prompt}\n\n"
            "Keep the answer concise, encouraging, and voice-friendly. "
            "Explain one concept at a time. Never dump ready-made solutions.\n\n"
            "Conversation:\n"
            + "\n\n".join(conversation)
            + "\n\nRoboBuddy:"
        )

    def _record_turn(self, question: str, answer: str):
        self.history.extend([
            {"role": "user", "text": question},
            {"role": "assistant", "text": answer},
        ])
        self.history = self.history[-8:]

    def ask(self, question: str, custom_system_prompt: str = None) -> str:
        question = (question or "").strip()
        if not question:
            return "Please ask a programming question."

        prompt = self._build_ask_prompt(question, custom_system_prompt)
        started = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config,
            )
            answer = (response.text or "").strip()

            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"[LATENCY] Gemini complete: {elapsed_ms:.0f} ms (model={self.model})", flush=True)

            if not answer:
                return "I couldn't generate a response. Please try asking in another way."

            self._record_turn(question, answer)
            return answer

        except Exception as error:
            print(f"Gemini Error ({self.model}): {error}", flush=True)
            raise

    def ask_stream(self, question: str, custom_system_prompt: str = None):
        """Yield response text chunks as Gemini streams them for low-latency TTS."""
        question = (question or "").strip()
        if not question:
            yield "Please ask a programming question."
            return

        prompt = self._build_ask_prompt(question, custom_system_prompt)
        started = time.perf_counter()
        first_token_logged = False
        chunks = []

        try:
            stream = self.client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=self.config,
            )
            for chunk in stream:
                text = getattr(chunk, "text", None) or ""
                if not text:
                    continue
                if not first_token_logged:
                    ttft_ms = (time.perf_counter() - started) * 1000
                    print(f"[LATENCY] Gemini first token: {ttft_ms:.0f} ms (model={self.model})", flush=True)
                    first_token_logged = True
                chunks.append(text)
                yield text

            answer = "".join(chunks).strip()
            elapsed_ms = (time.perf_counter() - started) * 1000
            print(f"[LATENCY] Gemini complete: {elapsed_ms:.0f} ms (model={self.model})", flush=True)

            if not answer:
                fallback = "I couldn't generate a response. Please try asking in another way."
                yield fallback
                return

            self._record_turn(question, answer)

        except Exception as error:
            print(f"Gemini Error ({self.model}): {error}", flush=True)
            raise

    def analyze_logical_mistake(
        self,
        experiment_name: str,
        experiment_objective: str,
        code_context: str,
        changed_line: str,
        line_number: int,
        hint_level: int = 1,
    ) -> str:
        """
        Analyze a logical mistake and produce a Socratic hint without providing the solution.
        """
        sys_prompt = get_system_prompt(self.language)
        lang_note = (
            "Explain in natural Hinglish."
            if "hind" in self.language.lower() or "hing" in self.language.lower()
            else "Explain in English."
        )

        prompt = f"""{sys_prompt}

You are observing a student writing code for the experiment: '{experiment_name}'.
Experiment Objective: {experiment_objective}

STUDENT'S CODE:
```python
{code_context}
```

The issue seems to be around line {line_number}:
`{changed_line}`

TASK:
Provide Socratic Hint #{hint_level} for this logical mistake.
{lang_note}

STRICT CONSTRAINTS:
1. NEVER write or show the corrected code.
2. NEVER write the replacement statement.
3. Mention line {line_number}.
4. Point out what assumption or logic is flawed.
5. Ask a guiding question or give a conceptual hint so the student fixes it on their own.
6. Keep the response to 2 to 4 sentences so it is voice-friendly.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config,
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"Error analyzing logical mistake: {e}", flush=True)
            return (
                f"I noticed a potential issue on line {line_number}. "
                "Check the condition logic and verify if it matches the expected experiment behavior."
            )

    def clear_history(self):
        self.history.clear()
