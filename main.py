import math
import random
import threading
import tempfile
import time
import wave
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pygame
import winsound

WINDOW_TITLE = "Tien Lo Do Kiep"
LEVELS = [
    "Luyen Khi",
    "Truc Co",
    "Ket Dan",
    "Nguyen Anh",
    "Hoa Than",
    "Van Dinh",
    "Am Duong Hu Thuc",
]
TARGET_SECONDS = 10.0
DISPLAY_W = 1600
DISPLAY_H = 900
DISPLAY_W = 1280
DISPLAY_H = 720
SKILLS = [
    ("Khi Chuyen", "CV skill: nam tay trai/phai de thi trien"),
    ("Ho The Ket Gioi", "CV skill: nam tay trai/phai de bat la chan"),
    ("Kim Dan Pha", "CV skill: nam tay trai/phai de no kim dan"),
    ("Nguyen Anh Anh Sat", "CV skill: nam tay trai/phai de goi phan than"),
    ("Than Thuc Quet", "CV skill: nam tay trai/phai de quet than thuc"),
    ("Thien Loi Kich", "CV skill: nam tay trai/phai de goi thien loi"),
    ("Hu Thuc Dao Chuyen", "CV skill: nam tay trai/phai de lap tran am duong"),
]
SKILL_DURATIONS = [2.6, 4.0, 2.8, 4.0, 4.0, 4.2, 5.0]
SKILL_COOLDOWN = 6.0
FIST_CAST_HOLD = 0.50
FIST_CAST_THRESHOLD = 0.76
FINGER_SELECT_HOLD = 0.65
FINGER_SELECT_CONF = 0.58
SKILL_ARM_SECONDS = 4.0
SKILL_SLOTS = [
    ("Nhat Chi Linh Dan", "1 ngon: dan linh khi toc do cao"),
    ("Nhi Chi Ket Gioi", "2 ngon: mo ket gioi ho the"),
    ("Tam Chi Kiem Quang", "3 ngon: kiem quang chem ngang"),
    ("Tu Chi Loi Anh", "4 ngon: loi anh va phan than"),
    ("Ngu Chi Dai Tran", "5 ngon: dai tran bung no"),
]
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]
FINGER_TIPS = {4, 8, 12, 16, 20}


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def smooth(prev: float, cur: float, alpha: float) -> float:
    return prev * (1.0 - alpha) + cur * alpha


def create_meditation_wav(path: Path, seconds: float = 3.0, sample_rate: int = 22050) -> None:
    total = int(seconds * sample_rate)
    tones = [174.0, 220.0, 261.6]
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            t = i / sample_rate
            env = 0.66 + 0.34 * math.sin(2.0 * math.pi * 0.21 * t)
            val = 0.0
            val += math.sin(2.0 * math.pi * tones[0] * t) * 0.58
            val += math.sin(2.0 * math.pi * tones[1] * t) * 0.27
            val += math.sin(2.0 * math.pi * tones[2] * t) * 0.15
            val = clamp(val * env * 0.26, -1.0, 1.0)
            i16 = int(val * 32767)
            frames.extend(i16.to_bytes(2, "little", signed=True))
        wav.writeframes(frames)


def create_effect_wav(path: Path, tones, seconds: float = 0.55, sample_rate: int = 44100, volume: float = 0.34, sweep: float = 0.0) -> None:
    total = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            t = i / sample_rate
            k = i / max(1, total - 1)
            env = math.sin(math.pi * k) ** 0.45
            val = 0.0
            for idx, freq in enumerate(tones):
                f = freq + sweep * k * (1.0 + idx * 0.18)
                val += math.sin(2.0 * math.pi * f * t) / len(tones)
            noise = random.uniform(-1.0, 1.0) * 0.06 * (1.0 - k)
            val = clamp((val + noise) * env * volume, -1.0, 1.0)
            frames.extend(int(val * 32767).to_bytes(2, "little", signed=True))
        wav.writeframes(frames)


