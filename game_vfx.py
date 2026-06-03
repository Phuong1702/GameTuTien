import math
import time

import pygame

from game_config import REALM_AURAS, SKILL_VFX
from game_utils import clamp


def tint_surface(assets: dict, surface: pygame.Surface, color) -> pygame.Surface:
    cache = assets.setdefault("_tint_cache", {})
    key = (id(surface), int(color[0]), int(color[1]), int(color[2]))
    cached = cache.get(key)
    if cached is not None:
        return cached
    tinted = surface.copy()
    tinted.fill((color[0], color[1], color[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
    cache[key] = tinted
    return tinted


def cached_rotozoom(assets: dict, surface: pygame.Surface, angle: float, scale: float) -> pygame.Surface:
    cache = assets.setdefault("_rotozoom_cache", {})
    angle_key = int(round(angle / 8.0) * 8) % 360
    scale_key = int(round(scale * 32.0))
    key = (id(surface), angle_key, scale_key)
    cached = cache.get(key)
    if cached is not None:
        return cached
    rendered = pygame.transform.rotozoom(surface, angle_key, max(0.05, scale_key / 32.0))
    if len(cache) > 700:
        cache.clear()
    cache[key] = rendered
    return rendered


def _blit_center(screen: pygame.Surface, surface: pygame.Surface, pos: pygame.Vector2):
    screen.blit(surface, (pos.x - surface.get_width() // 2, pos.y - surface.get_height() // 2))


def draw_player_aura(
    screen: pygame.Surface,
    camera: pygame.Vector2,
    assets: dict,
    pos: pygame.Vector2,
    level: int,
    clasp_on: bool = False,
    breakthrough_ready: bool = False,
):
    draw_pos = pos - camera
    level_idx = int(clamp(level, 0, len(REALM_AURAS) - 1))
    color = REALM_AURAS[level_idx]
    now = time.time()
    power = 1.0 + level_idx * 0.18
    pulse = 0.5 + 0.5 * math.sin(now * (3.0 + level_idx * 0.25))

    aura_size = 36 + level_idx * 7
    glow = pygame.Surface((aura_size * 4, aura_size * 4), pygame.SRCALPHA)
    center = (aura_size * 2, aura_size * 2)
    pygame.draw.circle(glow, (*color, int(24 + level_idx * 7)), center, aura_size * 2)
    pygame.draw.circle(glow, (*color, int(78 + pulse * 45)), center, aura_size + 6 + level_idx * 2, 2)
    if level_idx >= 2:
        pygame.draw.circle(glow, (255, 235, 150, int(55 + pulse * 55)), center, aura_size // 2, 2)
    screen.blit(glow, (draw_pos.x - aura_size * 2, draw_pos.y - aura_size * 2))

    ring_tex = tint_surface(assets, assets["fx_ring"], color)
    ring_scale = 0.34 + level_idx * 0.045 + pulse * 0.025
    _blit_center(screen, cached_rotozoom(assets, ring_tex, now * (38 + level_idx * 5), ring_scale), draw_pos)

    magic_tex = tint_surface(assets, assets["fx_magic"], color)
    magic = cached_rotozoom(assets, magic_tex, -now * (25 + level_idx * 6), 0.23 + level_idx * 0.035)
    magic.set_alpha(46 + level_idx * 10)
    _blit_center(screen, magic, draw_pos)

    if level_idx >= 1:
        lower = cached_rotozoom(assets, tint_surface(assets, assets["fx_magic_b"], color), now * 44, 0.18 + level_idx * 0.025)
        lower.set_alpha(74 + level_idx * 8)
        _blit_center(screen, lower, draw_pos + pygame.Vector2(0, 16))

    if level_idx >= 2:
        orbit_radius = 28 + level_idx * 4
        orbit_count = min(2 + level_idx, 7)
        for idx in range(orbit_count):
            angle = now * (62 + level_idx * 7) + idx * math.tau / orbit_count
            orb_pos = draw_pos + pygame.Vector2(math.cos(angle), math.sin(angle)) * orbit_radius
            orb = cached_rotozoom(assets, tint_surface(assets, assets["fx_flare"], (255, 235, 155)), 0, 0.11 + level_idx * 0.008)
            orb.set_alpha(130 + int(pulse * 60))
            _blit_center(screen, orb, orb_pos)

    if level_idx >= 3:
        spirit = cached_rotozoom(assets, tint_surface(assets, assets["fx_twirl"], color), -now * 36, 0.28 + level_idx * 0.02)
        spirit.set_alpha(45 + level_idx * 8)
        _blit_center(screen, spirit, draw_pos + pygame.Vector2(0, -20 - level_idx * 2))

    if level_idx >= 5:
        for idx in range(3):
            angle = now * 72 + idx * 120
            slash_pos = draw_pos + pygame.Vector2(1, 0).rotate(angle) * (42 + level_idx * 4)
            slash = cached_rotozoom(assets, tint_surface(assets, assets["fx_slash"], color), angle + 90, 0.18 + level_idx * 0.018)
            slash.set_alpha(72 + int(pulse * 55))
            _blit_center(screen, slash, slash_pos)

    if level_idx >= 6:
        yin = cached_rotozoom(assets, tint_surface(assets, assets["fxb_twirl3"], (230, 230, 245)), now * 32, 0.32)
        yang = cached_rotozoom(assets, tint_surface(assets, assets["fxb_ring"], (45, 35, 60)), -now * 44, 0.42)
        yin.set_alpha(105)
        yang.set_alpha(92)
        _blit_center(screen, yang, draw_pos)
        _blit_center(screen, yin, draw_pos)

    if clasp_on:
        clasp_tex = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], (255, 245, 180)), -now * 80, 0.52 + min(0.25, level_idx * 0.025))
        clasp_tex.set_alpha(145)
        _blit_center(screen, clasp_tex, draw_pos)

    if breakthrough_ready:
        ready_radius = 58 + int(8 * math.sin(now * 8.5))
        ready = pygame.Surface((ready_radius * 4, ready_radius * 4), pygame.SRCALPHA)
        ready_center = (ready_radius * 2, ready_radius * 2)
        pygame.draw.circle(ready, (255, 220, 120, 44), ready_center, ready_radius * 2)
        pygame.draw.circle(ready, (255, 245, 180, 150), ready_center, ready_radius, 4)
        pygame.draw.circle(ready, (120, 255, 190, 135), ready_center, max(12, ready_radius - 18), 2)
        screen.blit(ready, (draw_pos.x - ready_radius * 2, draw_pos.y - ready_radius * 2))


def draw_effect(screen: pygame.Surface, camera: pygame.Vector2, assets: dict, effect: list):
    kind = effect[0]
    if kind in ("break", "hit", "enemy_attack"):
        _, pos, life, radius, damage, color = effect
        if kind == "break":
            progress = clamp(life / 1.8, 0.0, 1.0)
            draw_pos = pos - camera
            now = time.time()
            shock_radius = radius * (1.25 - progress * 0.45)
            screen_flash = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            screen_flash.fill((255, 245, 185, int(42 * progress)))
            screen.blit(screen_flash, (0, 0))
            for scale_mul, alpha in ((2.8, 115), (2.1, 150), (1.35, 190)):
                ring = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], color), now * (120 / scale_mul), max(0.35, shock_radius / max(1, assets["fx_ring"].get_width()) * scale_mul))
                ring.set_alpha(int(alpha * progress))
                _blit_center(screen, ring, draw_pos)
            magic = cached_rotozoom(assets, tint_surface(assets, assets["fx_magic"], color), -now * 95, max(0.5, radius / max(1, assets["fx_magic"].get_width()) * 2.4))
            magic.set_alpha(int(210 * progress))
            _blit_center(screen, magic, draw_pos)
            twirl = cached_rotozoom(assets, tint_surface(assets, assets["fx_twirl"], (255, 255, 235)), now * 170, max(0.4, radius / max(1, assets["fx_twirl"].get_width()) * 1.65))
            twirl.set_alpha(int(150 * progress))
            _blit_center(screen, twirl, draw_pos)
            for idx in range(10):
                angle = now * 85 + idx * 36
                particle_pos = draw_pos + pygame.Vector2(1, 0).rotate(angle) * (42 + idx * 8 + (1.0 - progress) * 55)
                spark = cached_rotozoom(assets, tint_surface(assets, assets["fx_flare"], color), angle, 0.13 + idx * 0.006)
                spark.set_alpha(int(150 * progress))
                _blit_center(screen, spark, particle_pos)
            return
        tex = tint_surface(assets, assets["fx_slash"] if kind == "enemy_attack" else assets["fx_spark"], color)
        scale = max(0.3, radius / max(1, tex.get_width()) * 1.9)
        burst = cached_rotozoom(assets, tex, time.time() * 180, scale)
        burst.set_alpha(int(205 * clamp(life, 0.0, 1.0)))
        _blit_center(screen, burst, pos - camera)
        ring = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], color), -time.time() * 120, max(0.35, radius / 110.0))
        ring.set_alpha(int(130 * clamp(life, 0.0, 1.0)))
        _blit_center(screen, ring, pos - camera)
    elif kind == "boss_telegraph":
        _, pos, life, radius, boss_skill, boss_name = effect
        color = (255, 185, 110) if boss_skill == 91 else ((115, 255, 210) if boss_skill == 92 else (150, 235, 255))
        tex = tint_surface(assets, assets["fx_slash"] if boss_skill == 91 else (assets["fx_magic_b"] if boss_skill == 92 else assets["fx_spark"]), color)
        pulse = 1.0 + 0.12 * math.sin(time.time() * 18.0)
        aura = cached_rotozoom(assets, tex, time.time() * (90 if boss_skill != 91 else -140), max(0.5, radius / max(1, tex.get_width()) * 2.4) * pulse)
        aura.set_alpha(int(145 * clamp(life / 0.56, 0.0, 1.0)))
        screen.blit(aura, (pos.x - camera.x - aura.get_width() // 2, pos.y - camera.y - aura.get_height() // 2))
        warn = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], color), -time.time() * 160, max(0.45, radius / 120.0))
        warn.set_alpha(int(180 * clamp(life / 0.56, 0.0, 1.0)))
        screen.blit(warn, (pos.x - camera.x - warn.get_width() // 2, pos.y - camera.y - warn.get_height() // 2))
    elif kind == "skillfx":
        _, pos, life, skill_id = effect
        fx_groups = assets.get("skill_fx_anim", [])
        fx_idx = int(clamp(skill_id - 1, 0, len(fx_groups) - 1))
        if fx_groups and fx_groups[fx_idx]:
            frame_idx = int((0.45 - life) * 14) % len(fx_groups[fx_idx])
            fx = fx_groups[fx_idx][frame_idx].copy()
            fx.set_alpha(int(220 * clamp(life / 0.45, 0.2, 1.0)))
            screen.blit(fx, (pos.x - camera.x - fx.get_width() // 2, pos.y - camera.y - fx.get_height() // 2))
        data = SKILL_VFX.get(skill_id, SKILL_VFX[0])
        cast_tex = tint_surface(assets, assets[data["cast_tex"]], data["trail"])
        pulse = cached_rotozoom(assets, cast_tex, time.time() * (120 + skill_id * 18), data["scale"] * (1.2 + (1.0 - life) * 0.45))
        pulse.set_alpha(int(185 * clamp(life / 0.45, 0.25, 1.0)))
        screen.blit(pulse, (pos.x - camera.x - pulse.get_width() // 2, pos.y - camera.y - pulse.get_height() // 2))
    elif kind == "skill5_array":
        _, pos, life, max_life, radius, damage, timer = effect[:7]
        progress = clamp(life / max_life, 0.0, 1.0)
        core_color = (80, 20, 110)
        ring_color = (235, 180, 255)
        base = tint_surface(assets, assets["fxb_magic2"], ring_color)
        array = cached_rotozoom(assets, base, time.time() * 45, max(0.7, radius / max(1, base.get_width()) * 2.15))
        array.set_alpha(int(185 * progress))
        screen.blit(array, (pos.x - camera.x - array.get_width() // 2, pos.y - camera.y - array.get_height() // 2))
        twirl = cached_rotozoom(assets, tint_surface(assets, assets["fxb_twirl3"], core_color), -time.time() * 70, max(0.55, radius / max(1, assets["fxb_twirl3"].get_width()) * 1.65))
        twirl.set_alpha(int(135 * progress))
        screen.blit(twirl, (pos.x - camera.x - twirl.get_width() // 2, pos.y - camera.y - twirl.get_height() // 2))
        outer = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], ring_color), time.time() * 95, max(0.6, radius / max(1, assets["fx_ring"].get_width()) * 2.5))
        outer.set_alpha(int(170 * progress))
        screen.blit(outer, (pos.x - camera.x - outer.get_width() // 2, pos.y - camera.y - outer.get_height() // 2))
    elif kind == "black_lightning":
        _, pos, life, max_life, radius = effect
        progress = clamp(life / max_life, 0.0, 1.0)
        draw_pos = pos - camera

        top_y = draw_pos.y - radius * 1.85
        bottom_y = draw_pos.y + 6
        segments = 7
        phase = time.time() * 31.0 + pos.x * 0.017 + pos.y * 0.011
        points = []
        for idx in range(segments + 1):
            t = idx / segments
            wobble = math.sin(phase + idx * 1.73) * (10 + 8 * (1.0 - progress))
            if idx in (0, segments):
                wobble = 0.0
            points.append((int(draw_pos.x + wobble), int(top_y + (bottom_y - top_y) * t)))

        alpha = int(235 * progress)
        wide_color = (42, 10, 65, alpha)
        core_color = (210, 180, 255, alpha)
        hot_color = (250, 245, 255, min(255, alpha + 20))
        if len(points) >= 2:
            pygame.draw.lines(screen, wide_color, False, points, 9)
            pygame.draw.lines(screen, core_color, False, points, 4)
            pygame.draw.lines(screen, hot_color, False, points, 2)

        for offset in (-14, 16):
            side_points = []
            for idx, point in enumerate(points):
                if idx in (0, len(points) - 1):
                    side_points.append((point[0], point[1]))
                else:
                    side_points.append((int(point[0] + offset * math.sin(phase + idx)), point[1]))
            pygame.draw.lines(screen, (70, 22, 105, int(105 * progress)), False, side_points, 2)

        flash = cached_rotozoom(assets, tint_surface(assets, assets["fx_ring"], (210, 165, 255)), time.time() * 120, 0.42 + (1.0 - progress) * 0.18)
        flash.set_alpha(int(160 * progress))
        screen.blit(flash, (draw_pos.x - flash.get_width() // 2, draw_pos.y - flash.get_height() // 2))
        impact = cached_rotozoom(assets, tint_surface(assets, assets["fx_spark"], (120, 45, 180)), -time.time() * 160, 0.36 + (1.0 - progress) * 0.25)
        impact.set_alpha(int(155 * progress))
        screen.blit(impact, (draw_pos.x - impact.get_width() // 2, draw_pos.y - impact.get_height() // 2))
    elif kind == "chain_lightning":
        _, start, end, life, max_life, color = effect
        progress = clamp(life / max_life, 0.0, 1.0)
        start_pos = start - camera
        end_pos = end - camera
        direction = end_pos - start_pos
        if direction.length() <= 0.001:
            return
        side = pygame.Vector2(-direction.y, direction.x).normalize()
        phase = time.time() * 40.0 + start.x * 0.013 + end.y * 0.017
        points = []
        segments = 9
        for idx in range(segments + 1):
            ratio = idx / segments
            base = start_pos.lerp(end_pos, ratio)
            jitter = math.sin(phase + idx * 1.83) * 13 * (1.0 - abs(ratio - 0.5) * 0.85)
            if idx in (0, segments):
                jitter = 0.0
            points.append((base.x + side.x * jitter, base.y + side.y * jitter))
        wide = (55, 35, 115, int(95 * progress))
        mid = (color[0], color[1], color[2], int(185 * progress))
        core = (245, 238, 255, int(245 * progress))
        pygame.draw.lines(screen, wide, False, points, 12)
        pygame.draw.lines(screen, mid, False, points, 6)
        pygame.draw.lines(screen, core, False, points, 2)
        for point in (start_pos, end_pos):
            flare = cached_rotozoom(assets, tint_surface(assets, assets["fx_flare"], color), time.time() * 120, 0.28 + (1.0 - progress) * 0.12)
            flare.set_alpha(int(190 * progress))
            _blit_center(screen, flare, point)
        impact = cached_rotozoom(assets, tint_surface(assets, assets["fx_spark"], color), -time.time() * 180, 0.34)
        impact.set_alpha(int(175 * progress))
        _blit_center(screen, impact, end_pos)
