import os
import time
import random
import cv2
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

from gestures import Perception
from speech import SpeechListener
from tts import TTS
from commands import CommandCenter
from avatar import Avatar
import theme

EN_REPLIES = ["Hello!", "Hi!", "Hey there!"]
RO_REPLIES = ["Salut!", "Bună!", "Salutare!"]


class VideoAssistantGUI:
    def __init__(self, root):
        self.root = root
        root.title("Video Call Assistant — RO/EN (Tkinter)")
        root.geometry("1120x780")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.cap = None
        self.perc = Perception()
        self.tts = TTS(enabled=True)

        # inițializează tema (dark + accent brand)
        theme.set_theme("dark", accent_hex="#0066FF")

        self.avatar = Avatar()
        self.avatar_enabled = tk.BooleanVar(value=True)
        self.avatar_width_pct = tk.DoubleVar(value=28.0)
        self.last_avatar_text = ""
        self.lang_lock = None
        self.current_lang = "en"
        self.help_on = tk.BooleanVar(value=True)
        self.voice_on = tk.BooleanVar(value=True)
        self.running = False
        self.recording = False
        self.video_writer = None
        self.frame_size = None
        self.last_frame = None

        # TTS -> animă gura avatarului
        def _on_tts_state(speaking: bool):
            self.avatar.set_speaking(bool(speaking))
        self.tts.on_state = _on_tts_state

        self.build_ui()

        # CommandCenter cu callback-uri pentru controlul temei prin voce
        self.cmd = CommandCenter(
            self.base_dir,
            on_theme_change=self.apply_theme_from_voice,
            on_accent_change=self.apply_accent_from_voice,
        )

        # STT
        def on_phrase(text, lang):
            # istoric intrare
            self.add_history(f"User said: {text}")

            # log wrapper -> history + log
            def _cmd_log(m):
                self.log(m)
                self.add_history(m)

            # întâi, comenzi (screenshot, youtube, google, open site, theme/accent)
            if self.cmd.parse_and_run(
                text, frame_bgr=self.last_frame, log_fn=_cmd_log, lang_hint=lang
            ):
                return

            # salut -> wave
            if any(k in text.lower() for k in ["salut", "bună", "buna", "hello", "hi", "hei", "hey"]):
                self.avatar.start_wave(2.0)

            # small talk
            self.current_lang = lang
            reply = random.choice(RO_REPLIES if lang == "ro" else EN_REPLIES)
            if self.voice_on.get():
                self.tts.speak(reply)
            self.last_avatar_text = reply
            self.add_history(f"Assistant: {reply}")
            self.log(f"[{lang.upper()}] User: {text} -> Assistant: {reply}")

        self.speech = SpeechListener(phrase_handler=on_phrase)
        if self.speech.is_available():
            self.speech.start()
            self.log("Speech: started (Google recognizer).")
        else:
            self.log("Speech: microphone not available; running without STT.")

    # ---------- UI ----------
    def build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        self.btn_start = ttk.Button(top, text="Start Camera", command=self.start_camera)
        self.btn_stop = ttk.Button(top, text="Stop Camera", command=self.stop_camera, state=tk.DISABLED)
        self.btn_ss = ttk.Button(top, text="Screenshot", command=self.on_screenshot, state=tk.DISABLED)
        self.btn_rec = ttk.Button(top, text="Start Recording", command=self.toggle_recording, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT, padx=4)
        self.btn_stop.pack(side=tk.LEFT, padx=4)
        self.btn_ss.pack(side=tk.LEFT, padx=4)
        self.btn_rec.pack(side=tk.LEFT, padx=4)

        ttk.Separator(self.root, orient="horizontal").pack(fill=tk.X, pady=4)

        # Bară vizibilă de accent (se actualizează la schimbarea culorii)
        self.accent_bar = tk.Frame(self.root, bg=theme.get_accent_hex(), height=4)
        self.accent_bar.pack(fill=tk.X)

        options = ttk.Frame(self.root, padding=8)
        options.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(options, text="Language:").pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="auto")
        lang_combo = ttk.Combobox(
            options, textvariable=self.lang_var, values=["auto", "ro", "en"], width=6, state="readonly"
        )
        lang_combo.pack(side=tk.LEFT, padx=6)
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        ttk.Checkbutton(options, text="Voice", variable=self.voice_on, command=self.on_voice_toggle).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Checkbutton(options, text="Help overlay", variable=self.help_on).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(options, text="Avatar", variable=self.avatar_enabled).pack(side=tk.LEFT, padx=8)

        ttk.Label(options, text="Avatar width %").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Scale(
            options, from_=18, to=45, variable=self.avatar_width_pct, orient="horizontal", length=160
        ).pack(side=tk.LEFT)

        # Theme controls
        ttk.Label(options, text="Theme:").pack(side=tk.LEFT, padx=(16, 4))
        self.theme_mode = tk.StringVar(value="dark")
        theme_combo = ttk.Combobox(
            options, textvariable=self.theme_mode, values=["dark", "light"], width=6, state="readonly"
        )
        theme_combo.pack(side=tk.LEFT)
        theme_combo.bind("<<ComboboxSelected>>", self.on_theme_change)

        ttk.Label(options, text="Accent HEX:").pack(side=tk.LEFT, padx=(12, 4))
        self.accent_entry = ttk.Entry(options, width=9)
        self.accent_entry.insert(0, "#0066FF")
        self.accent_entry.pack(side=tk.LEFT)
        ttk.Button(options, text="Apply", command=self.apply_accent).pack(side=tk.LEFT, padx=4)

        self.video_label = ttk.Label(self.root)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        log_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        log_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(log_frame, text="Log:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=6)
        self.log_text.pack(fill=tk.X)

        # History list
        hist_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        hist_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(hist_frame, text="History (last 20):").pack(anchor="w")
        self.history_list = tk.Listbox(hist_frame, height=6)
        self.history_list.pack(fill=tk.X)

        self.root.bind("<Escape>", lambda e: self.on_quit())
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

    # ---------- Helpers ----------
    def add_history(self, msg):
        ts = time.strftime("[%H:%M:%S] ")
        self.history_list.insert(tk.END, ts + msg)
        if self.history_list.size() > 20:
            self.history_list.delete(0)

    def log(self, msg):
        self.log_text.insert(tk.END, time.strftime("[%H:%M:%S] ") + msg + "\n")
        self.log_text.see(tk.END)

    def refresh_gui_colors(self):
        """Actualizează culorile vizibile din GUI (bara de accent)."""
        try:
            self.accent_bar.configure(bg=theme.get_accent_hex())
        except Exception:
            pass

    # ---------- UI handlers ----------
    def on_language_change(self, _evt=None):
        sel = self.lang_var.get()
        self.lang_lock = None if sel == "auto" else sel
        if self.speech:
            self.speech.set_language_lock(self.lang_lock)
        self.log(f"Language lock: {self.lang_lock or 'auto'}")

    def on_voice_toggle(self):
        self.tts.set_enabled(self.voice_on.get())

    def on_theme_change(self, _evt=None):
        theme.set_theme(self.theme_mode.get())
        self.refresh_gui_colors()
        self.log(f"Theme set to {self.theme_mode.get()}")

    def apply_accent(self):
        hex_code = self.accent_entry.get().strip()
        theme.set_theme(self.theme_mode.get(), accent_hex=hex_code)
        self.refresh_gui_colors()
        self.log(f"Accent set to {hex_code}")

    # ----- utilizate de CommandCenter (prin voce) -----
    def apply_theme_from_voice(self, mode: str):
        import theme as _theme
        m = (str(mode) if mode else "dark").lower()
        if m.startswith("light"):
            m = "light"
        else:
            m = "dark"
        try:
            hex_code = self.accent_entry.get().strip()
        except Exception:
            hex_code = None
        _theme.set_theme(m, accent_hex=hex_code if hex_code else None)
        try:
            self.theme_mode.set(m)
        except Exception:
            pass
        self.add_history(f"Voice: Theme -> {m}")
        self.refresh_gui_colors()
        self.log(f"Theme set to {m} via voice")

    def apply_accent_from_voice(self, hex_code: str):
        import theme as _theme
        if not isinstance(hex_code, str) or not hex_code.startswith("#") or len(hex_code) != 7:
            return
        try:
            current_mode = self.theme_mode.get()
        except Exception:
            current_mode = "dark"
        _theme.set_theme(current_mode, accent_hex=hex_code)
        try:
            self.accent_entry.delete(0, tk.END)
            self.accent_entry.insert(0, hex_code)
        except Exception:
            pass
        self.add_history(f"Voice: Accent -> {hex_code}")
        self.refresh_gui_colors()
        self.log(f"Accent set to {hex_code} via voice")

    # ---------- Camera / video ----------
    def start_camera(self):
        if self.running:
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.log("ERROR: Could not open camera.")
            return
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_ss.config(state=tk.NORMAL)
        self.btn_rec.config(state=tk.NORMAL)
        self.last_ok_spoken = 0.0
        self.last_smile_spoken = 0.0
        self.last_thumb_spoken = 0.0
        self.last_brow_spoken = 0.0
        self.update_frame()

    def stop_camera(self):
        self.running = False
        if self.recording:
            self._stop_recording()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_ss.config(state=tk.DISABLED)
        self.btn_rec.config(state=tk.DISABLED)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.config(image="")

    def _start_recording(self):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        os.makedirs(os.path.join(self.base_dir, "captures"), exist_ok=True)
        path = os.path.join(
            self.base_dir, "captures", time.strftime("record_%Y%m%d_%H%M%S.mp4")
        )
        size = self.frame_size if self.frame_size else (640, 480)
        self.video_writer = cv2.VideoWriter(path, fourcc, 30.0, size)
        self.recording = True
        self.btn_rec.config(text="Stop Recording")
        self.log(f"Recording started: {path}")

    def _stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.recording = False
        self.btn_rec.config(text="Start Recording")
        self.log("Recording stopped.")

    def toggle_recording(self):
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def on_screenshot(self):
        if self.last_frame is None:
            self.log("No frame to capture.")
            return
        path = self.cmd.take_screenshot(self.last_frame)
        self.log(f"Screenshot salvat: {path}")
        self.add_history(f"Screenshot -> {path}")

    def update_frame(self):
        if not self.running or not self.cap:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.stop_camera()
            return

        frame = cv2.flip(frame, 1)
        self.last_frame = frame.copy()
        frame, hand_state, face_state = self.perc.process(frame)
        self.frame_size = (frame.shape[1], frame.shape[0])

        working_lang = self.lang_lock or self.current_lang or "en"
        self.perc.draw_assistant_reactions(frame, hand_state, face_state)
        self.perc.draw_hud(frame, working_lang, tts_on=self.voice_on.get(), help_on=self.help_on.get())

        # Spoken feedback (rate-limited)
        now = time.time()
        if hand_state and hand_state.ok_gesture and (now - getattr(self, "last_ok_spoken", 0) > 2.5):
            if self.voice_on.get():
                self.tts.speak("OK!" if working_lang != "ro" else "OK!")
            self.last_ok_spoken = now
            self.add_history("Gesture: OK")

        if hand_state and hand_state.thumbs_up and (now - getattr(self, "last_thumb_spoken", 0) > 2.5):
            if self.voice_on.get():
                self.tts.speak("Nice!" if working_lang != "ro" else "Bravo!")
            self.last_thumb_spoken = now
            self.add_history("Gesture: Thumbs-Up")

        if face_state and face_state.smiling and (now - getattr(self, "last_smile_spoken", 0) > 3.0):
            if self.voice_on.get():
                self.tts.speak("Nice smile!" if working_lang != "ro" else "Frumos zâmbet!")
            self.last_smile_spoken = now
            self.add_history("Gesture: Smile")

        if face_state and face_state.eyebrow_raise and (now - getattr(self, "last_brow_spoken", 0) > 3.0):
            if self.voice_on.get():
                self.tts.speak("Hmm?" if working_lang != "ro" else "Interesant!")
            self.last_brow_spoken = now
            self.add_history("Gesture: Eyebrow raise")

        # Avatar panel
        if self.avatar_enabled.get():
            H, W = frame.shape[:2]
            panel_w = int(W * (self.avatar_width_pct.get() / 100.0))
            state = {
                "smile": bool(face_state and face_state.smiling),
                "eyebrow_raise": bool(face_state and face_state.eyebrow_raise),
                "ok": bool(hand_state and hand_state.ok_gesture),
                "thumbs_up": bool(hand_state and hand_state.thumbs_up),
                "gaze": (face_state.gaze_offset if face_state else (0.0, 0.0)),
                "speech": self.last_avatar_text,
            }
            self.avatar.draw(frame, W - panel_w - 12, 12, panel_w, int(H * 0.50), state)

        if self.recording and self.video_writer:
            self.video_writer.write(frame)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.root.after(10, self.update_frame)

    def on_quit(self):
        try:
            self.stop_camera()
        except Exception:
            pass
        try:
            if self.speech:
                self.speech.stop()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoAssistantGUI(root)
    root.mainloop()
