
import cv2
import math
import time
import random

# Brand palette
BRAND_BG = (26, 32, 56)
BRAND_STROKE = (180, 190, 210)
BRAND_FACE = (230, 242, 255)
BRAND_FACE_STROKE = (170, 180, 200)
BRAND_OK = (90, 210, 90)
BRAND_LIKE = (0, 200, 255)
BRAND_TEXT = (240, 240, 240)
BRAND_BUBBLE = (255, 255, 255)
BRAND_BUBBLE_STROKE = (90, 100, 120)
HAIR = (32, 46, 80)
SHADOW = (180, 190, 210)

class Avatar:
    """
    2D avatar with more detailed face (eyes with whites/pupils, nose, brows, hair)
    and a stylized hand that can show 👍 or OK.
    """
    def __init__(self):
        self.next_blink_t = time.time() + random.uniform(2.0, 5.0)
        self.blink_dur = 0.12
        self.blinking = False
        self.speaking = False
        self._speak_anim_phase = 0.0

    def set_speaking(self, speaking: bool):
        self.speaking = speaking
        if speaking:
            self._speak_anim_phase = 0.0

    def _clip_rect(self, frame, x, y, w, h):
        H, W = frame.shape[:2]
        x = max(0, min(W-1, x))
        y = max(0, min(H-1, y))
        w = max(1, min(W - x, w))
        h = max(1, min(H - y, h))
        return x, y, w, h

    def _update_blink(self):
        now = time.time()
        if not self.blinking and now >= self.next_blink_t:
            self.blinking = True
            self.next_blink_t = now + self.blink_dur
        elif self.blinking and now >= self.next_blink_t:
            self.blinking = False
            self.next_blink_t = now + random.uniform(2.0, 5.0)

    def _draw_eye(self, roi, center, r, blink, pupil_offset=(0,0)):
        cx, cy = center
        if blink:
            cv2.line(roi, (cx - r, cy), (cx + r, cy), (40,40,40), 2)
            return
        # sclera
        cv2.ellipse(roi, (cx, cy), (int(r*1.4), int(r*1.0)), 0, 0, 360, (255,255,255), -1)
        cv2.ellipse(roi, (cx, cy), (int(r*1.4), int(r*1.0)), 0, 0, 360, (180,180,180), 1)
        # iris/pupil
        ix, iy = cx + int(pupil_offset[0]*r), cy + int(pupil_offset[1]*r)
        cv2.circle(roi, (ix, iy), int(r*0.9), (110,140,210), -1)
        cv2.circle(roi, (ix, iy), int(r*0.5), (20,20,20), -1)
        cv2.circle(roi, (ix - int(r*0.3), iy - int(r*0.3)), int(r*0.2), (255,255,255), -1)

    def _draw_hand_thumbsup(self, roi, x, y, scale=1.0, color=BRAND_LIKE):
        w, h = int(70*scale), int(70*scale)
        cv2.rectangle(roi, (x+10, y+20), (x+50, y+60), color, 2)
        cv2.rectangle(roi, (x+45, y+5), (x+60, y+30), color, 2)
        cv2.line(roi, (x+20, y+22), (x+42, y+22), color, 2)
        cv2.line(roi, (x+20, y+32), (x+42, y+32), color, 2)
        cv2.line(roi, (x+20, y+42), (x+42, y+42), color, 2)

    def _draw_hand_ok(self, roi, x, y, scale=1.0, color=BRAND_OK):
        s = scale
        cv2.circle(roi, (x+35, y+35), int(12*s), color, 2)
        cv2.line(roi, (x+20, y+20), (x+30, y+30), color, 2)
        cv2.line(roi, (x+35, y+35), (x+50, y+15), color, 2)
        cv2.line(roi, (x+50, y+45), (x+65, y+45), color, 2)
        cv2.line(roi, (x+50, y+55), (x+65, y+55), color, 2)
        cv2.line(roi, (x+50, y+65), (x+65, y+65), color, 2)

    def draw(self, frame, x, y, w, h, state):
        x, y, w, h = self._clip_rect(frame, x, y, w, h)
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0:
            return frame

        self._update_blink()

        # background panel
        cv2.rectangle(roi, (0,0), (w-1,h-1), BRAND_BG, -1)
        cv2.rectangle(roi, (0,0), (w-1,h-1), BRAND_STROKE, 2)

        # head shadow
        cx, cy = w//2, h//2 + 10
        radius = int(min(w,h)*0.32)
        cv2.circle(roi, (cx+2, cy+2), radius+2, SHADOW, 1)

        # face
        cv2.circle(roi, (cx, cy), radius, BRAND_FACE, -1)
        cv2.circle(roi, (cx, cy), radius, BRAND_FACE_STROKE, 2)

        # hair
        cv2.ellipse(roi, (cx, cy-int(radius*0.35)), (int(radius*0.95), int(radius*0.65)), 0, 0, 360, HAIR, -1)
        cv2.ellipse(roi, (cx, cy-int(radius*0.35)), (int(radius*0.95), int(radius*0.65)), 0, 0, 360, (20,30,50), 2)

        # eyes
        eye_dx = int(radius*0.45)
        eye_y = cy - int(radius*0.18)
        eye_r = max(3, int(radius*0.11))
        self._draw_eye(roi, (cx - eye_dx, eye_y), eye_r, self.blinking)
        self._draw_eye(roi, (cx + eye_dx, eye_y), eye_r, self.blinking)

        # eyebrows
        brow_offset = 6 if state.get('eyebrow_raise', False) else 0
        cv2.line(roi, (cx - eye_dx - eye_r, eye_y - int(radius*0.25) - brow_offset),
                      (cx - eye_dx + eye_r, eye_y - int(radius*0.27) - brow_offset), (30,30,30), 3)
        cv2.line(roi, (cx + eye_dx - eye_r, eye_y - int(radius*0.25) - brow_offset),
                      (cx + eye_dx + eye_r, eye_y - int(radius*0.27) - brow_offset), (30,30,30), 3)

        # nose
        cv2.line(roi, (cx, cy - int(radius*0.05)), (cx, cy + int(radius*0.08)), (120,120,120), 2)
        cv2.circle(roi, (cx, cy + int(radius*0.1)), 2, (100,100,100), -1)

        # mouth
        if self.speaking:
            self._speak_anim_phase += 0.22
            amp = 0.35 + 0.25*abs(math.sin(self._speak_anim_phase))
            cv2.ellipse(roi, (cx, cy+int(radius*0.18)), (int(radius*0.40), int(radius*amp)), 0, 0, 360, (40,60,120), 4)
        else:
            if state.get('smile', False):
                cv2.ellipse(roi, (cx, cy+int(radius*0.18)), (int(radius*0.48), int(radius*0.38)), 0, 15, 165, (40,120,40), 4)
            else:
                cv2.line(roi, (cx-int(radius*0.35), cy+int(radius*0.18)), (cx+int(radius*0.35), cy+int(radius*0.18)), (60,60,60), 3)

        # hand near panel bottom-right
        hand_x = w - int(radius*1.6)
        hand_y = int(h*0.58)
        if state.get('thumbs_up', False):
            self._draw_hand_thumbsup(roi, hand_x, hand_y, scale=1.2, color=BRAND_LIKE)
        if state.get('ok', False):
            self._draw_hand_ok(roi, hand_x - 24, hand_y, scale=1.2, color=BRAND_OK)

        # speech bubble
        text = state.get('speech', None)
        if text:
            bx, by, bw, bh = 10, h-70, w-20, 60
            cv2.rectangle(roi, (bx, by), (bx+bw, by+bh), BRAND_BUBBLE, -1)
            cv2.rectangle(roi, (bx, by), (bx+bw, by+bh), BRAND_BUBBLE_STROKE, 2)
            words = text.split()
            lines, line = [], ""
            for word in words:
                if len(line)+len(word)+1 > 28:
                    lines.append(line); line = word
                else:
                    line = (line+" "+word).strip()
            if line: lines.append(line)
            ty = by+22
            for ln in lines[:2]:
                cv2.putText(roi, ln, (bx+10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20,20,20), 2)
                ty += 22

        frame[y:y+h, x:x+w] = roi
        return frame