def create_named_skill_wav(path: Path, slot: int, sample_rate: int = 44100) -> None:
    durations = {1: 0.46, 2: 0.86, 3: 0.38, 4: 0.92, 5: 1.08}
    total = int(durations.get(slot, 0.6) * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        phase_noise = random.random() * math.tau
        for i in range(total):
            t = i / sample_rate
            k = i / max(1, total - 1)
            env = math.sin(math.pi * k) ** 0.35
            noise = random.uniform(-1.0, 1.0)

            if slot == 1:  # Nhat Chi Linh Dan: fast bright projectile
                f = 520.0 + 980.0 * k
                val = math.sin(math.tau * f * t) * 0.68 + math.sin(math.tau * (f * 1.52) * t) * 0.22 + noise * 0.04
                env *= (1.0 - k * 0.35)
            elif slot == 2:  # Nhi Chi Ket Gioi: shield bloom, low stable hum
                f = 150.0 + 80.0 * math.sin(k * math.pi)
                val = math.sin(math.tau * f * t) * 0.55 + math.sin(math.tau * 300.0 * t) * 0.18
                val += math.sin(math.tau * 8.0 * t) * 0.10
            elif slot == 3:  # Tam Chi Kiem Quang: sharp metallic slash
                f = 1420.0 - 830.0 * k
                burst = 1.0 if k < 0.55 else max(0.0, 1.0 - (k - 0.55) / 0.45)
                val = math.sin(math.tau * f * t) * 0.55 + math.sin(math.tau * (f * 2.01) * t) * 0.22
                val += noise * 0.18 * burst
                env = (1.0 - k) ** 0.65
            elif slot == 4:  # Tu Chi Loi Anh: thunder crack + rumble
                crack = 1.0 if k < 0.18 else 0.24 * (1.0 - k)
                rumble = math.sin(math.tau * (70.0 + 35.0 * math.sin(phase_noise + k * 12.0)) * t)
                val = noise * 0.55 * crack + rumble * 0.46 + math.sin(math.tau * 440.0 * t) * 0.12
            else:  # Ngu Chi Dai Tran: ritual array rising chord
                base = 130.8
                val = 0.0
                for mul in (1.0, 1.5, 2.0, 3.0):
                    val += math.sin(math.tau * (base * mul + 90.0 * k) * t) * 0.20
                val += math.sin(math.tau * 11.0 * t) * 0.12

            frames.extend(int(clamp(val * env * 1.18, -1.0, 1.0) * 32767).to_bytes(2, "little", signed=True))
        wav.writeframes(frames)


class AudioEngine:
    def __init__(self):
        self.enabled = False
        self.meditation = None
        self.meditation_path = None
        self.sfx = {}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(12)
            self.enabled = True
        except pygame.error as exc:
            print(f"pygame mixer unavailable, fallback winsound: {exc}")

    def load(self, meditation_path: Path, sfx_paths: dict):
        self.meditation_path = meditation_path
        if not self.enabled:
            return
        self.meditation = pygame.mixer.Sound(str(meditation_path))
        self.meditation.set_volume(0.38)
        for key, path in sfx_paths.items():
            snd = pygame.mixer.Sound(str(path))
            snd.set_volume(1.0)
            self.sfx[key] = snd

    def play_loop(self):
        if self.enabled and self.meditation is not None:
            self.meditation.play(loops=-1, fade_ms=220)
        elif self.meditation_path is not None:
            winsound.PlaySound(str(self.meditation_path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)

    def stop_loop(self):
        if self.enabled and self.meditation is not None:
            self.meditation.fadeout(180)
        else:
            winsound.PlaySound(None, winsound.SND_ASYNC)

    def play(self, key, fallback_path: Path | None = None):
        if self.enabled and key in self.sfx:
            channel = self.sfx[key].play()
            if channel is not None:
                channel.set_volume(1.0)
        elif fallback_path is not None:
            winsound.PlaySound(str(fallback_path), winsound.SND_FILENAME | winsound.SND_ASYNC)

    def shutdown(self):
        if self.enabled:
            pygame.mixer.fadeout(120)
            pygame.mixer.quit()
        else:
            winsound.PlaySound(None, winsound.SND_ASYNC)


def beep_pattern(freqs, duration=90) -> None:
    def worker():
        for freq in freqs:
            try:
                winsound.Beep(int(freq), int(duration))
            except RuntimeError:
                winsound.MessageBeep()

    threading.Thread(target=worker, daemon=True).start()


def detect_clasp(hand_landmarks, w: int, h: int):
    if not hand_landmarks or len(hand_landmarks) < 2:
        return 0.0, None, None, None, "hands"

    la = hand_landmarks[0].landmark
    lb = hand_landmarks[1].landmark

    aw = la[0]
    bw = lb[0]
    ax, ay = int(aw.x * w), int(aw.y * h)
    bx, by = int(bw.x * w), int(bw.y * h)

    # Ultra-easy mode: mainly wrist proximity with very generous threshold.
    wrist_dx = abs(aw.x - bw.x)
    wrist_dy = abs(aw.y - bw.y)
    score = clamp(1.0 - wrist_dx / 0.40, 0.0, 1.0) * clamp(1.0 - wrist_dy / 0.34, 0.0, 1.0)

    cx = (ax + bx) // 2
    cy = (ay + by) // 2
    wrist_dist = int(math.hypot(ax - bx, ay - by))
    return score, (ax, ay), (bx, by), (cx, cy, wrist_dist), "hands"


def detect_pose_wrists(pose_landmarks, w: int, h: int):
    if pose_landmarks is None:
        return 0.0, None, None, None, "pose"

    lm = pose_landmarks.landmark
    left_shoulder = lm[11]
    right_shoulder = lm[12]
    left_wrist = lm[15]
    right_wrist = lm[16]
    min_vis = min(left_wrist.visibility, right_wrist.visibility, left_shoulder.visibility, right_shoulder.visibility)
    if min_vis < 0.28:
        return 0.0, None, None, None, "pose"

    ax, ay = int(left_wrist.x * w), int(left_wrist.y * h)
    bx, by = int(right_wrist.x * w), int(right_wrist.y * h)
    sx = abs(left_shoulder.x - right_shoulder.x)
    sy = abs(left_shoulder.y - right_shoulder.y)
    shoulder_span = max(0.18, math.hypot(sx, sy))
    wrist_dist_norm = math.hypot(left_wrist.x - right_wrist.x, left_wrist.y - right_wrist.y)
    wrist_dx = abs(left_wrist.x - right_wrist.x)
    wrist_dy = abs(left_wrist.y - right_wrist.y)

    # Pose is more stable than Hands when palms overlap. It only asks: are the two wrists close?
    close_score = clamp(1.0 - wrist_dist_norm / (shoulder_span * 0.82), 0.0, 1.0)
    center_score = clamp(1.0 - wrist_dx / (shoulder_span * 0.62), 0.0, 1.0)
    height_score = clamp(1.0 - wrist_dy / 0.26, 0.0, 1.0)
    score = max(close_score * 0.82 + center_score * 0.12 + height_score * 0.06, close_score)

    cx = (ax + bx) // 2
    cy = (ay + by) // 2
    wrist_dist = int(math.hypot(ax - bx, ay - by))
    return score, (ax, ay), (bx, by), (cx, cy, wrist_dist), "pose"


def detect_fist(hand_landmarks, handedness, w: int, h: int):
    if not hand_landmarks:
        return 0.0, None, "none"

    best_score = 0.0
    best_center = None
    best_side = "none"
    labels = []
    if handedness:
        labels = [item.classification[0].label for item in handedness]

    for idx, hand in enumerate(hand_landmarks):
        lm = hand.landmark
        closed = 0
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            if lm[tip].y > lm[pip].y - 0.015:
                closed += 1

        tips = [lm[i] for i in (8, 12, 16, 20)]
        wrist = lm[0]
        palm = lm[9]
        compact = sum(math.hypot(t.x - palm.x, t.y - palm.y) for t in tips) / 4.0
        palm_size = max(0.045, math.hypot(lm[5].x - lm[17].x, lm[5].y - lm[17].y))
        compact_score = clamp(1.0 - compact / (palm_size * 2.35), 0.0, 1.0)
        curl_score = closed / 4.0
        score = curl_score * 0.72 + compact_score * 0.28

        if score > best_score:
            best_score = score
            cx = int((wrist.x * 0.45 + palm.x * 0.55) * w)
            cy = int((wrist.y * 0.45 + palm.y * 0.55) * h)
            best_center = (cx, cy)
            best_side = labels[idx] if idx < len(labels) else "hand"

    return best_score, best_center, best_side


def detect_raised_fingers(hand_landmarks, handedness, w: int, h: int):
    if not hand_landmarks:
        return 0, None, "none", 0.0

    labels = []
    if handedness:
        labels = [item.classification[0].label for item in handedness]

    best_count = 0
    best_center = None
    best_side = "none"
    best_score = 0.0
    for idx, hand in enumerate(hand_landmarks):
        lm = hand.landmark
        side = labels[idx] if idx < len(labels) else "hand"
        count = 0
        confidence = 0.0

        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            up_margin = lm[pip].y - lm[tip].y
            if up_margin > 0.035:
                count += 1
                confidence += clamp(up_margin / 0.16, 0.0, 1.0)

        thumb_span = lm[4].x - lm[2].x
        thumb_open = thumb_span > 0.055 if side == "Left" else thumb_span < -0.055
        if thumb_open:
            count += 1
            confidence += 0.75

        if count > 0:
            center_x = int(sum(lm[i].x for i in (0, 5, 9, 13, 17)) / 5.0 * w)
            center_y = int(sum(lm[i].y for i in (0, 5, 9, 13, 17)) / 5.0 * h)
            score = confidence / max(1, count)
            if score > best_score:
                best_count = min(5, count)
                best_center = (center_x, center_y)
                best_side = side
                best_score = score

    return best_count, best_center, best_side, best_score


def draw_glow_circle(img, center, radius, color, alpha=0.38):
    overlay = img.copy()
    for i in range(4):
        r = int(radius * (1.0 + 0.45 * i))
        a = alpha / (1.4 + i)
        cv2.circle(overlay, center, r, color, -1)
        img[:] = cv2.addWeighted(overlay, a, img, 1.0 - a, 0)


def draw_lightning(img, start, end, color=(255, 250, 170), thickness=4, branches=9):
    points = [start]
    for i in range(1, branches):
        k = i / branches
        x = int(start[0] * (1.0 - k) + end[0] * k + random.randint(-42, 42))
        y = int(start[1] * (1.0 - k) + end[1] * k + random.randint(-28, 28))
        points.append((x, y))
    points.append(end)
    for i in range(len(points) - 1):
        cv2.line(img, points[i], points[i + 1], color, thickness)
        cv2.line(img, points[i], points[i + 1], (255, 255, 255), max(1, thickness // 2))


def load_vfx_assets():
    base = Path(__file__).resolve().parent / "assets" / "kenney_particle_pack" / "PNG (Transparent)"
    files = {
        "circle": "circle_05.png",
        "flare": "flare_01.png",
        "light": "light_03.png",
        "magic": "magic_05.png",
        "spark": "spark_06.png",
        "star": "star_09.png",
        "symbol": "symbol_02.png",
        "slash": "slash_04.png",
        "trace": "trace_07.png",
        "twirl": "twirl_03.png",
        "smoke": "smoke_08.png",
    }
    assets = {}
    for key, name in files.items():
        img = cv2.imread(str(base / name), cv2.IMREAD_UNCHANGED)
        if img is not None and img.shape[2] == 4:
            assets[key] = img
    return assets


def overlay_asset(frame, asset, center, size, angle=0.0, alpha=1.0, tint=None):
    if asset is None or size <= 2:
        return

    patch = cv2.resize(asset, (int(size), int(size)), interpolation=cv2.INTER_LANCZOS4)
    if abs(angle) > 0.01:
        h, w = patch.shape[:2]
        mat = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        patch = cv2.warpAffine(patch, mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    rgb = patch[:, :, :3].astype(np.float32)
    mask = (patch[:, :, 3:4].astype(np.float32) / 255.0) * alpha
    if tint is not None:
        tint_arr = np.array(tint, dtype=np.float32).reshape((1, 1, 3))
        rgb = np.minimum(255.0, rgb * 0.32 + tint_arr * 1.05)

    x = int(center[0] - patch.shape[1] / 2)
    y = int(center[1] - patch.shape[0] / 2)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame.shape[1], x + patch.shape[1]), min(frame.shape[0], y + patch.shape[0])
    if x0 >= x1 or y0 >= y1:
        return

    px0, py0 = x0 - x, y0 - y
    px1, py1 = px0 + (x1 - x0), py0 + (y1 - y0)
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    roi_mask = mask[py0:py1, px0:px1]
    roi_rgb = rgb[py0:py1, px0:px1]
    frame[y0:y1, x0:x1] = np.clip(roi_rgb * roi_mask + roi * (1.0 - roi_mask), 0, 255).astype(np.uint8)


def draw_hand_debug(frame, hand_landmarks, handedness=None):
    if not hand_landmarks:
        return

    h, w = frame.shape[:2]
    labels = []
    if handedness:
        labels = [item.classification[0].label for item in handedness]

    for hand_idx, hand in enumerate(hand_landmarks):
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmark]
        label = labels[hand_idx] if hand_idx < len(labels) else f"hand{hand_idx + 1}"
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (70, 230, 255), 2)
            cv2.line(frame, pts[a], pts[b], (10, 40, 50), 1)
        for idx, p in enumerate(pts):
            color = (70, 255, 160) if idx in FINGER_TIPS else (255, 235, 130)
            radius = 5 if idx in FINGER_TIPS else 3
            cv2.circle(frame, p, radius, color, -1)
            if idx in FINGER_TIPS or idx == 0:
                cv2.putText(frame, str(idx), (p[0] + 5, p[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        cv2.putText(frame, label, (pts[0][0] - 20, pts[0][1] + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 245, 255), 1)


def draw_panel(frame, x, y, w, h, alpha=0.48, border=(120, 220, 255)):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (8, 10, 18), -1)
    frame[:] = cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0)
    cv2.rectangle(frame, (x, y), (x + w, y + h), border, 1)


def draw_bar(frame, x, y, w, h, ratio, fill, back=(45, 48, 58)):
    ratio = clamp(ratio, 0.0, 1.0)
    cv2.rectangle(frame, (x, y), (x + w, y + h), back, -1)
    cv2.rectangle(frame, (x, y), (x + int(w * ratio), y + h), fill, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (170, 180, 195), 1)


def draw_skill_vfx(frame, level, progress, center):
    h, w = frame.shape[:2]
    cx, cy = center
    pulse = 0.5 + 0.5 * math.sin(time.time() * 16.0)
    overlay = frame.copy()

    if level == 0:
        radius = int(70 + 260 * progress)
        draw_glow_circle(frame, center, max(28, radius), (70, 210, 255), alpha=0.36)
        cv2.circle(frame, center, radius, (255, 245, 120), 5)
        for i in range(18):
            ang = i * math.tau / 18 + progress * math.tau * 1.8
            p1 = (int(cx + math.cos(ang) * 28), int(cy + math.sin(ang) * 28))
            p2 = (int(cx + math.cos(ang) * (radius + 42)), int(cy + math.sin(ang) * (radius + 42)))
            cv2.line(frame, p1, p2, (90, 245, 255), 3)

    elif level == 1:
        radius = int(min(w, h) * (0.24 + 0.04 * pulse))
        pts = []
        for i in range(8):
            ang = i * math.tau / 8 + progress * math.tau * 0.5
            pts.append([int(cx + math.cos(ang) * radius), int(cy + math.sin(ang) * radius)])
        cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], (80, 210, 255))
        frame[:] = cv2.addWeighted(overlay, 0.30, frame, 0.70, 0)
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (255, 245, 140), 7)
        cv2.circle(frame, center, radius + 28, (180, 250, 255), 4)

    elif level == 2:
        orb = int(55 + 34 * pulse)
        draw_glow_circle(frame, center, orb + 36, (80, 220, 255), alpha=0.42)
        cv2.circle(frame, center, orb, (70, 205, 255), -1)
        cv2.circle(frame, center, orb + 10, (255, 245, 120), 6)
        for i in range(24):
            ang = i * math.tau / 24 + progress * math.tau * 3.0
            p2 = (int(cx + math.cos(ang) * (orb + 230)), int(cy + math.sin(ang) * (orb + 230)))
            cv2.line(frame, center, p2, (60, 235, 255), 2)

    elif level == 3:
        ghost = cv2.GaussianBlur(frame, (0, 0), 5.0)
        for side, color in [(-1, (140, 180, 255)), (1, (255, 170, 230))]:
            shift = int(side * (80 + 130 * math.sin(progress * math.pi)))
            m = np.float32([[1, 0, shift], [0, 1, 0]])
            clone = cv2.warpAffine(ghost, m, (w, h), borderMode=cv2.BORDER_REFLECT)
            tint = clone.copy()
            tint[:] = color
            clone = cv2.addWeighted(clone, 0.55, tint, 0.45, 0)
            frame[:] = cv2.addWeighted(clone, 0.28, frame, 0.72, 0)
        slash_y = int(cy + math.sin(progress * math.tau * 2.0) * 120)
        cv2.line(frame, (40, slash_y), (w - 40, slash_y - 100), (255, 255, 255), 8)
        cv2.line(frame, (40, slash_y + 16), (w - 40, slash_y - 84), (180, 210, 255), 4)

    elif level == 4:
        x = int((progress % 1.0) * w)
        cv2.rectangle(overlay, (max(0, x - 80), 0), (min(w, x + 80), h), (80, 255, 210), -1)
        frame[:] = cv2.addWeighted(overlay, 0.32, frame, 0.68, 0)
        for yy in range(60, h, 86):
            cv2.line(frame, (0, yy), (w, yy), (110, 255, 220), 2)
        cv2.circle(frame, center, int(120 + 380 * progress), (120, 255, 230), 5)

    elif level == 5:
        storm = frame.copy()
        storm[:] = (35, 35, 70)
        frame[:] = cv2.addWeighted(storm, 0.18, frame, 0.82, 0)
        for i in range(5):
            sx = int((i + 0.5) * w / 5 + random.randint(-70, 70))
            end = (int(cx + random.randint(-180, 180)), int(cy + random.randint(-80, 180)))
            draw_lightning(frame, (sx, 0), end, thickness=random.randint(3, 7), branches=10)
        cv2.circle(frame, center, int(90 + 180 * pulse), (255, 250, 150), 8)

    else:
        radius = int(min(w, h) * (0.28 + 0.03 * pulse))
        angle = progress * 720.0
        cv2.ellipse(overlay, center, (radius, radius), angle, 0, 180, (235, 235, 255), -1)
        cv2.ellipse(overlay, center, (radius, radius), angle, 180, 360, (35, 35, 55), -1)
        frame[:] = cv2.addWeighted(overlay, 0.42, frame, 0.58, 0)
        cv2.circle(frame, center, radius, (255, 240, 120), 7)
        for i in range(16):
            ang = i * math.tau / 16 - progress * math.tau
            p1 = (int(cx + math.cos(ang) * radius), int(cy + math.sin(ang) * radius))
            p2 = (int(cx + math.cos(ang) * (radius + 150)), int(cy + math.sin(ang) * (radius + 150)))
            cv2.line(frame, p1, p2, (175, 235, 255), 3)


