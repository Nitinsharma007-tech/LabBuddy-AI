import asyncio
import http.client
import json
import os
import queue
import re
import subprocess
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
import edge_tts
from PySide6.QtCore import QObject, QThread, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class SentenceGenerator(QThread):
    """Background TTS worker that synthesizes sentences from a streaming queue."""

    sentence_ready = Signal(int, str, str)
    generation_finished = Signal()
    generation_error = Signal(str)

    FALLBACK_VOICES = {
        "en": "en-IN-PrabhatNeural",
        "hi": "hi-IN-SwaraNeural",
    }

    def __init__(self, voice, rate, parent=None):
        super().__init__(parent)
        load_dotenv()
        self.voice = voice
        self.rate = rate
        self.cancelled = False
        self.files = []
        self._queue = queue.Queue()
        self._dg_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
        self._dg_model = os.getenv("DEEPGRAM_TTS_MODEL", "aura-orion-en").strip()
        self._tts_provider = os.getenv("TTS_PROVIDER", "auto").strip().lower()
        self._dg_conn = None

    def enqueue(self, index: int, sentence: str):
        if not self.cancelled:
            self._queue.put((index, sentence))

    def finish(self):
        self._queue.put(None)

    def cancel(self):
        self.cancelled = True
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._process_queue())
            self.generation_finished.emit()
        except Exception as error:
            if not self.cancelled:
                self.generation_error.emit(str(error))
            self.generation_finished.emit()
        finally:
            if self._dg_conn is not None:
                try:
                    self._dg_conn.close()
                except Exception:
                    pass
                self._dg_conn = None
            try:
                loop.close()
            except Exception:
                pass

    async def _process_queue(self):
        while not self.cancelled:
            item = await asyncio.get_running_loop().run_in_executor(
                None, self._queue.get
            )
            if item is None or self.cancelled:
                break

            index, sentence = item
            if not re.search(r"[A-Za-z0-9\u0900-\u097F]", sentence):
                continue

            fd, path = tempfile.mkstemp(prefix="labbuddy_", suffix=".mp3")
            os.close(fd)
            self.files.append(path)

            started = time.perf_counter()
            audio_path = await self._synthesize_with_fallback(sentence, path)
            if audio_path is None or self.cancelled:
                continue

            elapsed = (time.perf_counter() - started) * 1000
            print(f"[LATENCY] TTS sentence {index + 1}: {elapsed:.0f} ms", flush=True)

            if not self.cancelled:
                self.sentence_ready.emit(index, sentence, audio_path)

    def _synthesize_deepgram_aura(self, sentence: str, mp3_path: str) -> bool:
        if not self._dg_key:
            return False
        for attempt in range(2):
            if self.cancelled:
                return False
            try:
                if self._dg_conn is None:
                    self._dg_conn = http.client.HTTPSConnection("api.deepgram.com", timeout=8)
                self._dg_conn.request(
                    "POST",
                    f"/v1/speak?model={self._dg_model}",
                    body=json.dumps({"text": sentence}),
                    headers={
                        "Authorization": f"Token {self._dg_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp = self._dg_conn.getresponse()
                data = resp.read()
                if resp.status == 200 and data:
                    with open(mp3_path, "wb") as f:
                        f.write(data)
                    return True
                print(f"[TTS] Deepgram Aura HTTP {resp.status}", flush=True)
            except Exception as err:
                if self._dg_conn is not None:
                    try:
                        self._dg_conn.close()
                    except Exception:
                        pass
                    self._dg_conn = None
                if attempt == 1:
                    print(f"[TTS] Deepgram Aura failed: {err}", flush=True)
        return False

    async def _synthesize_with_fallback(self, sentence: str, mp3_path: str):
        lang_prefix = "hi" if self.voice.startswith("hi-") else "en"

        # Fast path: Deepgram Aura TTS for English (~450ms per sentence)
        if lang_prefix == "en" and self._dg_key and self._tts_provider != "edge":
            ok = await asyncio.get_running_loop().run_in_executor(
                None, self._synthesize_deepgram_aura, sentence, mp3_path
            )
            if ok:
                return mp3_path

        fallback_voice = self.FALLBACK_VOICES.get(lang_prefix, "en-IN-PrabhatNeural")
        voices_to_try = [self.voice]
        if fallback_voice != self.voice:
            voices_to_try.append(fallback_voice)

        for voice in voices_to_try:
            for attempt in range(2):
                if self.cancelled:
                    return None
                try:
                    communicate = edge_tts.Communicate(
                        text=sentence,
                        voice=voice,
                        rate=self.rate,
                    )
                    await communicate.save(mp3_path)
                    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                        return mp3_path
                except Exception as err:
                    if attempt == 0 and not self.cancelled:
                        await asyncio.sleep(0.15)
                    else:
                        print(f"[TTS] Edge-TTS ({voice}) failed: {err}", flush=True)

        # Offline Windows SAPI fallback so speech never fails silently
        wav_path = mp3_path[:-4] + ".wav"
        self.files.append(wav_path)
        if await asyncio.get_running_loop().run_in_executor(
            None, self._synthesize_windows_sapi, sentence, wav_path
        ):
            return wav_path

        raise RuntimeError("No audio was received from Edge-TTS or Windows Speech fallback.")

    @staticmethod
    def _synthesize_windows_sapi(sentence: str, wav_path: str) -> bool:
        if os.name != "nt":
            return False
        try:
            escaped_path = wav_path.replace("'", "''")
            escaped_text = sentence.replace("'", "''")
            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Rate = 2; "
                f"$s.SetOutputToWaveFile('{escaped_path}'); "
                f"$s.Speak('{escaped_text}'); "
                "$s.Dispose()"
            )
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=10,
                creationflags=creationflags,
            )
            return res.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0
        except Exception:
            return False


