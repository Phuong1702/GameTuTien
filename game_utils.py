import math
import random
import wave
from pathlib import Path

import pygame

from game_config import *

def clamp(value, low, high):
    return max(low, min(high, value))


def draw_ui_panel(screen: pygame.Surface, rect: pygame.Rect, assets: dict, border_color=(120, 180, 255), alpha=220):
    panel_tex = assets.get("ui_panel")
    inner_tex = assets.get("ui_panel_inner")
    if panel_tex is not None and inner_tex is not None:
        bg = pygame.transform.smoothscale(inner_tex, (rect.width, rect.height))
        bg.set_alpha(alpha)
        screen.blit(bg, rect.topleft)
        frame = pygame.transform.smoothscale(panel_tex, (rect.width, rect.height))
        frame.set_alpha(alpha)
        screen.blit(frame, rect.topleft)
    else:
        fallback = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        fallback.fill((8, 10, 18, alpha))
        screen.blit(fallback, rect.topleft)
    pygame.draw.rect(screen, border_color, rect, 2)


def norm(vec):
    length = math.hypot(vec[0], vec[1])
    if length <= 0.001:
        return pygame.Vector2()
    return pygame.Vector2(vec[0] / length, vec[1] / length)


def create_tone(path: Path, tones, seconds=0.4, volume=0.7, sweep=0.0, sample_rate=44100):
    total = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total):
            t = i / sample_rate
            k = i / max(1, total - 1)
            env = math.sin(math.pi * k) ** 0.4
            val = 0.0
            for freq in tones:
                val += math.sin(math.tau * (freq + sweep * k) * t) / len(tones)
            val += random.uniform(-1, 1) * 0.04 * (1.0 - k)
            frames.extend(int(clamp(val * env * volume, -1, 1) * 32767).to_bytes(2, "little", signed=True))
        wav.writeframes(frames)


