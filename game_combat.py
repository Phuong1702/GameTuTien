import math
import random
import time

import pygame

from game_config import SKILL_VFX
from game_entities import Enemy, Projectile
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


def get_projectile_vfx_assets(assets: dict, projectile: Projectile):
    if projectile.hostile:
        if projectile.skill == 91:
            return assets["fx_slash"], assets["fx_trace_b"], 0.55
        if projectile.skill == 92:
            return assets["fx_spark"], assets["fx_trace_a"], 0.60
        if projectile.skill == 93:
            return assets["fx_magic"], assets["fx_trace_b"], 0.70
        return assets["fx_star"], assets["fx_trace_a"], 0.45
    data = SKILL_VFX.get(projectile.skill, SKILL_VFX[0])
    return assets[data["proj_tex"]], assets[data["trail_tex"]], data["scale"]


def draw_projectile_vfx(screen: pygame.Surface, camera: pygame.Vector2, assets: dict, projectile: Projectile):
    pos = projectile.pos - camera
    speed = projectile.vel.length()
    direction = projectile.vel.normalize() if speed > 0.001 else pygame.Vector2(1, 0)
    angle = math.degrees(math.atan2(direction.y, direction.x))

    if not projectile.hostile and projectile.skill == 1:
        side = pygame.Vector2(-direction.y, direction.x)
        phase = time.time() * 12.0 + projectile.pos.x * 0.01
        core_color = (255, 246, 185)
        aura_color = (105, 245, 255)
        trail_color = (80, 210, 255)

        for idx, offset in enumerate((96, 68, 42, 20)):
            trail_pos = pos - direction * offset + side * math.sin(phase + idx * 1.4) * (4 + idx)
            trail_tex = tint_surface(assets, assets["fx_trace_a"], trail_color)
            trail = cached_rotozoom(assets, trail_tex, angle, 0.34 + idx * 0.035)
            trail.set_alpha(42 + idx * 22)
            screen.blit(trail, (trail_pos.x - trail.get_width() // 2, trail_pos.y - trail.get_height() // 2))

        ring_tex = tint_surface(assets, assets["fx_ring"], aura_color)
        for spin, scale, alpha in ((phase * 38, 0.42, 150), (-phase * 52, 0.30, 120)):
            ring = cached_rotozoom(assets, ring_tex, spin, scale)
            ring.set_alpha(alpha)
            screen.blit(ring, (pos.x - ring.get_width() // 2, pos.y - ring.get_height() // 2))

        twirl_tex = tint_surface(assets, assets["fx_twirl"], (120, 255, 235))
        twirl = cached_rotozoom(assets, twirl_tex, -phase * 45, 0.34)
        twirl.set_alpha(125)
        screen.blit(twirl, (pos.x - twirl.get_width() // 2, pos.y - twirl.get_height() // 2))

        core_tex = tint_surface(assets, assets["fx_magic_b"], core_color)
        core = cached_rotozoom(assets, core_tex, phase * 90, 0.38)
        core.set_alpha(235)
        screen.blit(core, (pos.x - core.get_width() // 2, pos.y - core.get_height() // 2))

        pearl = cached_rotozoom(assets, tint_surface(assets, assets["fx_flare"], (255, 255, 220)), 0, 0.22)
        pearl.set_alpha(245)
        screen.blit(pearl, (pos.x - pearl.get_width() // 2, pos.y - pearl.get_height() // 2))
        return

    if not projectile.hostile and projectile.skill == 4:
        side = pygame.Vector2(-direction.y, direction.x)
        phase = time.time() * 34.0 + projectile.pos.x * 0.015 + projectile.pos.y * 0.011
        bolt_color = (118, 82, 185)
        core_color = (232, 225, 255)
        glow_color = (74, 44, 118)
        start = pos - direction * 118
        end = pos + direction * 42

        for layer, width, alpha, jitter_scale in ((0, 16, 58, 1.55), (1, 8, 125, 1.05), (2, 3, 245, 0.55)):
            points = []
            for idx in range(10):
                ratio = idx / 9.0
                base = start.lerp(end, ratio)
                jitter = math.sin(phase + idx * 1.91 + layer * 2.7) * (13 - layer * 3.4) * jitter_scale
                points.append((base.x + side.x * jitter, base.y + side.y * jitter))
            color = glow_color if layer == 0 else (bolt_color if layer == 1 else core_color)
            if len(points) >= 2:
                pygame.draw.lines(screen, (*color, alpha), False, points, width)

        for offset_idx, offset in enumerate((-86, -52, -18, 18, 42)):
            spark_pos = pos + direction * offset + side * math.sin(phase + offset_idx) * 12
            spark_tex = tint_surface(assets, assets["fx_spark"], core_color if offset_idx % 2 else bolt_color)
            spark = cached_rotozoom(assets, spark_tex, angle + 90 + offset_idx * 23, 0.30 + offset_idx * 0.028)
            spark.set_alpha(120 + offset_idx * 24)
            screen.blit(spark, (spark_pos.x - spark.get_width() // 2, spark_pos.y - spark.get_height() // 2))

        head_tex = tint_surface(assets, assets["fx_flare"], (215, 205, 255))
        head = cached_rotozoom(assets, head_tex, angle, 0.52)
        head.set_alpha(225)
        screen.blit(head, (pos.x - head.get_width() // 2, pos.y - head.get_height() // 2))
        return

    head_tex, trail_tex, base_scale = get_projectile_vfx_assets(assets, projectile)
    head_tex = tint_surface(assets, head_tex, projectile.color)
    trail_tex = tint_surface(assets, trail_tex, projectile.color)
    speed_scale = clamp(speed / 700.0, 0.65, 1.25)
    scale = base_scale * speed_scale

    trail_len = 28 + int(clamp(speed / 18.0, 10, 42))
    trail_pos = pos - direction * trail_len * 0.5
    trail = cached_rotozoom(assets, trail_tex, angle, max(0.3, scale * 0.92))
    trail.set_alpha(165 if projectile.hostile else 145)
    screen.blit(trail, (trail_pos.x - trail.get_width() // 2, trail_pos.y - trail.get_height() // 2))

    aura_tex = tint_surface(assets, assets["fx_smoke"] if projectile.hostile else assets["fx_flare"], projectile.color)
    aura = cached_rotozoom(assets, aura_tex, angle, max(0.34, scale * 0.9))
    aura.set_alpha(120 if projectile.hostile else 105)
    screen.blit(aura, (pos.x - aura.get_width() // 2, pos.y - aura.get_height() // 2))

    core = cached_rotozoom(assets, head_tex, angle, max(0.32, scale))
    core.set_alpha(235)
    screen.blit(core, (pos.x - core.get_width() // 2, pos.y - core.get_height() // 2))


def spawn_boss_skill(enemy: Enemy, player: pygame.Vector2, wave: int, projectiles: list[Projectile], effects: list, sounds: dict, mode="active"):
    if not enemy.is_boss:
        return
    boss_name = enemy.name
    to_player = player - enemy.pos
    if to_player.length() <= 0.001:
        return
    base_dir = to_player.normalize()
    hp_ratio = enemy.hp / max(1, enemy.max_hp)
    passive = mode == "passive"
    side_dir = pygame.Vector2(-base_dir.y, base_dir.x)
    telegraph_skill = {"TenguRed": 91, "SquidGreen": 92, "DragonGreen": 93}.get(boss_name, 90)
    telegraph_radius = 104 if passive else 132
    effects.append(["boss_telegraph", enemy.pos.copy(), 0.42 if passive else 0.56, telegraph_radius, telegraph_skill, enemy.name])

    if boss_name == "TenguRed":
        roll = random.random()
        if roll < 0.45:
            if hp_ratio > 0.5:
                spreads = (-0.32, 0.0, 0.32) if not passive else (-0.24, 0.0, 0.24, 0.48)
                for spread in spreads:
                    vec = base_dir.rotate_rad(spread)
                    speed = 520 if not passive else 540
                    damage = (16 + wave * 0.9) if not passive else (13 + wave * 0.7)
                    projectiles.append(Projectile(enemy.pos, vec * speed, damage, 13, 0.95, (255, 210, 170), 91, True))
            else:
                spreads = (-0.48, -0.24, 0.0, 0.24, 0.48) if not passive else (-0.62, -0.31, 0.0, 0.31, 0.62)
                for spread in spreads:
                    vec = base_dir.rotate_rad(spread)
                    speed = 560 if not passive else 590
                    damage = (18 + wave * 1.0) if not passive else (15 + wave * 0.8)
                    projectiles.append(Projectile(enemy.pos, vec * speed, damage, 14, 1.00, (255, 200, 150), 91, True))
        elif roll < 0.78:
            # Cross slash pattern
            for angle in (0, 90, 180, 270):
                vec = base_dir.rotate(angle)
                projectiles.append(Projectile(enemy.pos, vec * (620 if hp_ratio <= 0.5 else 560), 14 + wave * 0.8, 11, 0.75, (255, 210, 170), 91, True))
        else:
            # Trap bloom around player
            for ring in (52, 92):
                steps = 6 if ring == 52 else 8
                for i in range(steps):
                    vec = pygame.Vector2(1, 0).rotate(i * (360.0 / steps))
                    trap_pos = player + vec * ring
                    projectiles.append(Projectile(trap_pos, pygame.Vector2(), 12 + wave * 0.6, 16, 1.0, (255, 190, 150), 91, True))
        effects.append(["enemy_attack", enemy.pos.copy(), 0.26, 84, 0, (255, 170, 130)])
    elif boss_name == "SquidGreen":
        roll = random.random()
        if roll < 0.4:
            if hp_ratio > 0.5:
                step = 45 if not passive else 60
                for angle in range(0, 360, step):
                    vec = pygame.Vector2(1, 0).rotate(angle)
                    speed = 360 if not passive else 400
                    damage = (14 + wave * 0.75) if not passive else (12 + wave * 0.6)
                    projectiles.append(Projectile(enemy.pos, vec * speed, damage, 12, 1.1, (165, 255, 220), 92, True))
            else:
                ring_speeds = (380, 460) if not passive else (420,)
                for ring_speed in ring_speeds:
                    for angle in range(0, 360, 30):
                        vec = pygame.Vector2(1, 0).rotate(angle + (12 if ring_speed > 400 else 0))
                        damage = (15 + wave * 0.8) if not passive else (13 + wave * 0.65)
                        projectiles.append(Projectile(enemy.pos, vec * ring_speed, damage, 11, 1.15, (140, 250, 215), 92, True))
        elif roll < 0.75:
            # Spiral drill: offset launch angles and mixed speeds
            for k in range(12):
                angle = k * 30 + (time.time() * 90 % 360)
                vec = pygame.Vector2(1, 0).rotate(angle)
                speed = 280 + (k % 4) * 70
                projectiles.append(Projectile(enemy.pos, vec * speed, 13 + wave * 0.7, 10, 1.2, (145, 255, 225), 92, True))
        else:
            # Mine field: stationary bubbles around player
            for i in range(10 if hp_ratio <= 0.5 else 7):
                angle = i * (360.0 / (10 if hp_ratio <= 0.5 else 7))
                vec = pygame.Vector2(1, 0).rotate(angle)
                trap_pos = player + vec * (72 + (i % 3) * 26)
                projectiles.append(Projectile(trap_pos, pygame.Vector2(), 11 + wave * 0.55, 15, 1.35, (130, 245, 210), 92, True))
        effects.append(["enemy_attack", enemy.pos.copy(), 0.30, 90, 0, (110, 245, 210)])
    elif boss_name == "DragonGreen":
        roll = random.random()
        if roll < 0.42:
            if hp_ratio > 0.5:
                spreads = (-0.22, -0.11, 0.0, 0.11, 0.22) if not passive else (-0.18, 0.0, 0.18)
                for spread in spreads:
                    vec = base_dir.rotate_rad(spread)
                    speed = 610 if not passive else 650
                    damage = (18 + wave * 1.1) if not passive else (15 + wave * 0.85)
                    projectiles.append(Projectile(enemy.pos, vec * speed, damage, 14, 1.0, (145, 245, 255), 93, True))
            else:
                spreads = (-0.38, -0.25, -0.12, 0.0, 0.12, 0.25, 0.38) if not passive else (-0.28, -0.14, 0.0, 0.14, 0.28)
                for spread in spreads:
                    vec = base_dir.rotate_rad(spread)
                    damage = (21 + wave * 1.2) if not passive else (17 + wave * 0.95)
                    speed = 680 if not passive else 700
                    projectiles.append(Projectile(enemy.pos, vec * speed, damage, 15, 1.05, (155, 245, 255), 93, True))
                side_shots = 2 if not passive else 1
                for side in (-90, 90)[:side_shots]:
                    vec = base_dir.rotate(side)
                    damage = (16 + wave * 0.9) if not passive else (13 + wave * 0.7)
                    projectiles.append(Projectile(enemy.pos, vec * 420, damage, 12, 0.85, (185, 255, 255), 93, True))
        elif roll < 0.74:
            # Sweep wall: line of projectiles sliding toward player direction
            lane_count = 7 if hp_ratio > 0.5 else 11
            spacing = 36
            for i in range(lane_count):
                offset = (i - (lane_count - 1) * 0.5) * spacing
                spawn_pos = enemy.pos + side_dir * offset
                vel = base_dir * (520 if hp_ratio > 0.5 else 600)
                projectiles.append(Projectile(spawn_pos, vel, 15 + wave * 0.85, 11, 1.05, (170, 250, 255), 93, True))
        else:
            # Orbit stars around player then collapse
            nodes = 8 if hp_ratio > 0.5 else 12
            radius = 128 if hp_ratio > 0.5 else 166
            for i in range(nodes):
                angle = i * (360.0 / nodes)
                vec = pygame.Vector2(1, 0).rotate(angle)
                start_pos = player + vec * radius
                vel = (player - start_pos).normalize() * (280 if hp_ratio > 0.5 else 360)
                projectiles.append(Projectile(start_pos, vel, 14 + wave * 0.75, 12, 1.15, (200, 255, 255), 93, True))
        effects.append(["enemy_attack", enemy.pos.copy(), 0.34, 102, 0, (170, 245, 255)])
    else:
        projectiles.append(Projectile(enemy.pos, base_dir * 420, 14 + wave * 0.8, 12, 0.85, (255, 200, 165), 90, True))

    if "skill4" in sounds:
        sounds["skill4"].play()


def get_enemy_frame(enemy: Enemy):
    if enemy.anim_states:
        frames = enemy.anim_states.get(enemy.state, [])
        if not frames:
            frames = enemy.anim_states.get("walk", []) or enemy.anim_states.get("idle", [])
        if frames:
            return frames[int(enemy.anim_timer) % len(frames)]
    if enemy.anim_frames:
        return enemy.anim_frames[int(enemy.anim_timer) % len(enemy.anim_frames)]
    return enemy.sprite


def spawn_enemy(player, wave, assets, arena_w, arena_h, walkable_points=None, boss=False, map_idx=0, preferred_points=None):
    if preferred_points:
        far_points = [point for point in preferred_points if point.distance_to(player) > 180]
        pool = far_points if far_points else preferred_points
        pos_v = random.choice(pool)
        pos = (pos_v.x, pos_v.y)
    elif walkable_points:
        far_points = [point for point in walkable_points if point.distance_to(player) > 280]
        pool = far_points if far_points else walkable_points
        pos_v = random.choice(pool)
        pos = (pos_v.x, pos_v.y)
    else:
        side = random.randint(0, 3)
        if side == 0:
            pos = (random.randint(40, int(arena_w) - 40), 40)
        elif side == 1:
            pos = (int(arena_w) - 40, random.randint(40, int(arena_h) - 40))
        elif side == 2:
            pos = (random.randint(40, int(arena_w) - 40), int(arena_h) - 40)
        else:
            pos = (40, random.randint(40, int(arena_h) - 40))
    map_enemy_pools = assets.get("map_enemy_pools", [])
    map_boss_pools = assets.get("map_boss_pools", [])
    if boss and map_boss_pools:
        pool = map_boss_pools[map_idx % len(map_boss_pools)]
        if pool:
            sprite = random.choice(pool)
        elif assets.get("boss_anims"):
            sprite = random.choice(assets["boss_anims"])
        else:
            sprite = random.choice(assets["bosses"])
    elif (not boss) and map_enemy_pools:
        pool = map_enemy_pools[map_idx % len(map_enemy_pools)]
        if pool:
            sprite = random.choice(pool)
        elif assets.get("enemy_anims"):
            sprite = random.choice(assets["enemy_anims"])
        else:
            sprite = random.choice(assets["enemies"])
    elif boss and assets.get("boss_anims"):
        sprite = random.choice(assets["boss_anims"])
    elif (not boss) and assets.get("enemy_anims"):
        sprite = random.choice(assets["enemy_anims"])
    else:
        sprite = random.choice(assets["bosses"] if boss else assets["enemies"])
    return Enemy(pos, wave, sprite, boss)


