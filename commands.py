
import os
import webbrowser
import urllib.parse
from datetime import datetime
import re

class CommandCenter:
    def __init__(self, base_dir: str, on_theme_change=None, on_accent_change=None):
        self.base_dir = base_dir
        self.captures_dir = os.path.join(self.base_dir, "captures")
        os.makedirs(self.captures_dir, exist_ok=True)
        # Optional callbacks wired from GUI
        self.on_theme_change = on_theme_change
        self.on_accent_change = on_accent_change

    # ---------- Utils ----------
    def _ts(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---------- Actions ----------
    def take_screenshot(self, frame_bgr) -> str:
        """Save current frame as PNG under /captures and return path."""
        import cv2
        fn = f"screenshot_{self._ts()}.png"
        path = os.path.join(self.captures_dir, fn)
        cv2.imwrite(path, frame_bgr)
        return path

    def open_youtube(self, query: str | None = None) -> None:
        if query:
            q = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={q}"
        else:
            url = "https://www.youtube.com/"
        webbrowser.open(url)

    def play_music(self, title: str) -> None:
        self.open_youtube(title)

    def google_search(self, query: str) -> None:
        if not query:
            return
        q = urllib.parse.quote_plus(query.strip())
        webbrowser.open(f"https://www.google.com/search?q={q}")

    def youtube_search(self, query: str) -> None:
        if not query:
            return
        q = urllib.parse.quote_plus(query.strip())
        webbrowser.open(f"https://www.youtube.com/results?search_query={q}")

    def open_site(self, domain_or_url: str) -> None:
        """Accepts "google.com" or "https://google.com" or "youtube" -> "youtube.com"."""
        u = (domain_or_url or "").strip().lower()
        if not u:
            return
        if not u.startswith(("http://", "https://")):
            if "." not in u:
                u = u + ".com"
            u = "https://" + u
        webbrowser.open(u)

    # ---------- Theme helpers ----------
    def _apply_theme(self, mode: str) -> bool:
        try:
            if self.on_theme_change:
                self.on_theme_change(mode)
                return True
            import theme
            theme.set_theme(mode)
            return True
        except Exception:
            return False

    def _apply_accent(self, hex_code: str) -> bool:
        try:
            if self.on_accent_change:
                self.on_accent_change(hex_code)
                return True
            import theme
            theme.set_theme('dark', accent_hex=hex_code)
            return True
        except Exception:
            return False

    # ---------- Parser ----------
    def parse_and_run(self, text: str, frame_bgr=None, log_fn=None, lang_hint: str = "en") -> bool:
        if not text:
            return False
        t = text.lower().strip()

        def log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        # --- SCREENSHOT ---
        if any(kw in t for kw in [
            "screenshot", "screen shot", "take a screenshot",
            "fa un screenshot", "fă un screenshot", "fa screenshot",
            "salveaza imaginea", "salvează imaginea"
        ]):
            if frame_bgr is None:
                log("Screenshot: no frame available.")
                return True
            path = self.take_screenshot(frame_bgr)
            log(f"Screenshot salvat: {path}")
            return True

        # --- OPEN YOUTUBE HOME ---
        if any(kw in t for kw in ["open youtube", "deschide youtube"]):
            self.open_youtube(None)
            log("Deschid YouTube.")
            return True

        # --- PLAY MUSIC ---
        music_prefixes = ["muzica ", "muzică ", "pune melodia ", "play music ", "play "]
        for prefix in music_prefixes:
            if t.startswith(prefix):
                title = t[len(prefix):].strip()
                if title:
                    self.play_music(title)
                    log(f"Caut pe YouTube: {title}")
                    return True

        # --- GOOGLE SEARCH ---
        google_prefixes = [
            "cauta pe google ", "caută pe google ", "căutare google ",
            "google ", "search google ", "search for ", "search "
        ]
        for prefix in google_prefixes:
            if t.startswith(prefix):
                query = t[len(prefix):].strip()
                if query:
                    self.google_search(query)
                    log(f"Caut pe Google: {query}")
                    return True

        # --- YOUTUBE SEARCH ---
        yt_prefixes = ["cauta pe youtube ", "caută pe youtube ", "youtube ", "search youtube "]
        for prefix in yt_prefixes:
            if t.startswith(prefix):
                q = t[len(prefix):].strip()
                if q:
                    self.youtube_search(q)
                    log(f"Caut pe YouTube: {q}")
                    return True

        # --- OPEN SITE ---
        site_prefixes = ["deschide ", "deschide site ", "deschide pagina ", "open ", "open site ", "go to "]
        for prefix in site_prefixes:
            if t.startswith(prefix):
                site = t[len(prefix):].strip()
                if site and not site.startswith(("youtube", "muzica", "google")):
                    self.open_site(site)
                    log(f"Deschid site: {site}")
                    return True

        # --- THEME SWITCH ---
        theme_prefixes = [
            "schimba tema in ", "schimbă tema în ",
            "seteaza tema pe ", "setează tema pe ",
            "set theme to ", "switch theme to ", "tema "
        ]
        for prefix in theme_prefixes:
            if t.startswith(prefix):
                mode = t[len(prefix):].strip()
                if mode in ["intunecat", "întunecat", "noapte", "dark"]:
                    mode = "dark"
                elif mode in ["luminos", "light", "zi", "alb"]:
                    mode = "light"
                if mode in ["dark", "light"]:
                    self._apply_theme(mode)
                    log(f"Theme -> {mode}")
                    return True

        # --- ACCENT HEX ---
        if "accent" in t:
            m = re.search(r"#([0-9a-f]{6})", t, re.IGNORECASE)
            if m:
                hex_code = "#" + m.group(1)
                self._apply_accent(hex_code)
                log(f"Accent -> {hex_code}")
                return True

        # --- Simple greetings as non-command ---
        if any(g in t for g in ["hello", "hi", "hey", "salut", "bună", "buna"]):
            return False  # let small talk handler reply

        return False