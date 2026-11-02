
import asyncio
import os
import re
import tempfile
import time

from pathlib import Path

import edge_tts

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    QUrl
)

from PySide6.QtMultimedia import (
    QAudioOutput,
    QMediaPlayer
)


class SentenceGenerator(QThread):

    sentence_ready = Signal(int, str, str)
    generation_finished = Signal()
    generation_error = Signal(str)

    def __init__(
        self,
        sentences,
        voice,
        rate,
        parent=None
    ):

        super().__init__(parent)

        self.sentences = sentences
        self.voice = voice
        self.rate = rate

        self.cancelled = False
        self.files = []

    def cancel(self):
        self.cancelled = True

    def run(self):

        try:

            for index, sentence in enumerate(
                self.sentences
            ):

                if self.cancelled:
                    break

                fd, path = tempfile.mkstemp(
                    prefix="labbuddy_",
                    suffix=".mp3"
                )

                os.close(fd)

                self.files.append(path)

                started = time.perf_counter()

                try:

                    asyncio.run(
                        self.generate_audio(
                            sentence,
                            path
                        )
                    )

                except Exception:

                    if self.cancelled:
                        break

                    time.sleep(0.2)

                    asyncio.run(
                        self.generate_audio(
                            sentence,
                            path
                        )
                    )

                elapsed = (
                    time.perf_counter() - started
                ) * 1000

                print(
                    f"[LATENCY] TTS sentence "
                    f"{index + 1}: {elapsed:.0f} ms",
                    flush=True
                )

                if not self.cancelled:

                    self.sentence_ready.emit(
                        index,
                        sentence,
                        path
                    )

            self.generation_finished.emit()

        except Exception as error:

            self.generation_error.emit(str(error))

            self.generation_finished.emit()

    async def generate_audio(
        self,
        sentence,
        path
    ):

        communicate = edge_tts.Communicate(
            text=sentence,
            voice=self.voice,
            rate=self.rate
        )

        await communicate.save(path)


class LabBuddySpeaker(QObject):

    sentence_started = Signal(int, str)
    speech_finished = Signal()
    speech_error = Signal(str)

    def __init__(
        self,
        parent=None,
        voice=None,
        rate=None
    ):

        super().__init__(parent)

        # Indian English male voice by default.
        self.voice = (
            voice
            or os.getenv(
                "EDGE_TTS_VOICE",
                "en-IN-PrabhatNeural"
            ).strip()
        )

        # Increase or decrease speaking speed here.
        self.rate = (
            rate
            or os.getenv(
                "EDGE_TTS_RATE",
                "+20%"
            ).strip()
        )

        self.audio_output = QAudioOutput(self)

        self.player = QMediaPlayer(self)

        self.player.setAudioOutput(
            self.audio_output
        )

        self.player.mediaStatusChanged.connect(
            self.on_media_status
        )

        self.player.errorOccurred.connect(
            self.on_player_error
        )

        self.worker = None

        self.sentences = []
        self.ready = {}

        self.current_index = 0

        self.generation_done = False
        self.active_paths = set()

        self.cancelled = False

        print(
            f"[VOICE] Voice: {self.voice}",
            flush=True
        )

        print(
            f"[VOICE] Rate: {self.rate}",
            flush=True
        )

    @staticmethod
    def clean_text(text):

        text = re.sub(
            r"```.*?```",
            " Code example omitted from speech. ",
            text,
            flags=re.S
        )

        text = re.sub(
            r"`([^`]*)`",
            r"\1",
            text
        )

        text = re.sub(
            r"[*_#>]",
            "",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text

    @classmethod
    def split_sentences(cls, text):

        clean = cls.clean_text(text)

        if not clean:
            return []

        parts = re.split(
            r"(?<=[.!?])\s+",
            clean
        )

        result = []
        buffer = ""

        for part in parts:

            part = part.strip()

            if not part:
                continue

            buffer = (
                f"{buffer} {part}".strip()
                if buffer
                else part
            )

            if len(buffer) >= 220:

                result.append(buffer)
                buffer = ""

        if buffer:
            result.append(buffer)

        return result

    def speak(self, text):

        self.stop()

        self.cancelled = False

        self.sentences = self.split_sentences(
            text
        )

        self.ready = {}

        self.current_index = 0

        self.generation_done = False

        self.active_paths = set()

        if not self.sentences:

            self.speech_finished.emit()
            return

        self.worker = SentenceGenerator(
            self.sentences,
            self.voice,
            self.rate,
            self
        )

        self.worker.sentence_ready.connect(
            self.on_sentence_ready
        )

        self.worker.generation_finished.connect(
            self.on_generation_finished
        )

        self.worker.generation_error.connect(
            self.speech_error
        )

        self.worker.start()

    def on_sentence_ready(
        self,
        index,
        sentence,
        path
    ):

        if self.cancelled:

            self.remove_file(path)
            return

        self.ready[index] = (
            sentence,
            path
        )

        self.play_if_ready()

    def play_if_ready(self):

        if self.cancelled:
            return

        if (
            self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            return

        item = self.ready.pop(
            self.current_index,
            None
        )

        if item is None:

            self.finish_if_complete()
            return

        sentence, path = item

        self.active_paths.add(path)

        self.sentence_started.emit(
            self.current_index,
            sentence
        )

        self.player.setSource(
            QUrl.fromLocalFile(
                str(Path(path).resolve())
            )
        )

        self.player.play()

        if self.current_index == 0:

            print(
                "[LATENCY] First audio playback started.",
                flush=True
            )

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
            and self.generation_done
            and self.current_index >= len(self.sentences)
            and self.player.playbackState()
            != QMediaPlayer.PlaybackState.PlayingState
        ):

            self.cleanup_files()

            self.speech_finished.emit()

    def on_player_error(
        self,
        error,
        error_string
    ):

        if (
            error != QMediaPlayer.Error.NoError
            and not self.cancelled
        ):

            self.speech_error.emit(
                error_string
                or "Audio playback failed."
            )

    def stop(self):

        self.cancelled = True

        self.player.stop()

        if (
            self.worker
            and self.worker.isRunning()
        ):

            self.worker.cancel()

            self.worker.wait(1000)

        self.cleanup_files()

        self.ready.clear()

        self.sentences = []

        self.current_index = 0

        self.generation_done = False

    def cleanup_files(self):

        paths = set(self.active_paths)

        paths.update(
            path
            for _, path in self.ready.values()
        )

        if self.worker:

            paths.update(
                getattr(
                    self.worker,
                    "files",
                    []
                )
            )

        for path in paths:
            self.remove_file(path)

        self.active_paths.clear()

    @staticmethod
    def remove_file(path):

        try:

            Path(path).unlink(
                missing_ok=True
            )

        except OSError:
            pass