def draw_slot_vfx(frame, slot, progress, center, assets=None):
    h, w = frame.shape[:2]
    cx, cy = center
    overlay = frame.copy()
    pulse = 0.5 + 0.5 * math.sin(time.time() * 18.0)
    assets = assets or {}

    if slot == 1:
        radius = int(36 + 260 * progress)
        overlay_asset(frame, assets.get("spark"), center, int(210 + 380 * progress), progress * 720, 0.90, (90, 245, 255))
        overlay_asset(frame, assets.get("flare"), center, int(130 + 180 * pulse), -progress * 540, 0.78, (255, 230, 120))
        cv2.circle(frame, center, radius, (80, 255, 255), 5)
        for i in range(10):
            ang = progress * math.tau * 4.0 + i * math.tau / 10
            p = (int(cx + math.cos(ang) * radius), int(cy + math.sin(ang) * radius))
            cv2.circle(frame, p, 8, (255, 245, 130), -1)
    elif slot == 2:
        radius = int(min(w, h) * (0.18 + pulse * 0.04))
        overlay_asset(frame, assets.get("circle"), center, int(radius * 2.9), progress * 140, 0.92, (90, 210, 255))
        overlay_asset(frame, assets.get("magic"), center, int(radius * 2.25), -progress * 220, 0.55, (255, 230, 120))
        cv2.circle(overlay, center, radius, (90, 190, 255), -1)
        frame[:] = cv2.addWeighted(overlay, 0.28, frame, 0.72, 0)
        for i in range(3):
            cv2.circle(frame, center, radius + i * 24, (255, 235, 120), 4)
    elif slot == 3:
        slash_len = int(min(w, h) * 0.34)
        overlay_asset(frame, assets.get("slash"), center, int(min(w, h) * 0.42), -18 + 18 * math.sin(progress * math.pi), 0.46, (120, 230, 255))
        overlay_asset(frame, assets.get("trace"), center, int(min(w, h) * 0.34), 25, 0.32, (255, 255, 255))
        for i in range(3):
            offset = int((i - 1) * 42 + math.sin(progress * math.tau + i) * 14)
            p1 = (int(cx - slash_len * 0.62), int(cy + offset + slash_len * 0.22))
            p2 = (int(cx + slash_len * 0.62), int(cy + offset - slash_len * 0.22))
            cv2.line(frame, p1, p2, (255, 255, 245), 4)
            cv2.line(frame, (p1[0], p1[1] + 8), (p2[0], p2[1] + 8), (110, 225, 255), 2)
    elif slot == 4:
        overlay_asset(frame, assets.get("light"), center, int(min(w, h) * (0.78 + pulse * 0.18)), progress * 360, 0.72, (120, 150, 255))
        overlay_asset(frame, assets.get("star"), center, int(240 + 180 * pulse), -progress * 480, 0.82, (255, 245, 150))
        for i in range(4):
            sx = int((i + 0.5) * w / 4 + random.randint(-60, 60))
            ex = int(cx + random.randint(-220, 220))
            ey = int(cy + random.randint(-120, 160))
            draw_lightning(frame, (sx, 0), (ex, ey), (255, 245, 140), random.randint(3, 6), 8)
        cv2.circle(frame, center, int(70 + 150 * pulse), (190, 210, 255), 5)
    else:
        radius = int(min(w, h) * (0.18 + progress * 0.28))
        overlay_asset(frame, assets.get("symbol"), center, int(radius * 2.45), progress * 260, 0.95, (220, 150, 255))
        overlay_asset(frame, assets.get("twirl"), center, int(radius * 2.1), -progress * 480, 0.78, (255, 220, 120))
        overlay_asset(frame, assets.get("smoke"), center, int(radius * 2.75), progress * 90, 0.46, (180, 180, 255))
        cv2.circle(overlay, center, radius, (190, 110, 255), -1)
        frame[:] = cv2.addWeighted(overlay, 0.36, frame, 0.64, 0)
        for i in range(18):
            ang = i * math.tau / 18 + progress * math.tau * 2.0
            p1 = (int(cx + math.cos(ang) * 50), int(cy + math.sin(ang) * 50))
            p2 = (int(cx + math.cos(ang) * (radius + 150)), int(cy + math.sin(ang) * (radius + 150)))
            cv2.line(frame, p1, p2, (255, 225, 120), 3)