class LabBuddySpeaker(QObject):
    """Low-latency streaming text-to-speech player."""

    sentence_started = Signal(int, str)
    speech_finished = Signal()
    speech_error = Signal(str)

    def __init__(self, parent=None, voice=None, rate=None):
        super().__init__(parent)

        self.voice = (
            voice
            or os.getenv("EDGE_TTS_VOICE", "en-IN-PrabhatNeural").strip()
        )
        self.rate = (
            rate
            or os.getenv("EDGE_TTS_RATE", "+20%").strip()
        )

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(self.on_player_error)

        self.worker = None
        self.ready = {}
        self.current_index = 0
        self.enqueued_count = 0
        self.stream_ended = False
        self.generation_done = False
        self.active_paths = set()
        self.cancelled = False

        # Streaming text accumulator
        self._text_buffer = ""
        self._in_code_block = False

        print(f"[VOICE] Voice: {self.voice}", flush=True)
        print(f"[VOICE] Rate: {self.rate}", flush=True)

    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r"```.*?```", " Code example omitted from speech. ", text, flags=re.S)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"[*_#>]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def split_sentences(cls, text: str):
        clean = cls.clean_text(text)
        if not clean:
            return []

        parts = re.split(r"(?<=[.!?])\s+", clean)
        result = []
        buffer = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue
            buffer = f"{buffer} {part}".strip() if buffer else part
            # Flush the first sentence immediately for minimal time-to-first-audio
            limit = 40 if not result else 160
            if len(buffer) >= limit:
                result.append(buffer)
                buffer = ""

        if buffer:
            result.append(buffer)
        return result

    def set_voice(self, voice: str):
        if voice:
            self.voice = voice

    def start_stream(self, voice=None):
        """Start a new streaming TTS session."""
        if voice:
            self.voice = voice

        self.stop()
        self.cancelled = False
        self.ready = {}
        self.current_index = 0
        self.enqueued_count = 0
        self.stream_ended = False
        self.generation_done = False
        self.active_paths = set()
        self._text_buffer = ""
        self._in_code_block = False

        self.worker = SentenceGenerator(self.voice, self.rate, self)
        self.worker.sentence_ready.connect(self.on_sentence_ready)
        self.worker.generation_finished.connect(self.on_generation_finished)
        self.worker.generation_error.connect(self.speech_error)
        self.worker.start()

    def push_text(self, chunk: str):
        """Feed streamed LLM text chunks; complete sentences are queued for TTS immediately."""
        if self.cancelled or not chunk or not self.worker:
            return

        self._text_buffer += chunk

        # Strip fenced code blocks incrementally
        while "```" in self._text_buffer:
            if not self._in_code_block:
                idx = self._text_buffer.index("```")
                before = self._text_buffer[:idx]
                self._text_buffer = self._text_buffer[idx + 3:]
                self._in_code_block = True
                self._flush_sentences_from(before + " Code example omitted from speech. ")
            else:
                idx = self._text_buffer.index("```")
                self._text_buffer = self._text_buffer[idx + 3:]
                self._in_code_block = False

        if self._in_code_block:
            return

        self._flush_buffer_ready_parts()

    def _flush_sentences_from(self, text: str):
        for s in self.split_sentences(text):
            self._enqueue_sentence(s)

    def _flush_buffer_ready_parts(self):
        # For the very first sentence, also allow clause breaks after 55 chars
        while True:
            match = re.search(r"([.!?](?:\s|$)|\n+)", self._text_buffer)
            if not match and self.enqueued_count == 0 and len(self._text_buffer) >= 55:
                match = re.search(r"([,;:]\s+)", self._text_buffer[35:])
                if match:
                    end_pos = 35 + match.end()
                    chunk = self._text_buffer[:end_pos].strip()
                    self._text_buffer = self._text_buffer[end_pos:]
                    clean = self.clean_text(chunk)
                    if clean:
                        self._enqueue_sentence(clean)
                    continue
            if not match:
                break

            end_pos = match.end()
            # Keep accumulating if subsequent sentences are tiny, except for the very first chunk
            if self.enqueued_count > 0 and end_pos < 80:
                next_match = re.search(r"([.!?](?:\s|$)|\n+)", self._text_buffer[end_pos:])
                if not next_match:
                    break
                end_pos += next_match.end()

            chunk = self._text_buffer[:end_pos].strip()
            self._text_buffer = self._text_buffer[end_pos:]
            clean = self.clean_text(chunk)
            if clean:
                self._enqueue_sentence(clean)

    def _enqueue_sentence(self, sentence: str):
        if self.cancelled or not self.worker:
            return
        idx = self.enqueued_count
        self.enqueued_count += 1
        self.worker.enqueue(idx, sentence)

    def finish_stream(self):
        """Flush any remaining buffered text and signal end of stream."""
        if self.cancelled or not self.worker:
            return
        if not self._in_code_block and self._text_buffer.strip():
            for s in self.split_sentences(self._text_buffer):
                self._enqueue_sentence(s)
        self._text_buffer = ""
        self._in_code_block = False
        self.stream_ended = True

        if self.enqueued_count == 0:
            self.worker.finish()
            self.speech_finished.emit()
            return

        self.worker.finish()

    def speak(self, text: str, voice=None):
        """Speak a complete text string immediately."""
        self.start_stream(voice=voice)
        sentences = self.split_sentences(text)
        if not sentences:
            self.stream_ended = True
            self.worker.finish()
            self.speech_finished.emit()
            return
        for s in sentences:
            self._enqueue_sentence(s)
        self.stream_ended = True
        self.worker.finish()

    def on_sentence_ready(self, index: int, sentence: str, path: str):
        if self.cancelled:
            self.remove_file(path)
            return
        self.ready[index] = (sentence, path)
        self.play_if_ready()

    def play_if_ready(self):
        if self.cancelled:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return

        item = self.ready.pop(self.current_index, None)
        if item is None:
            self.finish_if_complete()
            return

        sentence, path = item
        self.active_paths.add(path)
        self.sentence_started.emit(self.current_index, sentence)

        self.player.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        self.player.play()

        if self.current_index == 0:
            print("[LATENCY] First audio playback started.", flush=True)

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.current_index += 1
            self.play_if_ready()

    def on_generation_finished(self):
        self.generation_done = True
        self.finish_if_complete()

    def finish_if_complete(self):
        if (
            not self.cancelled
            and self.stream_ended
            and self.generation_done
            and self.current_index >= self.enqueued_count
            and self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState
        ):
            self.player.setSource(QUrl())
            self.cleanup_files()
            self.speech_finished.emit()

    def on_player_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError and not self.cancelled:
            self.speech_error.emit(error_string or "Audio playback failed.")

    def stop(self):
        self.cancelled = True
        self.player.stop()
        self.player.setSource(QUrl())

        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)

        self.cleanup_files()
        self.ready.clear()
        self.enqueued_count = 0
        self.current_index = 0
        self.stream_ended = False
        self.generation_done = False
        self._text_buffer = ""
        self._in_code_block = False

    def cleanup_files(self):
        paths = set(self.active_paths)
        paths.update(path for _, path in self.ready.values())
        if self.worker:
            paths.update(getattr(self.worker, "files", []))

        for path in paths:
            self.remove_file(path)
        self.active_paths.clear()

    @staticmethod
    def remove_file(path):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
