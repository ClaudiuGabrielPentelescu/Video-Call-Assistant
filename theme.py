# Simple theme manager for avatar/HUD
# Colors are in BGR (OpenCV)
import colorsys

def _hex_to_bgr(hex_str):
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch*2 for ch in s)
    if len(s) != 6:
        return None
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (b, g, r)

def _bgr_to_hex(bgr):
    b, g, r = bgr
    return f"#{r:02X}{g:02X}{b:02X}"

def _derive_shades(accent_bgr):
    # BGR -> RGB pentru colorsys
    b, g, r = [c/255.0 for c in accent_bgr]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # LIGHT: +V, -S
    v_l = min(1.0, v * 1.25 + 0.05); s_l = max(0.0, s * 0.85)
    rl, gl, bl = colorsys.hsv_to_rgb(h, s_l, v_l)
    # DARK: -V
    v_d = max(0.0, v * 0.65); s_d = s
    rd, gd, bd = colorsys.hsv_to_rgb(h, s_d, v_d)
    light = (int(bl*255), int(gl*255), int(rl*255))
    dark  = (int(bd*255), int(gd*255), int(rd*255))
    return light, dark

# Defaults (dark + accent placeholder)
COLORS = {
    "mode": "dark",
    "accent": (255, 102, 0),
    "accent_light": (255, 160, 80),
    "accent_dark": (140, 60, 0),
    "hud_bg": (26, 32, 56),
    "hud_text": (255, 255, 255),
    "panel_bg": (26, 32, 56),
    "panel_stroke": (180, 190, 210),
    "face_fill": (230, 242, 255),
    "face_stroke": (170, 180, 200),
    "bubble_fill": (255, 255, 255),
    "bubble_stroke": (90, 100, 120),
}

def set_accent_from_hex(hex_code: str):
    bgr = _hex_to_bgr(hex_code)
    if bgr:
        COLORS["accent"] = bgr
        light, dark = _derive_shades(bgr)
        COLORS["accent_light"] = light
        COLORS["accent_dark"] = dark

def get_accent_hex() -> str:
    return _bgr_to_hex(COLORS["accent"])

def set_theme(mode: str, accent_hex: str = None):
    mode = (mode or "dark").lower()
    if accent_hex:
        set_accent_from_hex(accent_hex)
    if mode == "light":
        COLORS.update({
            "mode": "light",
            "hud_bg": (245, 245, 245),
            "hud_text": (20, 20, 20),
            "panel_bg": (245, 248, 255),
            "panel_stroke": (180, 190, 210),
            "face_fill": (255, 255, 255),
            "face_stroke": (170, 180, 200),
            "bubble_fill": (255, 255, 255),
            "bubble_stroke": (140, 150, 170),
        })
    else:
        COLORS.update({
            "mode": "dark",
            "hud_bg": (26, 32, 56),
            "hud_text": (255, 255, 255),
            "panel_bg": (26, 32, 56),
            "panel_stroke": (180, 190, 210),
            "face_fill": (230, 242, 255),
            "face_stroke": (170, 180, 200),
            "bubble_fill": (255, 255, 255),
            "bubble_stroke": (90, 100, 120),
        })
