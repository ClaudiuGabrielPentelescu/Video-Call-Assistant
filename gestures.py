from dataclasses import dataclass
from typing import Optional, Tuple
import math
import numpy as np

import cv2
import mediapipe as mp
import theme  # paleta de culori (BGR) + accent

mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# drawing_styles nu există în toate versiunile MediaPipe — fallback la stiluri implicite
if hasattr(mp.solutions, "drawing_styles"):
    mp_styles = mp.solutions.drawing_styles
else:
    mp_styles = None


@dataclass
class HandState:
    ok_gesture: bool = False
    thumbs_up: bool = False
    hand_center: Tuple[int, int] = (0, 0)


@dataclass
class FaceState:
    smiling: bool = False
    eyebrow_raise: bool = False
    mouth_center: Tuple[int, int] = (0, 0)
    gaze_offset: Tuple[float, float] = (0.0, 0.0)  # (-1..1, -1..1)


class Perception:
    def __init__(self):
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.face = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # necesar pt. iris/gaze
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        # smoothing pentru gaze (mai natural)
        self.gaze_ema = (0.0, 0.0)
        self.gaze_alpha = 0.35

    # ---------- helpers ----------
    @staticmethod
    def _norm_dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _detect_ok(self, pts):
        # deget mare (4) atinge arătător (8), raportat la lățimea palmei
        thumb_tip = pts[4]
        index_tip = pts[8]
        wrist = pts[0]
        middle_mcp = pts[9]
        palm = max(1, self._norm_dist(wrist, middle_mcp))
        ok_distance = self._norm_dist(thumb_tip, index_tip) / palm
        return ok_distance < 0.5

    def _detect_thumbs_up(self, pts):
        # 👍: policul sus, restul degetelor îndoite
        thumb_tip = pts[4]; thumb_mcp = pts[2]
        index_tip, index_pip = pts[8], pts[6]
        middle_tip, middle_pip = pts[12], pts[10]
        ring_tip, ring_pip = pts[16], pts[14]
        pinky_tip, pinky_pip = pts[20], pts[18]

        thumb_up = thumb_tip[1] < thumb_mcp[1] - 6
        index_folded = index_tip[1] > index_pip[1]
        middle_folded = middle_tip[1] > middle_pip[1]
        ring_folded = ring_tip[1] > ring_pip[1]
        pinky_folded = pinky_tip[1] > pinky_pip[1]
        return thumb_up and index_folded and middle_folded and ring_folded and pinky_folded

    def _detect_smile(self, lm, w, h):
        def pt(i): return (int(lm[i].x * w), int(lm[i].y * h))
        left_mouth = pt(61); right_mouth = pt(291)
        upper_lip = pt(13); lower_lip = pt(14)
        width = self._norm_dist(left_mouth, right_mouth)
        height = self._norm_dist(upper_lip, lower_lip)
        ratio = width / max(1.0, height)
        smiling = ratio > 1.8
        center = (int((left_mouth[0] + right_mouth[0]) / 2),
                  int((upper_lip[1] + lower_lip[1]) / 2))
        return smiling, center

    def _detect_eyebrow_raise(self, lm, w, h):
        def pt(i): return (int(lm[i].x * w), int(lm[i].y * h))
        left_eye_center_y = (pt(33)[1] + pt(133)[1]) / 2.0
        right_eye_center_y = (pt(263)[1] + pt(362)[1]) / 2.0
        left_brow_y = pt(105)[1]
        right_brow_y = pt(334)[1]
        left_gap = max(1.0, left_eye_center_y - left_brow_y)
        right_gap = max(1.0, right_eye_center_y - right_brow_y)
        asymmetry = left_gap / right_gap if right_gap > 0 else 1.0
        asymmetry_inv = right_gap / left_gap if left_gap > 0 else 1.0
        eyebrow_raise = (asymmetry > 1.2 and left_gap > 8) or (asymmetry_inv > 1.2 and right_gap > 8)
        return eyebrow_raise

    def _detect_gaze(self, lm, w, h):
        # calculează offset (-1..1) pentru privire, medie între ochi
        try:
            def pt(i): return (lm[i].x * w, lm[i].y * h)
            # ochi stâng
            lx0, ly0 = pt(33); lx1, ly1 = pt(133)
            lcx = (lx0 + lx1) / 2.0; lcy = (ly0 + ly1) / 2.0
            lix = np.mean([pt(i)[0] for i in [468, 469, 470, 471, 472]])
            liy = np.mean([pt(i)[1] for i in [468, 469, 470, 471, 472]])
            lw = abs(lx1 - lx0) + 1e-5
            lh = abs(ly1 - ly0) + 1e-5
            lgx = (lix - lcx) / (lw * 0.5)
            lgy = (liy - lcy) / (lh * 0.5)
            # ochi drept
            rx0, ry0 = pt(263); rx1, ry1 = pt(362)
            rcx = (rx0 + rx1) / 2.0; rcy = (ry0 + ry1) / 2.0
            rix = np.mean([pt(i)[0] for i in [473, 474, 475, 476, 477]])
            riy = np.mean([pt(i)[1] for i in [473, 474, 475, 476, 477]])
            rw = abs(rx1 - rx0) + 1e-5
            rh = abs(ry1 - ry0) + 1e-5
            rgx = (rix - rcx) / (rw * 0.5)
            rgy = (riy - rcy) / (rh * 0.5)
            # medie + limitare
            gx = float(max(-1.0, min(1.0, (lgx + rgx) * 0.5)))
            gy = float(max(-1.0, min(1.0, (lgy + rgy) * 0.5)))
            return (gx, gy)
        except Exception:
            return (0.0, 0.0)

    # ---------- pipeline ----------
    def process(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        hand_state: Optional[HandState] = None
        face_state: Optional[FaceState] = None

        # Hands
        hand_results = self.hands.process(frame_rgb)
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                pts = [(int(l.x * w), int(l.y * h)) for l in hand_landmarks.landmark]
                cx = int(sum(p[0] for p in pts) / len(pts))
                cy = int(sum(p[1] for p in pts) / len(pts))
                ok_detected = self._detect_ok(pts)
                thumbs_up = self._detect_thumbs_up(pts)
                hand_state = HandState(ok_gesture=ok_detected, thumbs_up=thumbs_up, hand_center=(cx, cy))

                if mp_styles:
                    mp_drawing.draw_landmarks(
                        frame_bgr, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )
                else:
                    mp_drawing.draw_landmarks(frame_bgr, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                break  # doar prima mână pentru reacție

        # Face
        face_results = self.face.process(frame_rgb)
        if face_results.multi_face_landmarks:
            lm = face_results.multi_face_landmarks[0].landmark
            smiling, center = self._detect_smile(lm, w, h)
            eyebrow_raise = self._detect_eyebrow_raise(lm, w, h)
            gaze = self._detect_gaze(lm, w, h)

            # EMA smoothing
            gx = self.gaze_ema[0] * (1 - self.gaze_alpha) + gaze[0] * self.gaze_alpha
            gy = self.gaze_ema[1] * (1 - self.gaze_alpha) + gaze[1] * self.gaze_alpha
            self.gaze_ema = (gx, gy)

            face_state = FaceState(
                smiling=smiling,
                eyebrow_raise=eyebrow_raise,
                mouth_center=center,
                gaze_offset=self.gaze_ema
            )

            if mp_styles:
                mp_drawing.draw_landmarks(
                    frame_bgr, face_results.multi_face_landmarks[0],
                    mp_face_mesh.FACEMESH_TESSELATION,
                    mp_styles.get_default_face_mesh_tesselation_style(),
                    mp_styles.get_default_face_mesh_tesselation_style()
                )
            else:
                mp_drawing.draw_landmarks(
                    frame_bgr, face_results.multi_face_landmarks[0],
                    mp_face_mesh.FACEMESH_TESSELATION
                )

        return frame_bgr, hand_state, face_state

    # ---------- overlays ----------
    @staticmethod
    def draw_assistant_reactions(frame, hand_state: Optional[HandState], face_state: Optional[FaceState]):
        # mic “mirror” vizual
        if hand_state:
            if hand_state.ok_gesture:
                x, y = hand_state.hand_center
                cv2.putText(frame, "Assistant: OK!", (x - 60, y - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.circle(frame, (x, y), 22, (0, 255, 0), 3)
                cv2.line(frame, (x + 10, y + 8), (x + 22, y + 20), (0, 255, 0), 3)
            if hand_state.thumbs_up:
                x, y = hand_state.hand_center
                cv2.putText(frame, "Assistant: 👍", (x - 60, y - 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)
                cv2.rectangle(frame, (x - 10, y - 10), (x + 25, y + 25), (0, 200, 255), 2)
                cv2.rectangle(frame, (x + 25, y - 5), (x + 35, y + 10), (0, 200, 255), 2)

        if face_state:
            if face_state.smiling:
                x, y = face_state.mouth_center
                cv2.putText(frame, "Assistant: :)", (x - 50, y - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 215, 255), 2)
                cv2.ellipse(frame, (x, y + 10), (35, 18), 0, 10, 170, (0, 215, 255), 3)
            if face_state.eyebrow_raise:
                h, _w = frame.shape[:2]
                cv2.putText(frame, "Assistant: 🤨", (20, h - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)

    @staticmethod
    def draw_hud(frame, lang, tts_on, help_on):
        """HUD cu status în culoarea de accent + underline și spațiere dinamică a rândurilor."""
        h, w = frame.shape[:2]

        # fundal HUD (pentru lizibilitate)
        cv2.rectangle(frame, (8, 8), (w - 8, 60), theme.COLORS['hud_bg'], -1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        title_scale, title_th = 0.9, 2
        line_scale, line_th = 0.7, 2

        status = f"Lang: {lang.upper()} | Voice: {'ON' if tts_on else 'OFF'} | H: help"
        cv2.putText(frame, status, (20, 40), font, title_scale, theme.COLORS['accent'], title_th)
        cv2.line(frame, (8, 60), (w - 8, 60), theme.COLORS['accent'], 3)  # accent underline

        if not help_on:
            return

        # spațiu dintre linii calculat pe baza metricei textului (rezoluție-agnostic)
        pad = max(6, int(h * 0.012))  # ~8px la 720p
        y = 80
        lines = [
            "ESC: quit | GUI: Start/Stop, Screenshot, Recording",
            "Language auto/RO/EN | Voice on/off | Avatar on/off | Avatar width %",
            "Gestures: OK, Thumbs-Up, Smile, Eyebrow raise",
            "Voice: screenshot, open youtube, muzica/play [titlu]",
            "       google [termen], youtube [termen], deschide [site]",
            "Theme: theme dark/light | Accent: accent #RRGGBB",
        ]
        for line in lines:
            (tw, th), base = cv2.getTextSize(line, font, line_scale, line_th)
            cv2.putText(frame, line, (20, y), font, line_scale, theme.COLORS['hud_text'], line_th)
            y += th + base + pad  # distanță dinamică