def enhance_frame_visual(frame: np.ndarray) -> np.ndarray:
    return frame


def main() -> int:
    tmp_wav = Path(tempfile.gettempdir()) / "thien_dotpha_loop.wav"
    create_meditation_wav(tmp_wav)
    sound_dir = Path(tempfile.gettempdir()) / "thien_dotpha_sfx"
    sound_dir.mkdir(exist_ok=True)
    breakthrough_wav = sound_dir / "breakthrough.wav"
    create_effect_wav(breakthrough_wav, [146.8, 220.0, 440.0], 1.15, volume=0.82, sweep=220.0)
    skill_wavs = [
        sound_dir / "skill_1_lingdan.wav",
        sound_dir / "skill_2_barrier.wav",
        sound_dir / "skill_3_sword.wav",
        sound_dir / "skill_4_thunder.wav",
        sound_dir / "skill_5_array.wav",
    ]
    for idx, path in enumerate(skill_wavs, start=1):
        create_named_skill_wav(path, idx)
    skill_beeps = [
        [720, 1040],
        [260, 330, 260],
        [1320, 820],
        [120, 80, 420],
        [196, 294, 392, 588],
    ]
    audio = AudioEngine()
    audio.load(
        tmp_wav,
        {
            "breakthrough": breakthrough_wav,
            "skill_1": skill_wavs[0],
            "skill_2": skill_wavs[1],
            "skill_3": skill_wavs[2],
            "skill_4": skill_wavs[3],
            "skill_5": skill_wavs[4],
        },
    )
    vfx_assets = load_vfx_assets()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print("Cannot open webcam")
        return 2

    hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.62,
        min_tracking_confidence=0.62,
    )
    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=0,
        smooth_landmarks=True,
        min_detection_confidence=0.45,
        min_tracking_confidence=0.45,
    )

    score = 0.0
    fist_score = 0.0
    fist_side = "none"
    fist_center = None
    fist_hold_time = 0.0
    finger_count = 0
    finger_side = "none"
    finger_center = None
    finger_hold_time = 0.0
    no_finger_time = 0.0
    pending_skill_slot = 1
    selected_skill_slot = 1
    skill_armed_time = 0.0
    detector_source = "none"
    clasp_active = False
    active_hold_timer = 0.0
    merit_seconds = 0.0
    level = 0
    sound_on = False

    flash = 0.0
    shake_time = 0.0
    shake_amp = 0.0
    banner = ""
    banner_time = 0.0
    skill_banner = ""
    skill_banner_time = 0.0
    active_skill = -1
    active_skill_slot = 1
    active_skill_started = 0.0
    active_skill_until = 0.0
    active_skill_center = (DISPLAY_W // 2, DISPLAY_H // 2)
    skill_cooldown = 0.0
    sparks = []
    dust = []
    spirit_wave_t = 0.0
    lightning_t = 0.0
    yin_angle = 0.0
    show_hand_net = True

    last = time.perf_counter()
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, DISPLAY_W, DISPLAY_H)
    beep_pattern([440, 660, 880], 90)
    audio.play("skill_1", skill_wavs[0])
    print("Audio test: neu nghe 3 tieng beep la am thanh dang hoat dong. Bam T de test lai.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            now = time.perf_counter()
            dt = now - last
            last = now
            skill_cooldown = max(0.0, skill_cooldown - dt)
            skill_running = active_skill >= 0 and now < active_skill_until

            frame = cv2.resize(frame, (DISPLAY_W, DISPLAY_H), interpolation=cv2.INTER_LANCZOS4)
            h, w = frame.shape[:2]
            frame_enhanced = enhance_frame_visual(frame)
            rgb = cv2.cvtColor(frame_enhanced, cv2.COLOR_BGR2RGB)
            hand_res = hands.process(rgb)
            pose_res = pose.process(rgb)
            frame = frame_enhanced

            hand_raw, hand_pa, hand_pb, hand_center, hand_source = detect_clasp(hand_res.multi_hand_landmarks, w, h)
            pose_raw, pose_pa, pose_pb, pose_center, pose_source = detect_pose_wrists(pose_res.pose_landmarks, w, h)
            if pose_raw >= hand_raw:
                raw, pa, pb, center_data, detector_source = pose_raw, pose_pa, pose_pb, pose_center, pose_source
            else:
                raw, pa, pb, center_data, detector_source = hand_raw, hand_pa, hand_pb, hand_center, hand_source
            score = smooth(score, raw, 0.3)
            is_close_now = score > 0.14
            if is_close_now:
                active_hold_timer = 0.55
            else:
                active_hold_timer = max(0.0, active_hold_timer - dt)
            clasp_active = active_hold_timer > 0.0

            skill_armed_time = max(0.0, skill_armed_time - dt)
            raw_finger_count, raw_finger_center, raw_finger_side, finger_conf = detect_raised_fingers(hand_res.multi_hand_landmarks, hand_res.multi_handedness, w, h)
            selecting_finger = (not clasp_active) and raw_finger_count > 0 and finger_conf > FINGER_SELECT_CONF
            if selecting_finger:
                no_finger_time = 0.0
                if raw_finger_count == pending_skill_slot:
                    finger_hold_time += dt
                else:
                    pending_skill_slot = raw_finger_count
                    finger_hold_time = 0.0
                finger_count = raw_finger_count
                finger_center = raw_finger_center
                finger_side = raw_finger_side
                if finger_hold_time >= FINGER_SELECT_HOLD and selected_skill_slot != pending_skill_slot:
                    selected_skill_slot = pending_skill_slot
                    slot_name, _ = SKILL_SLOTS[selected_skill_slot - 1]
                    skill_armed_time = SKILL_ARM_SECONDS
                elif finger_hold_time >= FINGER_SELECT_HOLD:
                    skill_armed_time = SKILL_ARM_SECONDS
            else:
                finger_count = 0
                finger_center = None
                finger_side = "none"
                finger_hold_time = 0.0
                no_finger_time += dt

            raw_fist, raw_fist_center, raw_fist_side = detect_fist(hand_res.multi_hand_landmarks, hand_res.multi_handedness, w, h)
            if selecting_finger or clasp_active:
                raw_fist = 0.0
            fist_score = smooth(fist_score, raw_fist, 0.28)
            skill_armed = skill_armed_time > 0.0
            fist_active = fist_score > FIST_CAST_THRESHOLD and skill_armed and not selecting_finger and not clasp_active
            if fist_active:
                fist_hold_time += dt
                fist_center = raw_fist_center if raw_fist_center is not None else fist_center
                fist_side = raw_fist_side
            else:
                fist_hold_time = 0.0
                fist_center = None
                fist_side = "none"

            if clasp_active and level < len(LEVELS) - 1:
                gain_mult = 1.0
                if level >= 2:  # Ket Dan skill: Kim Dan Quang
                    gain_mult = 1.35
                if level >= 4:  # Hoa Than upgrade
                    gain_mult = 1.55
                if skill_running and active_skill == 4:
                    gain_mult += 0.75
                if skill_running and active_skill == 6:
                    gain_mult += 1.25
                merit_seconds = min(TARGET_SECONDS, merit_seconds + dt * gain_mult)
            elif not clasp_active:
                decay = 0.55
                if level >= 1:  # Truc Co skill: Ho The
                    decay = 0.20
                if level >= 6:  # Am Duong Hu Thuc almost no decay
                    decay = 0.08
                if skill_running and active_skill in (1, 6):
                    decay = 0.0
                merit_seconds = max(0.0, merit_seconds - dt * decay)

            if clasp_active and not sound_on:
                audio.play_loop()
                sound_on = True
            elif not clasp_active and sound_on:
                audio.stop_loop()
                sound_on = False

            if merit_seconds >= TARGET_SECONDS and level < len(LEVELS) - 1:
                level += 1
                merit_seconds = 0.0
                flash = 1.0
                shake_time = 0.9
                shake_amp = 16.0
                skill_name, skill_desc = SKILLS[level]
                banner = f"DOT PHA CANH GIOI: {LEVELS[level]}"
                banner_time = 2.0
                skill_banner = f"MO KHOA SKILL: {skill_name} - {skill_desc}"
                skill_banner_time = 2.8
                audio.play("breakthrough", breakthrough_wav)
                beep_pattern([220, 330, 440, 660], 95)
                sound_on = False
                if center_data is not None:
                    cx, cy, _ = center_data
                    for _ in range(140):
                        ang = random.uniform(0, math.tau)
                        spd = random.uniform(160, 520)
                        sparks.append([cx, cy, math.cos(ang) * spd, math.sin(ang) * spd, random.uniform(0.5, 1.1)])

            if fist_active and fist_hold_time >= FIST_CAST_HOLD and skill_cooldown <= 0.0 and not skill_running:
                active_skill = level
                active_skill_slot = selected_skill_slot
                skill_armed_time = 0.0
                active_skill_started = now
                active_skill_until = now + SKILL_DURATIONS[level] + selected_skill_slot * 0.12
                active_skill_center = fist_center if fist_center is not None else (w // 2, h // 2)
                skill_cooldown = SKILL_COOLDOWN
                skill_running = True
                skill_name, _ = SKILLS[level]
                slot_name, _ = SKILL_SLOTS[selected_skill_slot - 1]
                skill_banner = f"NAM TAY {fist_side.upper()} THI TRIEN: {slot_name}"
                skill_banner_time = 1.6
                audio.play(f"skill_{selected_skill_slot}", skill_wavs[selected_skill_slot - 1])
                beep_pattern(skill_beeps[selected_skill_slot - 1], 85)
                sound_on = False
                flash = max(flash, 0.24 if selected_skill_slot == 3 else 0.42)
                shake_time = max(shake_time, 0.38)
                shake_amp = max(shake_amp, 8.0 + selected_skill_slot * 3.0)
                bonus = [0.8, 0.35, 1.8, 1.0, 0.6, 2.4, 1.4][level] + selected_skill_slot * 0.18
                merit_seconds = min(TARGET_SECONDS, merit_seconds + bonus)
                sx, sy = active_skill_center
                for _ in range(70 + level * 20 + selected_skill_slot * 28):
                    ang = random.uniform(0, math.tau)
                    spd = random.uniform(180, 720)
                    sparks.append([sx, sy, math.cos(ang) * spd, math.sin(ang) * spd, random.uniform(0.45, 1.0)])

            # atmospheric color wash
            t = time.time()
            wash = frame.copy()
            for i in range(5):
                px = int((0.12 + i * 0.2 + 0.03 * math.sin(t + i)) * w)
                py = int((0.16 + (i % 3) * 0.24 + 0.04 * math.cos(t * 0.7 + i)) * h)
                rr = int(95 + 46 * math.sin(t * 0.9 + i))
                col = [(255, 180, 120), (150, 220, 255), (210, 160, 255), (155, 255, 205), (255, 220, 140)][i]
                cv2.circle(wash, (px, py), max(40, rr), col, -1)
            wash_alpha = 0.0
            if clasp_active:
                wash_alpha = 0.10
            if active_skill >= 0 and now < active_skill_until:
                wash_alpha = 0.13
            frame = cv2.addWeighted(wash, wash_alpha, frame, 1.0 - wash_alpha, 0)

            # dust sweep
            if len(dust) < 180:
                add_n = 5 if clasp_active else 2
                for _ in range(add_n):
                    dust.append([
                        random.uniform(0, w), random.uniform(0, h),
                        random.uniform(-15, 15), random.uniform(-35, -8),
                        random.uniform(1.0, 3.0), random.uniform(0.18, 0.58)
                    ])
            dust_overlay = frame.copy()
            next_dust = []
            for x, y, vx, vy, rad, a in dust:
                nx = x + vx * dt
                ny = y + vy * dt
                na = a - dt * (0.20 if not clasp_active else 0.10)
                if 0 <= nx < w and 0 <= ny < h and na > 0.02:
                    next_dust.append([nx, ny, vx, vy, rad, na])
                    c = (230, 250, 255) if clasp_active else (170, 170, 190)
                    cv2.circle(dust_overlay, (int(nx), int(ny)), int(rad), c, -1)
            dust = next_dust
            frame = cv2.addWeighted(dust_overlay, 0.30 if clasp_active else 0.16, frame, 0.84 if clasp_active else 0.88, 0)

            # Nguyen Anh skill: afterimage split (boosted visibility)
            if level >= 3:
                ghost = cv2.GaussianBlur(frame, (0, 0), 3.2)
                shift = int(34 + 18 * math.sin(time.time() * 5.2))
                m1 = np.float32([[1, 0, -shift], [0, 1, 0]])
                m2 = np.float32([[1, 0, shift], [0, 1, 0]])
                left_ghost = cv2.warpAffine(ghost, m1, (w, h), borderMode=cv2.BORDER_REFLECT)
                right_ghost = cv2.warpAffine(ghost, m2, (w, h), borderMode=cv2.BORDER_REFLECT)
                frame = cv2.addWeighted(left_ghost, 0.22, frame, 0.78, 0)
                frame = cv2.addWeighted(right_ghost, 0.22, frame, 0.78, 0)
                cv2.putText(frame, "NGUYEN ANH PHAN ANH", (w // 2 - 180, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.92, (210, 210, 255), 3)

            # Hoa Than skill: spirit wave pulse
            if level >= 4:
                spirit_wave_t += dt * 2.3
                wave_overlay = frame.copy()
                cx, cy = w // 2, h // 2
                for k in range(3):
                    rr = int((spirit_wave_t * 220 + k * 140) % (max(w, h)))
                    if rr > 12:
                        cv2.circle(wave_overlay, (cx, cy), rr, (140, 210, 255), 2)
                frame = cv2.addWeighted(wave_overlay, 0.18, frame, 0.82, 0)

            # Van Dinh skill: lightning strikes
            if level >= 5:
                lightning_t -= dt
                if lightning_t <= 0.0:
                    lightning_t = random.uniform(0.18, 0.45)
                    x = random.randint(60, w - 60)
                    y = 0
                    bolt = [(x, y)]
                    for _ in range(8):
                        x += random.randint(-35, 35)
                        y += random.randint(50, 95)
                        bolt.append((clamp(x, 20, w - 20), min(y, h - 10)))
                    bolt_overlay = frame.copy()
                    for i in range(len(bolt) - 1):
                        p1 = (int(bolt[i][0]), int(bolt[i][1]))
                        p2 = (int(bolt[i + 1][0]), int(bolt[i + 1][1]))
                        cv2.line(bolt_overlay, p1, p2, (255, 250, 180), 3)
                    frame = cv2.addWeighted(bolt_overlay, 0.42, frame, 0.58, 0)

            # Am Duong Hu Thuc skill: rotating dual-field overlay
            if level >= 6:
                yin_angle += dt * 85.0
                yg = frame.copy()
                cx, cy = w // 2, h // 2
                r = int(min(w, h) * 0.28)
                cv2.ellipse(yg, (cx, cy), (r, r), yin_angle, 0, 180, (235, 235, 255), -1)
                cv2.ellipse(yg, (cx, cy), (r, r), yin_angle, 180, 360, (50, 50, 70), -1)
                cv2.circle(yg, (cx, cy), int(r * 0.5), (120, 120, 170), 2)
                frame = cv2.addWeighted(yg, 0.12, frame, 0.88, 0)

            if active_skill >= 0 and now < active_skill_until:
                duration = SKILL_DURATIONS[active_skill] + active_skill_slot * 0.12
                progress = clamp((now - active_skill_started) / duration, 0.0, 1.0)
                draw_skill_vfx(frame, active_skill, progress, active_skill_center)
                draw_slot_vfx(frame, active_skill_slot, progress, active_skill_center, vfx_assets)
                cv2.rectangle(frame, (w // 2 - 330, h - 142), (w // 2 + 330, h - 92), (8, 8, 18), -1)
                cv2.rectangle(frame, (w // 2 - 330, h - 142), (w // 2 + 330, h - 92), (255, 220, 110), 3)
                cv2.putText(frame, f"DANG THI TRIEN: {SKILL_SLOTS[active_skill_slot - 1][0]}", (w // 2 - 300, h - 107), cv2.FONT_HERSHEY_SIMPLEX, 0.86, (255, 245, 160), 3)
            elif active_skill >= 0:
                active_skill = -1

            if show_hand_net:
                draw_hand_debug(frame, hand_res.multi_hand_landmarks, hand_res.multi_handedness)

            # clasp visuals
            if clasp_active and pa and pb and center_data:
                x1, y1 = pa
                x2, y2 = pb
                cx, cy, dist_px = center_data
                cv2.line(frame, (x1, y1), (x2, y2), (85, 255, 185), 3)
                pad = 42
                cv2.rectangle(frame, (min(x1, x2) - pad, min(y1, y2) - pad), (max(x1, x2) + pad, max(y1, y2) + pad), (120, 240, 255), 3)

                ring_radius = max(48, int(dist_px * 1.45))
                ring_color = (90, 225, 255) if not clasp_active else (100, 235, 255)
                cv2.circle(frame, (cx, cy), ring_radius, ring_color, 4)
                pulse = int(16 + 10 * math.sin(time.time() * 9.0))
                draw_glow_circle(frame, (cx, cy), ring_radius + pulse, (110, 220, 255), alpha=0.48)
                cv2.circle(frame, (cx, cy), ring_radius + pulse + 12, (140, 235, 255), 3)
                cv2.putText(frame, "VONG VANG: ACTIVE", (cx - 165, cy - ring_radius - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 245, 150), 3)

                # Truc Co skill visual: Ho The shield layer
                if level >= 1:
                    shield_r = ring_radius + 34 + int(10 * math.sin(time.time() * 6.0))
                    shield_col = (200, 255, 220)
                    cv2.circle(frame, (cx, cy), shield_r, shield_col, 3)
                    shield_overlay = frame.copy()
                    cv2.circle(shield_overlay, (cx, cy), shield_r - 6, (120, 220, 170), -1)
                    frame = cv2.addWeighted(shield_overlay, 0.14, frame, 0.86, 0)

                # Ket Dan skill visual: Kim Dan Quang core orb
                if level >= 2:
                    orb_r = 14 + int(4 * math.sin(time.time() * 8.2))
                    cv2.circle(frame, (cx, cy), orb_r, (110, 230, 255), -1)
                    orb_overlay = frame.copy()
                    cv2.circle(orb_overlay, (cx, cy), orb_r + 16, (140, 245, 255), -1)
                    frame = cv2.addWeighted(orb_overlay, 0.30, frame, 0.70, 0)

            # sparks
            if sparks:
                keep = []
                for x, y, vx, vy, life in sparks:
                    nx = x + vx * dt
                    ny = y + vy * dt
                    nvx = vx * (0.96 ** (dt * 60))
                    nvy = vy * (0.96 ** (dt * 60)) + 220 * dt
                    nlife = life - dt
                    if 0 <= nx < w and 0 <= ny < h and nlife > 0:
                        keep.append([nx, ny, nvx, nvy, nlife])
                        col = (255, 240, 120) if nlife > 0.45 else (255, 170, 80)
                        cv2.circle(frame, (int(nx), int(ny)), 3, col, -1)
                sparks = keep

            if fist_center is not None:
                fx, fy = fist_center
                fist_col = (80, 255, 160) if fist_score > FIST_CAST_THRESHOLD else (120, 180, 220)
                cv2.circle(frame, (fx, fy), 44, fist_col, 4)
                cv2.circle(frame, (fx, fy), 58 + int(8 * math.sin(time.time() * 12.0)), (255, 230, 110), 3)
                cv2.putText(frame, "NAM TAY: SKILL", (fx - 118, fy - 62), cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 245, 160), 2)

            if finger_center is not None and finger_count > 0:
                gx, gy = finger_center
                select_pct = min(100, int((finger_hold_time / FINGER_SELECT_HOLD) * 100))
                cv2.circle(frame, (gx, gy), 22, (120, 225, 255), 2)
                cv2.putText(frame, f"S{finger_count} {select_pct}%", (gx - 34, gy - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (210, 245, 255), 1)

            # HUD
            hud_h = 104
            draw_panel(frame, 14, 14, 440, hud_h, 0.42, (95, 170, 210))
            cv2.putText(frame, f"CANH GIOI  {LEVELS[level]}", (30, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 232, 130), 2)
            state_col = (120, 255, 180) if clasp_active else (190, 195, 205)
            cv2.putText(frame, f"Thien: {'ON' if clasp_active else 'OFF'}    CV: {detector_source}", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.50, state_col, 1)
            cv2.putText(frame, f"Clasp", (30, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (210, 230, 240), 1)
            draw_bar(frame, 92, 88, 120, 10, score, (105, 230, 255))
            cv2.putText(frame, f"Fist", (232, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (210, 230, 240), 1)
            draw_bar(frame, 286, 88, 120, 10, fist_score / FIST_CAST_THRESHOLD, (120, 255, 170))
            skill_name, skill_desc = SKILLS[level]
            slot_name, slot_desc = SKILL_SLOTS[selected_skill_slot - 1]
            panel_w = 500
            draw_panel(frame, w - panel_w - 14, 14, panel_w, hud_h, 0.42, (130, 210, 255))
            px = w - panel_w
            cv2.putText(frame, f"REALM SKILL  {skill_name}", (px + 6, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (155, 235, 255), 2)
            cv2.putText(frame, f"SELECTED {selected_skill_slot}: {slot_name}", (px + 6, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 240, 170), 1)
            cd_text = "READY" if skill_cooldown <= 0.0 else f"CD {skill_cooldown:.1f}s"
            cd_color = (130, 255, 170) if skill_cooldown <= 0.0 else (160, 190, 220)
            fist_pct = min(100, int((fist_hold_time / FIST_CAST_HOLD) * 100)) if fist_active else 0
            if clasp_active:
                hint = "dang thien: khoa skill"
            elif skill_armed_time > 0.0:
                hint = f"skill {selected_skill_slot} san sang: nam tay de cast {fist_pct}% | {cd_text}"
            else:
                hint = "giu 1-5 ngon ro de chon skill | H: net tay | T: test am"
            cv2.putText(frame, hint, (px + 6, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.44, cd_color, 1)

            bar_x, bar_y, bar_w, bar_h = 20, h - 60, w - 40, 34
            draw_panel(frame, bar_x - 4, bar_y - 26, bar_w + 8, 58, 0.36, (120, 205, 180))
            ratio = merit_seconds / TARGET_SECONDS
            fill_col = (100, 245, 180) if clasp_active else (160, 160, 160)
            cv2.putText(frame, f"CONG DUC {merit_seconds:.1f}s / {TARGET_SECONDS:.0f}s", (bar_x + 8, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (235, 245, 240), 1)
            draw_bar(frame, bar_x + 8, bar_y + 4, bar_w - 16, 18, ratio, fill_col)

            if banner_time > 0:
                banner_time -= dt
                cv2.rectangle(frame, (w // 2 - 420, 108), (w // 2 + 420, 190), (18, 18, 24), -1)
                cv2.rectangle(frame, (w // 2 - 420, 108), (w // 2 + 420, 190), (90, 90, 120), 2)
                cv2.putText(frame, banner, (w // 2 - 370, 162), cv2.FONT_HERSHEY_SIMPLEX, 1.08, (255, 220, 120), 4)

            if skill_banner_time > 0:
                skill_banner_time -= dt
                cv2.rectangle(frame, (w // 2 - 520, 198), (w // 2 + 520, 248), (10, 16, 28), -1)
                cv2.rectangle(frame, (w // 2 - 520, 198), (w // 2 + 520, 248), (120, 210, 255), 2)
                cv2.putText(frame, skill_banner, (w // 2 - 490, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.74, (190, 245, 255), 2)

            if flash > 0.0:
                flash = max(0.0, flash - dt * 1.6)
                bright = frame.copy()
                bright[:] = (220, 245, 255)
                frame = cv2.addWeighted(bright, flash * 0.75, frame, 1.0 - flash * 0.75, 0)

            if shake_time > 0.0:
                shake_time = max(0.0, shake_time - dt)
                strength = shake_amp * (shake_time / 0.9)
                ox = int(random.uniform(-strength, strength))
                oy = int(random.uniform(-strength, strength))
                m = np.float32([[1, 0, ox], [0, 1, oy]])
                frame = cv2.warpAffine(frame, m, (w, h), borderMode=cv2.BORDER_REFLECT)

            cv2.imshow(WINDOW_TITLE, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("f"):
                current = cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN)
                is_full = current == cv2.WINDOW_FULLSCREEN
                cv2.setWindowProperty(
                    WINDOW_TITLE,
                    cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_NORMAL if is_full else cv2.WINDOW_FULLSCREEN,
                )
            if key == ord("t"):
                beep_pattern([440, 660, 880], 90)
                audio.play(f"skill_{selected_skill_slot}", skill_wavs[max(0, min(selected_skill_slot - 1, len(skill_wavs) - 1))])
            if key == ord("h"):
                show_hand_net = not show_hand_net
            if ord("1") <= key <= ord("7"):
                level = key - ord("1")
                level = max(0, min(level, len(LEVELS) - 1))
                skill_name, skill_desc = SKILLS[level]
                banner = f"CANH GIOI: {LEVELS[level]}"
                banner_time = 1.2
                skill_banner = f"SKILL: {skill_name} - {skill_desc}"
                skill_banner_time = 2.0
            if key == ord("q"):
                break
    finally:
        audio.shutdown()
        pose.close()
        hands.close()
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
