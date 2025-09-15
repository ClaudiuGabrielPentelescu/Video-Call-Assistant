
import threading, time, queue
try:
    import speech_recognition as sr
except Exception:
    sr = None

class SpeechListener:
    """
    Background speech recognizer using SpeechRecognition (Google Web Speech API).
    Calls phrase_handler(text:str, lang:str) with 'ro' or 'en' best guess.
    """
    def __init__(self, phrase_handler=None, energy_threshold=300, pause_threshold=0.75):
        self.phrase_handler = phrase_handler
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self._thread = None
        self._stop = threading.Event()
        self._lang_lock = None  # 'ro' / 'en' / None

    def is_available(self) -> bool:
        return sr is not None

    def set_language_lock(self, lang):
        if lang in ("ro", "en", None):
            self._lang_lock = lang

    def _detect_lang(self, text: str) -> str:
        if self._lang_lock in ("ro", "en"):
            return self._lang_lock
        t = (text or "").lower()
        ro_markers = ["salut", "buna", "bună", "captura", "ecran", "deschide", "youtube", "muzica", "căutare", "cauta", "accent", "tema"]
        if any(m in t for m in ro_markers):
            return "ro"
        # diacritics heuristic
        if any(ch in t for ch in "ăâîșşțţ"):
            return "ro"
        return "en"

    def start(self):
        if not self.is_available() or self._thread:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def _loop(self):
        r = sr.Recognizer()
        r.energy_threshold = self.energy_threshold
        r.pause_threshold = self.pause_threshold
        try:
            mic = sr.Microphone()
        except Exception:
            return
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=0.6)
        while not self._stop.is_set():
            try:
                with mic as source:
                    audio = r.listen(source, timeout=3, phrase_time_limit=6)
                try:
                    # prefer Romanian when likely; use lang lock if set
                    lang = self._lang_lock or "ro"
                    text = r.recognize_google(audio, language=lang)
                except Exception:
                    # fallback to English
                    text = r.recognize_google(audio, language="en-US")
                if text and self.phrase_handler:
                    lang_detected = self._detect_lang(text)
                    self.phrase_handler(text, lang_detected)
            except Exception:
                # timeout or recognition issue; continue
                pass
    