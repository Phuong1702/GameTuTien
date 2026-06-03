from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Iterable

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import asset_registry
import game_2d
from game_stage import get_stage_layout
from game_vfx import draw_effect, draw_player_aura


@dataclass
class CheckResult:
    ok: bool
    name: str
    detail: str


def _alpha_metrics(surface: pygame.Surface) -> tuple[float, tuple[int, int, int, int] | None]:
    mask = pygame.mask.from_surface(surface)
    if mask.count() <= 0:
        return 0.0, None
    bbox = mask.get_bounding_rects()[0]
    bbox_area = max(1, bbox.width * bbox.height)
    ratio = float(mask.count()) / float(bbox_area)
    return ratio, (bbox.x, bbox.y, bbox.width, bbox.height)


def check_maps(assets: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    maps = assets.get("maps", [])
    if len(maps) < 3:
        results.append(CheckResult(False, "maps.count", f"expected >=3, got {len(maps)}"))
        return results
    for idx, map_data in enumerate(maps[:3], start=1):
        w = int(map_data.get("width_px", 0))
        h = int(map_data.get("height_px", 0))
        walk = map_data.get("walkable", [])
        ok = w >= game_2d.WIDTH and h >= game_2d.HEIGHT and len(walk) > 100
        results.append(CheckResult(ok, f"maps.map{idx}", f"{w}x{h}, walkable={len(walk)}"))
    return results


def _iter_actor_pools(assets: dict) -> Iterable[tuple[str, dict]]:
    for pool_idx, pool in enumerate(assets.get("map_enemy_pools", []), start=1):
        for actor in pool:
            yield f"enemy_pool_{pool_idx}", actor
    for pool_idx, pool in enumerate(assets.get("map_boss_pools", []), start=1):
        for actor in pool:
            yield f"boss_pool_{pool_idx}", actor


def check_actor_frames(assets: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    for pool_name, actor in _iter_actor_pools(assets):
        actor_name = actor.get("name", "unknown")
        states = actor.get("states", {})
        idle_frames = states.get("idle", [])
        if not idle_frames:
            results.append(CheckResult(False, f"actor.{actor_name}.idle", f"{pool_name}: no idle frames"))
            continue

        frame = idle_frames[0]
        fw, fh = frame.get_size()
        size_ok = 24 <= fw <= 360 and 24 <= fh <= 360
        results.append(CheckResult(size_ok, f"actor.{actor_name}.size", f"{pool_name}: {fw}x{fh}"))

        # Detect opaque rectangular preview-like artifacts.
        alpha_ratio, bbox = _alpha_metrics(frame)
        ratio_ok = alpha_ratio <= 0.88
        results.append(CheckResult(ratio_ok, f"actor.{actor_name}.alpha", f"{pool_name}: ratio={alpha_ratio:.3f}, bbox={bbox}"))

        # Frame-to-frame center jitter check for idle animation.
        centers: list[tuple[float, float]] = []
        for sample in idle_frames[: min(8, len(idle_frames))]:
            _, sample_bbox = _alpha_metrics(sample)
            if sample_bbox is None:
                continue
            x, y, w, h = sample_bbox
            centers.append((x + w * 0.5, y + h * 0.5))
        if len(centers) >= 2:
            base_x, base_y = centers[0]
            max_shift = max(math.hypot(x - base_x, y - base_y) for x, y in centers[1:])
            jitter_ok = max_shift <= 18.0
            results.append(CheckResult(jitter_ok, f"actor.{actor_name}.jitter", f"{pool_name}: max_shift={max_shift:.2f}px"))
    return results


def check_boss_contract(assets: dict) -> list[CheckResult]:
    expected = [item["name"] for item in asset_registry.BOSS_BY_MAP]
    pools = assets.get("map_boss_pools", [])
    results: list[CheckResult] = []
    for idx, name in enumerate(expected):
        if idx >= len(pools) or not pools[idx]:
            results.append(CheckResult(False, f"boss.map{idx+1}", "missing pool"))
            continue
        got = pools[idx][0].get("name", "")
        results.append(CheckResult(got == name, f"boss.map{idx+1}", f"expected={name}, got={got}"))
    return results


def check_registry_contract(assets: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    map_names = [map_data.get("name", "") for map_data in assets.get("maps", [])[: len(asset_registry.MAP_FILES)]]
    expected_map_names = [item["name"] for item in asset_registry.MAP_FILES]
    results.append(CheckResult(map_names == expected_map_names, "registry.maps", f"expected={expected_map_names}, got={map_names}"))

    excluded = asset_registry.EXCLUDED_MOB_ACTORS
    loaded_names = []
    for pool in assets.get("map_enemy_pools", []):
        loaded_names.extend(actor.get("name", "") for actor in pool)
    leaked = sorted(name for name in loaded_names if name in excluded)
    results.append(CheckResult(not leaked, "registry.excluded_mobs", f"leaked={leaked}"))

    icon_count = len([icon for icon in assets.get("ui_skill_icons", []) if icon is not None])
    results.append(CheckResult(icon_count >= 5, "registry.skill_icons", f"loaded={icon_count}"))

    particle_missing = [key for key in asset_registry.PARTICLE_TEXTURES if key not in assets]
    results.append(CheckResult(not particle_missing, "registry.particles", f"missing={particle_missing}"))

    black_keys = [key for key, value in asset_registry.PARTICLE_TEXTURES.items() if value[0] == "black"]
    opaque_corners = []
    for key in black_keys:
        texture = assets.get(key)
        if texture is None:
            continue
        corners = [
            texture.get_at((0, 0)).a,
            texture.get_at((texture.get_width() - 1, 0)).a,
            texture.get_at((0, texture.get_height() - 1)).a,
            texture.get_at((texture.get_width() - 1, texture.get_height() - 1)).a,
        ]
        if max(corners) > 5:
            opaque_corners.append((key, max(corners)))
    results.append(CheckResult(not opaque_corners, "registry.black_particle_alpha", f"opaque_corners={opaque_corners}"))
    return results


def check_stage_layouts(assets: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    for idx, map_data in enumerate(assets.get("maps", [])[:3]):
        width = float(map_data["width_px"])
        height = float(map_data["height_px"])
        layout = get_stage_layout(idx, width, height)
        points = [layout["altar"], layout["boss"], layout["portal"], *layout["spawns"]]
        out_of_bounds = [
            (round(point.x, 1), round(point.y, 1))
            for point in points
            if point.x < 40 or point.y < 40 or point.x > width - 40 or point.y > height - 40
        ]
        results.append(CheckResult(not out_of_bounds, f"stage_layout.map{idx+1}", f"out_of_bounds={out_of_bounds}"))
    return results


def check_combat_flow(assets: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    maps = assets.get("maps", [])
    if not maps:
        return [CheckResult(False, "flow.maps", "no maps loaded")]

    for idx, expected_boss in enumerate(("TenguRed", "SquidGreen", "DragonGreen")):
        map_data = maps[idx]
        player = pygame.Vector2(map_data["width_px"] * 0.5, map_data["height_px"] * 0.5)
        boss = game_2d.spawn_enemy(
            player,
            idx + 1,
            assets,
            map_data["width_px"],
            map_data["height_px"],
            map_data.get("walkable"),
            True,
            idx,
        )
        results.append(CheckResult(boss.is_boss and boss.name == expected_boss, f"flow.boss.map{idx+1}", f"got={boss.name}"))

        projectiles: list[game_2d.Projectile] = []
        effects: list[list] = []
        game_2d.spawn_boss_skill(boss, player + pygame.Vector2(120, 0), idx + 1, projectiles, effects, {}, "active")
        hostile_count = sum(1 for projectile in projectiles if projectile.hostile)
        results.append(CheckResult(hostile_count > 0, f"flow.boss_skill.map{idx+1}", f"hostile_projectiles={hostile_count}"))

    for skill_id in range(1, len(game_2d.SKILLS) + 1):
        projectile = game_2d.Projectile((100, 100), (250, 0), 10, 12, 0.5, (255, 255, 255), skill_id)
        head, trail, scale = game_2d.get_projectile_vfx_assets(assets, projectile)
        ok = head is not None and trail is not None and scale > 0
        results.append(CheckResult(ok, f"flow.skill_vfx.{skill_id}", f"scale={scale:.2f}"))

    tracking_projectile = game_2d.Projectile((100, 100), (250, 0), 10, 12, 0.5, (255, 255, 255), 4)
    results.append(CheckResult(hasattr(tracking_projectile, "hit_targets") and isinstance(tracking_projectile.hit_targets, set), "flow.projectile_hit_tracking", "hit_targets=set"))

    spawn_counts = [game_2d.get_normal_spawn_count(idx, idx + 1) for idx in range(3)]
    results.append(CheckResult(spawn_counts == [10, 15, 20], "flow.spawn_counts", f"counts={spawn_counts}"))

    probe = pygame.Surface((320, 240), pygame.SRCALPHA)
    try:
        chain_effect = ["chain_lightning", pygame.Vector2(80, 120), pygame.Vector2(230, 95), 0.22, 0.24, (190, 170, 255)]
        results.append(CheckResult(game_2d.get_effect_life_index(["hit", pygame.Vector2(), 0.2, 30, 0, (255, 255, 255)]) == 2, "flow.effect_life.default", "index=2"))
        results.append(CheckResult(game_2d.get_effect_life_index(chain_effect) == 3, "flow.effect_life.chain", "index=3"))
        draw_effect(probe, pygame.Vector2(), assets, ["skill5_array", pygame.Vector2(160, 120), 2.5, 3.0, 120, 60, 0.2])
        draw_effect(probe, pygame.Vector2(), assets, ["black_lightning", pygame.Vector2(160, 120), 0.22, 0.28, 96])
        draw_effect(probe, pygame.Vector2(), assets, chain_effect)
        draw_player_aura(probe, pygame.Vector2(), assets, pygame.Vector2(160, 120), 6, True, True)
        results.append(CheckResult(True, "flow.skill5_array_render", "rendered"))
    except Exception as exc:
        results.append(CheckResult(False, "flow.skill5_array_render", repr(exc)))

    return results


def run_checks() -> int:
    pygame.init()
    pygame.display.set_mode((1, 1))
    assets = game_2d.load_assets()

    results: list[CheckResult] = []
    results.extend(check_maps(assets))
    results.extend(check_registry_contract(assets))
    results.extend(check_stage_layouts(assets))
    results.extend(check_boss_contract(assets))
    results.extend(check_actor_frames(assets))
    results.extend(check_combat_flow(assets))

    failed = [item for item in results if not item.ok]
    passed = len(results) - len(failed)
    print(f"[QA] passed={passed} failed={len(failed)} total={len(results)}")
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    pygame.quit()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
