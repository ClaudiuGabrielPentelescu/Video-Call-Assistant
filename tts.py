
import threading, queue, time
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

class TTS:
    def __init__(self, enabled=True, rate=175):
        self.enabled = enabled
        self.rate = rate
        self._queue = queue.Queue()
        self._stop = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._engine = pyttsx3.init() if pyttsx3 else None
        if self._engine:
            try:
                self._engine.setProperty('rate', self.rate)
            except Exception:
                pass
        self.speaking = False
        self.on_state = None  # callback: on_state(bool)
        self._thread.start()

    def set_enabled(self, flag: bool):
        self.enabled = bool(flag)

    def speak(self, text: str):
        if text:
            self._queue.put(str(text))

    def stop(self):
        self._stop = True
        try:
            self._queue.put_nowait("")
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.5)
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass

    def _loop(self):
        while not self._stop:
            try:
                text = self._queue.get(timeout=0.5)
            except Exception:
                continue
            if not text:
                continue
            if self._engine and self.enabled:
                try:
                    self.speaking = True
                    if self.on_state: self.on_state(True)
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception:
                    pass
                finally:
                    self.speaking = False
                    if self.on_state: self.on_state(False)
    