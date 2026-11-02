import asyncio
import json
import os
import threading
import time
from urllib.parse import urlencode

import sounddevice as sd
import websockets
from websockets.exceptions import InvalidStatus
from dotenv import load_dotenv
from PySide6.QtCore import QThread, Signal


class VoiceListener(QThread):
    """One-turn Deepgram Flux Multilingual listener."""

    partial_transcript = Signal(str)
    final_transcript = Signal(str)
    listener_error = Signal(str)
    listening_started = Signal()
    listening_stopped = Signal()

    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1280  # 80 ms, mono, int16

    def __init__(self, parent=None):
        super().__init__(parent)
        load_dotenv()
        self.api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
        self._stop_event = threading.Event()
        self._loop = None
        self._audio_queue = None
        self._stream = None
        self._started_at = None

    def stop_listening(self):
        self._stop_event.set()
        if self._loop and self._audio_queue:
            try:
                self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, None)
            except (RuntimeError, asyncio.QueueFull):
                pass

    def run(self):
        if not self.api_key:
            self.listener_error.emit("DEEPGRAM_API_KEY is missing from .env")
            self.listening_stopped.emit()
            return

        self._stop_event.clear()
        self._started_at = time.perf_counter()
        try:
            asyncio.run(self._listen())
        except InvalidStatus as error:
            response = error.response
            details = getattr(response, "body", b"")
            if isinstance(details, bytes):
                details = details.decode("utf-8", errors="replace")
            self.listener_error.emit(
                "Deepgram rejected the connection. "
                f"HTTP status: {response.status_code}. "
                f"Details: {details or 'No response details'}"
            )
        except Exception as error:
            if not self._stop_event.is_set():
                self.listener_error.emit(str(error))
        finally:
            self.listening_stopped.emit()

    async def _listen(self):
        self._loop = asyncio.get_running_loop()
        self._audio_queue = asyncio.Queue(maxsize=100)
        params = {
            "model": "flux-general-multi",
            "encoding": "linear16",
            "sample_rate": str(self.SAMPLE_RATE),
        }
        url = "wss://api.deepgram.com/v2/listen?" + urlencode(params)
        headers = {"Authorization": f"Token {self.api_key}"}

        async with websockets.connect(
            url,
            additional_headers=headers,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=2,
        ) as websocket:
            print("[VOICE] Deepgram connected.", flush=True)
            self.listening_started.emit()

            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"[VOICE] Microphone: {status}", flush=True)
                if self._stop_event.is_set():
                    return
                audio = indata.copy().tobytes()
                try:
                    self._loop.call_soon_threadsafe(self._queue_audio, audio)
                except RuntimeError:
                    pass

            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=self.CHUNK_SIZE,
                latency="low",
                callback=audio_callback,
            ) as stream:
                self._stream = stream
                sender = asyncio.create_task(self._send_audio(websocket))
                receiver = asyncio.create_task(self._receive_results(websocket))
                done, pending = await asyncio.wait(
                    [sender, receiver], return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for task in done:
                    if not task.cancelled():
                        error = task.exception()
                        if error:
                            raise error
            self._stream = None

    def _queue_audio(self, audio):
        if self._audio_queue is None:
            return
        if self._audio_queue.full():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._audio_queue.put_nowait(audio)

    async def _send_audio(self, websocket):
        while True:
            audio = await self._audio_queue.get()
            if audio is None:
                break
            await websocket.send(audio)
        await websocket.send(json.dumps({"type": "CloseStream"}))

    async def _receive_results(self, websocket):
        async for message in websocket:
            data = json.loads(message)
            event_type = data.get("type", "")
            event = data.get("event", "")

            if event_type == "TurnInfo":
                transcript = (data.get("transcript") or "").strip()
                if event in ("Update", "EagerEndOfTurn"):
                    if transcript:
                        self.partial_transcript.emit(transcript)
                elif event == "EndOfTurn":
                    if transcript:
                        if self._started_at is not None:
                            elapsed = (time.perf_counter() - self._started_at) * 1000
                            print(f"[LATENCY] Deepgram final transcript: {elapsed:.0f} ms", flush=True)
                        self.final_transcript.emit(transcript)
                    self.stop_listening()
                    break
            elif event_type == "Error":
                raise RuntimeError(data.get("description", "Deepgram transcription error"))
            elif event_type == "CloseStream":
                break
