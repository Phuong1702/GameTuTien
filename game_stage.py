import pygame

from asset_registry import STAGE_LAYOUTS
from game_config import SHOP_RADIUS


def _scaled_point(pair, arena_w, arena_h):
    return pygame.Vector2(float(pair[0]) * arena_w, float(pair[1]) * arena_h)


def get_stage_layout(map_idx: int, arena_w: float, arena_h: float) -> dict:
    source = STAGE_LAYOUTS[map_idx % len(STAGE_LAYOUTS)]
    return {
        "altar": _scaled_point(source["altar"], arena_w, arena_h),
        "boss": _scaled_point(source["boss"], arena_w, arena_h),
        "portal": _scaled_point(source["portal"], arena_w, arena_h),
        "spawns": [_scaled_point(point, arena_w, arena_h) for point in source["spawns"]],
        "boss_radius": max(220.0, min(arena_w, arena_h) * 0.18),
        "shop_radius": SHOP_RADIUS,
    }


def choose_spawn_points(layout: dict, player: pygame.Vector2, min_distance=260.0) -> list[pygame.Vector2]:
    points = [point for point in layout["spawns"] if point.distance_to(player) >= min_distance]
    return points if points else list(layout["spawns"])
