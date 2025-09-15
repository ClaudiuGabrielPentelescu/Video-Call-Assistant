
<p align="center">
  <img src="assist.PNG" alt="ASSIST — Innovative Minds" height="72">
</p>

<h1 align="center">Video Call Assistant — RO/EN</h1>
<p align="center">
  Gaze tracking · Gesture mirror · Voice commands · Animated avatar · Brand theme
</p>

---

## ✨ Features
- 👀 **Gaze tracking** (MediaPipe Iris) – pupilele avatarului urmăresc privirea ta (EMA smoothing).
- 🤝 **Gesturi**: OK 👌, Like 👍, zâmbet 🙂, sprânceană ridicată 🤨 (reacții vizuale + TTS).
- 🗣️ **Comenzi vocale** RO/EN:
  - „fă un **screenshot**”
  - „**deschide youtube**”, „**youtube [termen]**”, „**muzica [titlu]** / play [title]”
  - „**caută pe google [termen]**”
  - „**deschide [site]**” (acceptă și „open/go to” + fără .com)
  - „**schimbă tema în dark/light**”
  - „**accent #0066FF**”
- 🧑‍🎨 **Avatar animat** (blink, gură la vorbire, wave 👋 la salut, mână 👍/👌), panel **History**.
- 🎨 **Theme switcher** (dark/light) + **Accent HEX** (brand Assist).

## 🧱 Stack
Python, OpenCV, MediaPipe (Hands + FaceMesh + Iris), Tkinter (GUI), PyAudio + SpeechRecognition (STT), pyttsx3 (offline TTS), Pillow, NumPy.

## 🚀 Quick start
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python main_tk2.py
```

> Microfon:
> - Windows: `pip install pipwin && pipwin install pyaudio`
> - macOS: `brew install portaudio && pip install pyaudio`
> - Linux: `sudo apt-get install portaudio19-dev && pip install pyaudio`

## 🎛️ Controls
- GUI: **Start/Stop Camera**, **Screenshot**, **Start/Stop Recording**, **Language (auto/ro/en)**, **Voice**, **Help overlay**, **Avatar**, **Avatar width %**, **Theme (dark/light)**, **Accent HEX + Apply**.
- Voice: vezi lista de mai sus (RO/EN).
- Shortcuts: `ESC` pentru quit (sau X pe fereastră).

## 📁 Structure
```
main_tk2.py        # aplicația GUI
gestures.py        # MediaPipe: mâini + față + iris (gaze), HUD
speech.py          # STT (Google recognizer via SpeechRecognition + PyAudio)
tts.py             # TTS offline (pyttsx3) + callback "speaking"
avatar.py          # avatar 2D (blink, gură, wave, mână 👍/👌, speech bubble)
commands.py        # parsare și execuție comenzi (YouTube, Google, site, screenshot, muzică, theme/accent voice)
theme.py           # tema dark/light + accent HEX
requirements.txt
README.md
assist.PNG         # logo-ul brandului (opțional, pentru README/UI)
captures/          # screenshot-uri și înregistrări video
```

## 🗒️ Notes
- Gaze tracking este o estimare (în lumină bună e stabil, în lumină slabă poate fluctua).
- Dacă ai mai multe camere, schimbă `cv2.VideoCapture(0)` → `1`/`2`.
- STT folosește microfonul default (verifică permisiunile OS).

## 🛡️ Privacy
Procesare locală (video/voce/gesturi). Nu se trimit date online în afara STT-ului Google din `SpeechRecognition` (poți dezactiva Voice din GUI).

## 🧾 License
MIT – vezi fișierul [LICENSE](LICENSE).


**Quick run:** Windows → `run_app.bat`, macOS/Linux → `run_app.sh`.
