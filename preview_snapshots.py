from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game_assets import load_assets
from game_combat import draw_projectile_vfx, get_enemy_frame
from game_config import HEIGHT, LEVELS, SKILLS, WIDTH
from game_entities import Enemy, Projectile
from game_stage import get_stage_layout
from game_vfx import draw_effect, draw_player_aura


OUT_DIR = Path(__file__).parent / "previews_auto"


def _save(surface: pygame.Surface, filename: str) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / filename
    pygame.image.save(surface, str(path))
    return path


def _fit_blit(dst: pygame.Surface, src: pygame.Surface, rect: pygame.Rect):
    scale = min(rect.width / src.get_width(), rect.height / src.get_height())
    size = (max(1, int(src.get_width() * scale)), max(1, int(src.get_height() * scale)))
    scaled = pygame.transform.smoothscale(src, size)
    dst.blit(scaled, (rect.centerx - size[0] // 2, rect.centery - size[1] // 2))


def render_map_previews(assets: dict) -> list[Path]:
    paths = []
    font = pygame.font.SysFont("consolas", 28, bold=True)
    for idx, map_data in enumerate(assets.get("maps", [])[:3], start=1):
        canvas = pygame.Surface((960, 540))
        canvas.fill((8, 10, 14))
        _fit_blit(canvas, map_data["surface"], canvas.get_rect())
        scale = min(canvas.get_width() / map_data["surface"].get_width(), canvas.get_height() / map_data["surface"].get_height())
        offset = pygame.Vector2(
            (canvas.get_width() - map_data["surface"].get_width() * scale) * 0.5,
            (canvas.get_height() - map_data["surface"].get_height() * scale) * 0.5,
        )
        layout = get_stage_layout(idx - 1, map_data["width_px"], map_data["height_px"])
        def world_to_canvas(point):
            return pygame.Vector2(offset.x + point.x * scale, offset.y + point.y * scale)
        altar = world_to_canvas(layout["altar"])
        boss = world_to_canvas(layout["boss"])
        portal = world_to_canvas(layout["portal"])
        pygame.draw.circle(canvas, (255, 220, 110), altar, 10, 3)
        pygame.draw.circle(canvas, (255, 90, 80), boss, 18, 3)
        pygame.draw.circle(canvas, (120, 240, 255), portal, 14, 2)
        for spawn in layout["spawns"]:
            pygame.draw.circle(canvas, (160, 255, 170), world_to_canvas(spawn), 6, 0)
        label = font.render(f"Map {idx}: {map_data['name']}", True, (255, 245, 180))
        canvas.blit(label, (18, 16))
        paths.append(_save(canvas, f"map_{idx}.png"))
    return paths


def render_actor_preview(assets: dict) -> Path:
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small = pygame.font.SysFont("consolas", 14)
    canvas = pygame.Surface((1280, 720), pygame.SRCALPHA)
    canvas.fill((18, 22, 26, 255))
    canvas.blit(font.render("Actor Registry Preview", True, (255, 245, 180)), (24, 18))

    actor_entries = []
    for pool_idx, pool in enumerate(assets.get("map_enemy_pools", []), start=1):
        for actor in pool:
            actor_entries.append((f"M{pool_idx}", actor, False))
    for pool_idx, pool in enumerate(assets.get("map_boss_pools", []), start=1):
        for actor in pool:
            actor_entries.append((f"B{pool_idx}", actor, True))

    x, y = 38, 78
    cell_w, cell_h = 180, 150
    for label, actor, is_boss in actor_entries:
        enemy = Enemy((0, 0), 1, actor, is_boss)
        frame = get_enemy_frame(enemy)
        cell = pygame.Rect(x, y, cell_w, cell_h)
        pygame.draw.rect(canvas, (32, 36, 45), cell)
        pygame.draw.rect(canvas, (255, 190, 110) if is_boss else (120, 210, 255), cell, 2)
        fit = cell.inflate(-18, -42)
        _fit_blit(canvas, frame, fit)
        canvas.blit(small.render(f"{label} {actor.get('name', 'unknown')}", True, (220, 235, 245)), (x + 8, y + cell_h - 28))
        x += cell_w + 16
        if x + cell_w > canvas.get_width():
            x = 38
            y += cell_h + 18
    return _save(canvas, "actors_registry.png")


def render_skill_preview(assets: dict) -> Path:
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small = pygame.font.SysFont("consolas", 14)
    canvas = pygame.Surface((1280, 720), pygame.SRCALPHA)
    canvas.fill((10, 12, 18, 255))
    canvas.blit(font.render("Skill VFX Preview", True, (255, 245, 180)), (24, 18))
    camera = pygame.Vector2(0, 0)

    for skill_id, skill in enumerate(SKILLS, start=1):
        col = (skill_id - 1) % 4
        row = (skill_id - 1) // 4
        origin = pygame.Vector2(150 + col * 300, 170 + row * 250)
        pygame.draw.rect(canvas, (24, 28, 38), (origin.x - 105, origin.y - 100, 230, 190))
        pygame.draw.rect(canvas, (80, 130, 180), (origin.x - 105, origin.y - 100, 230, 190), 1)
        if skill_id == 5:
            array_radius = 120
            draw_effect(canvas, camera, assets, ["skill5_array", origin, 2.4, 3.0, array_radius, 72, 0.2, 0])
            strike_points = [origin.copy()]
            for point_idx in range(5):
                strike_points.append(origin + pygame.Vector2(1, 0).rotate(-90 + point_idx * 72) * array_radius * 0.62)
            for strike_pos in strike_points:
                draw_effect(canvas, camera, assets, ["black_lightning", strike_pos, 0.24, 0.28, 96])
        else:
            for offset in range(5):
                projectile = Projectile(origin - pygame.Vector2(offset * 34, 0), pygame.Vector2(620, 0), 10, 12, 0.5, skill[4], skill_id)
                draw_projectile_vfx(canvas, camera, assets, projectile)
        fx_groups = assets.get("skill_fx_anim", [])
        if skill_id <= len(fx_groups) and fx_groups[skill_id - 1]:
            fx = fx_groups[skill_id - 1][0]
            _fit_blit(canvas, fx, pygame.Rect(int(origin.x - 42), int(origin.y + 24), 84, 56))
        canvas.blit(small.render(f"{skill_id}. {skill[0]}", True, (230, 235, 245)), (origin.x - 96, origin.y - 88))
    return _save(canvas, "skills_vfx.png")


def render_boss_skill_preview(assets: dict) -> Path:
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small = pygame.font.SysFont("consolas", 14)
    canvas = pygame.Surface((1280, 720), pygame.SRCALPHA)
    canvas.fill((10, 12, 18, 255))
    canvas.blit(font.render("Boss Telegraph / Skill Preview", True, (255, 245, 180)), (24, 18))
    camera = pygame.Vector2(0, 0)
    boss_specs = [
        ("TenguRed", 91, pygame.Vector2(220, 330)),
        ("SquidGreen", 92, pygame.Vector2(640, 330)),
        ("DragonGreen", 93, pygame.Vector2(1040, 330)),
    ]
    for name, skill_id, center in boss_specs:
        pygame.draw.rect(canvas, (24, 28, 38), (center.x - 170, center.y - 190, 340, 360))
        pygame.draw.rect(canvas, (255, 190, 110), (center.x - 170, center.y - 190, 340, 360), 2)
        actor = None
        for pool in assets.get("map_boss_pools", []):
            for item in pool:
                if item.get("name") == name:
                    actor = item
                    break
            if actor is not None:
                break
        if actor is not None:
            enemy = Enemy(center, 1, actor, True)
            frame = get_enemy_frame(enemy)
            _fit_blit(canvas, frame, pygame.Rect(int(center.x - 80), int(center.y - 80), 160, 130))
        draw_effect(canvas, camera, assets, ["boss_telegraph", center, 0.56, 132, skill_id, name])
        for offset in (-36, 0, 36):
            projectile = Projectile(center + pygame.Vector2(0, offset), pygame.Vector2(520, 0), 12, 12, 0.8, (255, 240, 190), skill_id, True)
            draw_projectile_vfx(canvas, camera, assets, projectile)
        canvas.blit(small.render(name, True, (245, 235, 190)), (center.x - 58, center.y - 168))
    return _save(canvas, "boss_skills.png")


def render_aura_preview(assets: dict) -> Path:
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small = pygame.font.SysFont("consolas", 14)
    canvas = pygame.Surface((1280, 720), pygame.SRCALPHA)
    canvas.fill((10, 12, 18, 255))
    canvas.blit(font.render("Realm Aura / Breakthrough Preview", True, (255, 245, 180)), (24, 18))
    camera = pygame.Vector2(0, 0)
    hero_anim = assets.get("hero_anim", [])
    hero = hero_anim[0] if hero_anim else assets["hero"]
    for level_idx, realm in enumerate(LEVELS):
        col = level_idx % 4
        row = level_idx // 4
        center = pygame.Vector2(160 + col * 300, 190 + row * 260)
        pygame.draw.rect(canvas, (24, 28, 38), (center.x - 110, center.y - 112, 230, 210))
        pygame.draw.rect(canvas, (90, 150, 210), (center.x - 110, center.y - 112, 230, 210), 1)
        draw_player_aura(canvas, camera, assets, center, level_idx, level_idx >= 1, level_idx >= 4)
        canvas.blit(hero, (center.x - hero.get_width() // 2, center.y - hero.get_height() // 2))
        pygame.draw.circle(canvas, (80, 255, 225), center, 20, 2)
        canvas.blit(small.render(f"{level_idx + 1}. {realm}", True, (240, 235, 190)), (center.x - 94, center.y - 96))
    break_center = pygame.Vector2(1040, 520)
    draw_effect(canvas, camera, assets, ["break", break_center, 1.5, 300, 0, (255, 235, 130)])
    canvas.blit(small.render("Dot pha burst", True, (255, 245, 180)), (break_center.x - 58, break_center.y - 118))
    return _save(canvas, "realm_auras.png")


def main() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))
    assets = load_assets()
    paths = []
    paths.extend(render_map_previews(assets))
    paths.append(render_actor_preview(assets))
    paths.append(render_skill_preview(assets))
    paths.append(render_boss_skill_preview(assets))
    paths.append(render_aura_preview(assets))
    for path in paths:
        print(path)
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
