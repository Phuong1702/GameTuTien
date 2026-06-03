import math
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import pygame

from asset_registry import (
    BOSS_BY_MAP,
    DEFAULT_MOB_ACTOR_SCALE,
    EXCLUDED_MOB_ACTORS,
    MAP_FILES,
    MOB_ACTOR_SCALE_OVERRIDES,
    NINJA_HERO,
    NINJA_NPCS,
    NINJA_SKILL_FX,
    PARTICLE_TEXTURES,
    SKILL_ICONS,
    SKILL_SFX,
)
from game_config import *

def load_tile(tile_id, scale=3):
    path = Path(__file__).parent / "assets" / "kenney_tiny_dungeon" / "Tiles" / f"tile_{tile_id:04d}.png"
    surf = pygame.image.load(str(path)).convert_alpha()
    return pygame.transform.scale(surf, (surf.get_width() * scale, surf.get_height() * scale))


def load_sheet_tile(sheet_path: Path, col: int, row: int, tile_px=16, scale=3):
    sheet = pygame.image.load(str(sheet_path)).convert_alpha()
    rect = pygame.Rect(col * tile_px, row * tile_px, tile_px, tile_px)
    tile = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
    tile.blit(sheet, (0, 0), rect)
    return pygame.transform.scale(tile, (tile_px * scale, tile_px * scale))


def load_sheet_frame(sheet_path: Path, frame_w: int, frame_h: int, frame_idx=0, scale=1.0):
    sheet = pygame.image.load(str(sheet_path)).convert_alpha()
    cols = max(1, sheet.get_width() // frame_w)
    frame_idx = max(0, min(cols - 1, frame_idx))
    rect = pygame.Rect(frame_idx * frame_w, 0, frame_w, frame_h)
    frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), rect)
    out_w = int(frame_w * scale)
    out_h = int(frame_h * scale)
    return pygame.transform.scale(frame, (out_w, out_h))


def load_static_image(path: Path, scale=1.0):
    surf = pygame.image.load(str(path)).convert_alpha()
    if abs(scale - 1.0) < 0.001:
        return surf
    return pygame.transform.scale(surf, (int(surf.get_width() * scale), int(surf.get_height() * scale)))


def load_particle_texture(path: Path, remove_black=False):
    surf = pygame.image.load(str(path)).convert_alpha()
    if not remove_black:
        return surf
    out = surf.copy()
    out.lock()
    for y in range(out.get_height()):
        for x in range(out.get_width()):
            r, g, b, a = out.get_at((x, y))
            brightness = max(r, g, b)
            if brightness < 18:
                out.set_at((x, y), (r, g, b, 0))
            elif brightness < 70:
                out.set_at((x, y), (r, g, b, int(a * (brightness - 18) / 52)))
    out.unlock()
    return out


def load_strip_anim(path: Path, frame_w=16, frame_h=16, scale=3):
    if not path.exists():
        return []
    sheet = pygame.image.load(str(path)).convert_alpha()
    cols = max(1, sheet.get_width() // frame_w)
    rows = max(1, sheet.get_height() // frame_h)
    frames = []
    for col in range(cols):
        rect = pygame.Rect(col * frame_w, 0, frame_w, frame_h)
        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), rect)
        frames.append(pygame.transform.scale(frame, (frame_w * scale, frame_h * scale)))
    if not frames:
        return []
    if rows > 1:
        # Keep direction-agnostic row 0 for top-down simplicity.
        return frames
    return frames


ACTOR_FRAME_WIDTHS = {
    "GiantBlueSamurai": {
        "idle": 96,
        "walk": 96,
        "attackleft": 96,
        "attackright": 96,
        "chargeleft": 96,
        "chargeright": 96,
        "hit": 48,
    },
    "GiantRedSamurai": {
        "idle": 96,
        "walk": 96,
        "attackleft": 96,
        "attackright": 96,
        "chargeleft": 96,
        "chargeright": 96,
        "hit": 48,
    },
    "GiantSlime": {
        "idle": 62,
        "hit": 62,
    },
    "GiantSlime2": {
        "idle": 62,
        "hit": 62,
    },
    "SquidGreen": {
        "idle": 76,
        "walk": 76,
        "attack": 76,
        "attackloop": 76,
        "hit": 76,
        "shoot": 76,
    },
    "SquidRed": {
        "idle": 76,
        "walk": 76,
        "attack": 76,
        "attackloop": 76,
        "hit": 76,
        "shoot": 76,
    },
}


def load_horizontal_strip(path: Path, scale=1.0, actor_name=""):
    if not path.exists():
        return []
    sheet = pygame.image.load(str(path)).convert_alpha()
    frame_h = sheet.get_height()
    if frame_h <= 0:
        return []
    sheet_w = sheet.get_width()
    actor_overrides = ACTOR_FRAME_WIDTHS.get(actor_name, {})
    frame_w = actor_overrides.get(path.stem.lower(), frame_h)
    if sheet_w % frame_w != 0:
        candidates = []
        for cols in range(2, 13):
            if sheet_w % cols == 0:
                candidate_w = sheet_w // cols
                ratio = candidate_w / float(frame_h)
                if 0.55 <= ratio <= 2.25:
                    candidates.append((abs(candidate_w - frame_h), candidate_w))
        if candidates:
            frame_w = sorted(candidates)[0][1]
    if sheet.get_width() < frame_w:
        return []
    cols = max(1, sheet.get_width() // frame_w)
    frames = []
    for col in range(cols):
        rect = pygame.Rect(col * frame_w, 0, frame_w, frame_h)
        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), rect)
        out_w = max(1, int(frame_w * scale))
        out_h = max(1, int(frame_h * scale))
        frames.append(pygame.transform.scale(frame, (out_w, out_h)))
    return frames


def _find_actor_sheet(actor_dir: Path, prefixes):
    if not actor_dir.exists():
        return None
    files = sorted(actor_dir.glob("*.png"))
    lower_prefixes = tuple(prefix.lower() for prefix in prefixes)
    for file_path in files:
        stem = file_path.stem.lower()
        if "preview" in stem:
            continue
        if stem.startswith(lower_prefixes):
            return file_path
    return None


def build_dragon_actor_frames(actor_dir: Path, scale=1.0):
    required = ["Head.png", "Wing.png", "Body1.png", "Body2.png", "BodyEnd.png"]
    if not all((actor_dir / name).exists() for name in required):
        return []
    head = pygame.image.load(str(actor_dir / "Head.png")).convert_alpha()
    wing = pygame.image.load(str(actor_dir / "Wing.png")).convert_alpha()
    body1 = pygame.image.load(str(actor_dir / "Body1.png")).convert_alpha()
    body2 = pygame.image.load(str(actor_dir / "Body2.png")).convert_alpha()
    tail = pygame.image.load(str(actor_dir / "BodyEnd.png")).convert_alpha()

    frames = []
    for phase in range(6):
        bob = int(math.sin(phase / 6.0 * math.tau) * 2)
        frame = pygame.Surface((112, 92), pygame.SRCALPHA)
        frame.blit(tail, (10, 54 + bob))
        frame.blit(body2, (32, 50 - bob))
        frame.blit(body1, (52, 44 + bob))
        left_wing = pygame.transform.flip(wing, True, False)
        frame.blit(left_wing, (4, 8 + bob))
        frame.blit(wing, (52, 8 - bob))
        frame.blit(head, (36, 26 + bob))
        out_w = max(1, int(frame.get_width() * scale))
        out_h = max(1, int(frame.get_height() * scale))
        frames.append(pygame.transform.scale(frame, (out_w, out_h)))
    return frames


def load_actor_state_pack(actor_dir: Path, scale=2.6):
    if not actor_dir.exists():
        return None
    dragon_frames = build_dragon_actor_frames(actor_dir, scale)
    if dragon_frames:
        states = {
            "idle": dragon_frames,
            "walk": dragon_frames,
            "attack": dragon_frames,
            "hit": dragon_frames,
            "death": dragon_frames,
        }
        return {"name": actor_dir.name, "states": states, "scale": scale}
    idle_sheet = _find_actor_sheet(actor_dir, ("Idle",))
    if idle_sheet is None:
        fallback = None
        sprite_sheet = actor_dir / "Sprite.png"
        if sprite_sheet.exists():
            fallback = sprite_sheet
        if fallback is None:
            return None
        frame = load_static_image(fallback, scale)
        states = {
            "idle": [frame],
            "walk": [frame],
            "attack": [frame],
            "hit": [frame],
            "death": [frame],
        }
        return {"name": actor_dir.name, "states": states, "scale": scale}
    states = {
        "idle": load_horizontal_strip(idle_sheet, scale, actor_dir.name),
        "walk": [],
        "attack": [],
        "hit": [],
        "death": [],
    }
    walk_sheet = _find_actor_sheet(actor_dir, ("Walk", "Move", "Jump"))
    attack_sheet = _find_actor_sheet(actor_dir, ("Attack", "Charge"))
    hit_sheet = _find_actor_sheet(actor_dir, ("Hit",))
    death_sheet = _find_actor_sheet(actor_dir, ("Death", "Dead"))
    if walk_sheet is not None:
        states["walk"] = load_horizontal_strip(walk_sheet, scale, actor_dir.name)
    if attack_sheet is not None:
        states["attack"] = load_horizontal_strip(attack_sheet, scale, actor_dir.name)
    if hit_sheet is not None:
        states["hit"] = load_horizontal_strip(hit_sheet, scale, actor_dir.name)
    if death_sheet is not None:
        states["death"] = load_horizontal_strip(death_sheet, scale, actor_dir.name)
    if not states["walk"]:
        states["walk"] = list(states["idle"])
    if not states["attack"]:
        states["attack"] = list(states["walk"])
    return {"name": actor_dir.name, "states": states, "scale": scale}


def load_monster_anim_pack(monster_root: Path, monster_name: str, scale=3):
    folder = monster_root / monster_name
    candidates = [
        folder / "SpriteSheet.png",
        folder / f"{monster_name}.png",
        folder / f"{monster_name.lower()}.png",
    ]
    for path in candidates:
        if path.exists():
            return load_strip_anim(path, 16, 16, scale)
    return []


def build_ninja_maps(base_dir: Path, map_count=5, tile_scale=3):
    pack = base_dir / "assets" / "ninja_adventure_pack" / "Ninja Adventure - Asset Pack"
    field = pack / "Backgrounds" / "Tilesets" / "TilesetField.png"
    nature = pack / "Backgrounds" / "Tilesets" / "TilesetNature.png"
    dungeon = pack / "Backgrounds" / "Tilesets" / "TilesetDungeon.png"
    village = pack / "Backgrounds" / "Tilesets" / "TilesetVillageAbandoned.png"
    element = pack / "Backgrounds" / "Tilesets" / "TilesetElement.png"
    sources = [field, nature, dungeon, village, element]
    if not all(path.exists() for path in sources):
        return []

    map_names = ["Ngo Mon Son", "Linh Moc Lam", "Co Dien Dia Cung", "Luyen Dan That", "Ma Vuc Tran Mon"]
    w_tiles, h_tiles = 32, 20
    tile_px = 16 * tile_scale
    maps = []
    for idx in range(min(map_count, len(map_names))):
        floor_src = sources[idx % len(sources)]
        deco_src = sources[(idx + 1) % len(sources)]
        floor_sheet = pygame.image.load(str(floor_src)).convert_alpha()
        deco_sheet = pygame.image.load(str(deco_src)).convert_alpha()
        floor_cols = max(1, floor_sheet.get_width() // 16)
        floor_rows = max(1, floor_sheet.get_height() // 16)
        deco_cols = max(1, deco_sheet.get_width() // 16)
        deco_rows = max(1, deco_sheet.get_height() // 16)
        surface = pygame.Surface((w_tiles * tile_px, h_tiles * tile_px), pygame.SRCALPHA)
        walkable = []
        for y in range(h_tiles):
            for x in range(w_tiles):
                fc = (x * 3 + y * 2 + idx * 5) % floor_cols
                fr = (x + y + idx * 2) % floor_rows
                floor_tile = load_sheet_tile(floor_src, fc, fr, 16, tile_scale)
                px = x * tile_px
                py = y * tile_px
                surface.blit(floor_tile, (px, py))
                blocked = ((x * 7 + y * 11 + idx * 13) % 29 == 0) and (x > 1 and x < w_tiles - 2 and y > 1 and y < h_tiles - 2)
                if blocked:
                    dc = (x + idx * 3) % deco_cols
                    dr = (y + idx * 5) % deco_rows
                    deco_tile = load_sheet_tile(deco_src, dc, dr, 16, tile_scale)
                    surface.blit(deco_tile, (px, py))
                else:
                    walkable.append(pygame.Vector2(px + tile_px * 0.5, py + tile_px * 0.5))
        maps.append({
            "name": map_names[idx],
            "surface": surface,
            "width_px": surface.get_width(),
            "height_px": surface.get_height(),
            "walkable": walkable if walkable else [pygame.Vector2(surface.get_width() * 0.5, surface.get_height() * 0.5)],
        })
    return maps


def extract_tiles_from_sheet(sheet_path: Path, tile_px=16, scale=3):
    if not sheet_path.exists():
        return []
    sheet = pygame.image.load(str(sheet_path)).convert_alpha()
    cols = max(1, sheet.get_width() // tile_px)
    rows = max(1, sheet.get_height() // tile_px)
    tiles = []
    for row in range(rows):
        for col in range(cols):
            rect = pygame.Rect(col * tile_px, row * tile_px, tile_px, tile_px)
            tile = pygame.Surface((tile_px, tile_px), pygame.SRCALPHA)
            tile.blit(sheet, (0, 0), rect)
            tiles.append(pygame.transform.scale(tile, (tile_px * scale, tile_px * scale)))
    return tiles


def draw_tile_blob(surface, center_x, center_y, radius_tiles, tile_choices, tile_px, walkable, block=False):
    if not tile_choices:
        return
    cx = int(center_x // tile_px)
    cy = int(center_y // tile_px)
    for y in range(cy - radius_tiles, cy + radius_tiles + 1):
        for x in range(cx - radius_tiles, cx + radius_tiles + 1):
            if x < 0 or y < 0:
                continue
            px = x * tile_px
            py = y * tile_px
            if px >= surface.get_width() or py >= surface.get_height():
                continue
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy > radius_tiles * radius_tiles:
                continue
            tile = tile_choices[(x * 7 + y * 11 + radius_tiles) % len(tile_choices)]
            surface.blit(tile, (px, py))
            pos = pygame.Vector2(px + tile_px * 0.5, py + tile_px * 0.5)
            if block:
                if pos in walkable:
                    walkable.remove(pos)
            else:
                walkable.append(pos)


def build_valley_maps(base_dir: Path, tile_scale=3):
    root = base_dir / "assets" / "valley_ruin_pack" / "Valley Ruin Asset Pack V0.3"
    if not root.exists():
        return []
    grass_tiles = extract_tiles_from_sheet(root / "Tiles Maps" / "GrassTile.png", 16, tile_scale)
    sand_tiles = extract_tiles_from_sheet(root / "Tiles Maps" / "SandTile.png", 16, tile_scale)
    wall_tiles = extract_tiles_from_sheet(root / "Tiles Maps" / "RockWall.png", 16, tile_scale)
    grass_wall_tiles = extract_tiles_from_sheet(root / "Tiles Maps" / "GrassWall.png", 16, tile_scale)
    dirt_tile = load_sheet_tile(root / "Tiles Maps" / "DirtTile.png", 0, 0, 16, tile_scale)
    flora_tiles = extract_tiles_from_sheet(root / "FlowerAndGrass.png", 16, tile_scale)
    stone_tiles = extract_tiles_from_sheet(root / "Objects" / "stone and bush.png", 16, tile_scale)
    if not grass_tiles or not sand_tiles:
        return []
    tile_px = 16 * tile_scale
    w_tiles, h_tiles = 32, 20
    map_names = ["Moc Mon Cuu Tho", "Linh Hoa Dao Tam", "Hai Nhai Co Lo"]
    maps = []

    grass_base = grass_tiles[min(len(grass_tiles) - 1, 11)]
    sand_base = sand_tiles[min(len(sand_tiles) - 1, 11)]
    wall_base = (wall_tiles or grass_wall_tiles)[min(len((wall_tiles or grass_wall_tiles)) - 1, 6)] if (wall_tiles or grass_wall_tiles) else grass_base
    wall_alt = (wall_tiles or grass_wall_tiles)[min(len((wall_tiles or grass_wall_tiles)) - 1, 14)] if (wall_tiles or grass_wall_tiles) else wall_base
    flower = flora_tiles[min(len(flora_tiles) - 1, 2)] if flora_tiles else None
    grass_deco = flora_tiles[min(len(flora_tiles) - 1, 5)] if flora_tiles else None
    stone = stone_tiles[min(len(stone_tiles) - 1, 5)] if stone_tiles else None
    chest = load_sheet_tile(root / "Objects" / "ChestSheet.png", 0, 0, 16, tile_scale) if (root / "Objects" / "ChestSheet.png").exists() else None
    giant_tree = load_static_image(root / "Objects" / "Giant_Tree.png", 0.42) if (root / "Objects" / "Giant_Tree.png").exists() else None

    def new_surface(base_tile):
        surface = pygame.Surface((w_tiles * tile_px, h_tiles * tile_px), pygame.SRCALPHA)
        walk = [[True for _ in range(w_tiles)] for _ in range(h_tiles)]
        for y in range(h_tiles):
            for x in range(w_tiles):
                surface.blit(base_tile, (x * tile_px, y * tile_px))
        return surface, walk

    def put(surface, x, y, tile):
        if 0 <= x < w_tiles and 0 <= y < h_tiles and tile is not None:
            surface.blit(tile, (x * tile_px, y * tile_px))

    def block(surface, walk, x, y, tile):
        if 0 <= x < w_tiles and 0 <= y < h_tiles and tile is not None:
            surface.blit(tile, (x * tile_px, y * tile_px))
            walk[y][x] = False

    def to_walkable(walk):
        out = []
        for y in range(h_tiles):
            for x in range(w_tiles):
                if walk[y][x]:
                    out.append(pygame.Vector2(x * tile_px + tile_px * 0.5, y * tile_px + tile_px * 0.5))
        return out if out else [pygame.Vector2(w_tiles * tile_px * 0.5, h_tiles * tile_px * 0.5)]

    for idx, name in enumerate(map_names):
        surface, walk = new_surface(grass_base)
        center = pygame.Vector2(w_tiles / 2, h_tiles / 2)

        if idx == 0:
            # Similar to first reference: forest + big clearing + giant tree shrine top-center.
            for y in range(h_tiles):
                for x in range(w_tiles):
                    radius = ((x - center.x) ** 2) / 90.0 + ((y - 13.0) ** 2) / 18.0
                    if radius < 1.0:
                        put(surface, x, y, dirt_tile)
            for x in range(w_tiles):
                block(surface, walk, x, 0, wall_base)
                if x % 2 == 0:
                    block(surface, walk, x, 1, wall_alt)
            for x in range(5, 27):
                if x % 3 != 1:
                    block(surface, walk, x, 4, wall_base)
            for y in range(5, 13):
                block(surface, walk, 1, y, wall_base)
                block(surface, walk, w_tiles - 2, y, wall_base)
            if giant_tree is not None:
                tx = surface.get_width() // 2 - giant_tree.get_width() // 2
                ty = -12
                surface.blit(giant_tree, (tx, ty))
            if chest is not None:
                surface.blit(chest, (surface.get_width() // 2 - chest.get_width() // 2, 5 * tile_px))
            for i in range(130):
                x = 2 + (i * 7) % 28
                y = 6 + (i * 11) % 11
                put(surface, x, y, flower if i % 3 else grass_deco)

        elif idx == 1:
            # Similar to second reference: island circles and center stone ring.
            for y in range(h_tiles):
                for x in range(w_tiles):
                    d = ((x - center.x) ** 2) / 95.0 + ((y - center.y) ** 2) / 38.0
                    if d < 2.1:
                        put(surface, x, y, sand_base)
                    if d < 1.2:
                        put(surface, x, y, grass_base)
                    if 0.26 < d < 0.40:
                        block(surface, walk, x, y, wall_base)
                    if d < 0.18:
                        put(surface, x, y, grass_deco if grass_deco else grass_base)
            for i in range(220):
                x = 7 + (i * 5) % 18
                y = 4 + (i * 9) % 12
                if ((x - center.x) ** 2) / 70.0 + ((y - center.y) ** 2) / 26.0 < 1.0:
                    put(surface, x, y, flower if i % 2 else grass_deco)
            for i in range(16):
                x = 6 + (i * 13) % 20
                y = 4 + (i * 7) % 12
                block(surface, walk, x, y, stone if stone else wall_alt)

        else:
            # Similar to third reference: upper cliff lane + lower sand coast.
            for y in range(h_tiles):
                if y >= 13:
                    for x in range(w_tiles):
                        put(surface, x, y, sand_base)
            for y in range(1, 7):
                for x in range(w_tiles):
                    if x % 3 != 1:
                        block(surface, walk, x, y, wall_base if y < 4 else wall_alt)
            for y in range(6, 14):
                path_center = 16 + int(4 * math.sin(y * 0.7))
                for x in range(path_center - 3, path_center + 4):
                    put(surface, x, y, dirt_tile)
            for i in range(100):
                x = 2 + (i * 7) % 28
                y = 7 + (i * 5) % 10
                put(surface, x, y, flower if i % 2 else grass_deco)
            for i in range(14):
                x = 3 + i * 2
                y = 9 + (i % 3)
                if i % 4 == 0:
                    block(surface, walk, x, y, stone if stone else wall_alt)

        maps.append({
            "name": name,
            "surface": surface,
            "width_px": surface.get_width(),
            "height_px": surface.get_height(),
            "walkable": to_walkable(walk),
        })
    return maps


def build_reference_image_maps(base_dir: Path):
    maps_dir = base_dir / "assets" / "valley_maps"
    if not maps_dir.exists():
        return []
    maps = []
    for item in MAP_FILES:
        name = item["name"]
        img_path = None
        for filename in item["files"]:
            candidate = maps_dir / filename
            if candidate.exists():
                img_path = candidate
                break
        if img_path is None:
            return []
        src = pygame.image.load(str(img_path)).convert_alpha()
        w, h = src.get_width(), src.get_height()
        if w < 320 or h < 180:
            return []
        tw = max(320, int(w * MAP_WORLD_SCALE))
        th = max(180, int(h * MAP_WORLD_SCALE))
        surface = pygame.transform.smoothscale(src, (tw, th))
        walkable = []
        tile_px = int(48 * MAP_WORLD_SCALE)
        cols = max(1, surface.get_width() // tile_px)
        rows = max(1, surface.get_height() // tile_px)
        for y in range(rows):
            for x in range(cols):
                walkable.append(pygame.Vector2(x * tile_px + tile_px * 0.5, y * tile_px + tile_px * 0.5))
        maps.append({
            "name": name,
            "surface": surface,
            "width_px": surface.get_width(),
            "height_px": surface.get_height(),
            "walkable": walkable,
        })
    return maps


def decode_tmx_gid(raw_gid):
    if raw_gid <= 0:
        return 0
    return raw_gid & TMX_FLIP_MASK


def parse_tmx_layer_data(layer_node, width, height):
    data = layer_node.find("data")
    if data is None or not data.text:
        return [[0 for _ in range(width)] for _ in range(height)]
    values = [int(v.strip()) for v in data.text.replace("\n", "").split(",") if v.strip()]
    if len(values) < width * height:
        values.extend([0] * (width * height - len(values)))
    grid = []
    idx = 0
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append(decode_tmx_gid(values[idx]))
            idx += 1
        grid.append(row)
    return grid


def variant_transform(grid, shift_x=0, shift_y=0, mirror_x=False, mirror_y=False):
    height = len(grid)
    width = len(grid[0]) if height else 0
    out = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        src_y = (height - 1 - y) if mirror_y else y
        for x in range(width):
            src_x = (width - 1 - x) if mirror_x else x
            out[y][x] = grid[(src_y - shift_y) % height][(src_x - shift_x) % width]
    return out


def draw_tmx_layer_to_surface(surface, layer_grid, tile_cache, tile_px):
    for y, row in enumerate(layer_grid):
        py = y * tile_px
        for x, gid in enumerate(row):
            tile = tile_cache.get(gid)
            if tile is not None:
                surface.blit(tile, (x * tile_px, py))


def load_tmx_tileset_cache(tmx_dir: Path, ts_node, tile_scale: int):
    firstgid = int(ts_node.attrib.get("firstgid", "1"))
    source = ts_node.attrib.get("source", "")
    if not source:
        return {}, 16, 16
    tsx_path = tmx_dir / source
    if not tsx_path.exists():
        return {}, 16, 16
    tsx_root = ET.parse(str(tsx_path)).getroot()
    tile_w = int(tsx_root.attrib.get("tilewidth", "16"))
    tile_h = int(tsx_root.attrib.get("tileheight", "16"))
    spacing = int(tsx_root.attrib.get("spacing", "0"))
    columns = int(tsx_root.attrib.get("columns", "1"))
    tile_count = int(tsx_root.attrib.get("tilecount", "0"))
    image_node = tsx_root.find("image")
    if image_node is None:
        return {}, tile_w, tile_h
    image_path = tsx_path.parent / image_node.attrib.get("source", "")
    if not image_path.exists():
        return {}, tile_w, tile_h
    sheet = pygame.image.load(str(image_path)).convert_alpha()
    cache = {}
    for tile_id in range(tile_count):
        col = tile_id % columns
        row = tile_id // columns
        sx = col * (tile_w + spacing)
        sy = row * (tile_h + spacing)
        rect = pygame.Rect(sx, sy, tile_w, tile_h)
        tile = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
        tile.blit(sheet, (0, 0), rect)
        cache[firstgid + tile_id] = pygame.transform.scale(tile, (tile_w * tile_scale, tile_h * tile_scale))
    return cache, tile_w, tile_h


def parse_all_tmx_layers(root, map_w: int, map_h: int):
    layers = []
    for layer_node in root.findall("layer"):
        layers.append(parse_tmx_layer_data(layer_node, map_w, map_h))
    return layers


def build_map_surface_from_layers(layers, tile_cache, map_w: int, map_h: int, tile_px: int):
    surface = pygame.Surface((map_w * tile_px, map_h * tile_px), pygame.SRCALPHA)
    for layer in layers:
        draw_tmx_layer_to_surface(surface, layer, tile_cache, tile_px)
    return surface


def build_walkable_from_layers(layers, map_w: int, map_h: int, tile_px: int):
    walkable = []
    base_layer = layers[0] if layers else [[0 for _ in range(map_w)] for _ in range(map_h)]
    block_layer = layers[1] if len(layers) > 1 else [[0 for _ in range(map_w)] for _ in range(map_h)]
    for y in range(map_h):
        for x in range(map_w):
            if base_layer[y][x] > 0 and block_layer[y][x] == 0:
                walkable.append(pygame.Vector2(x * tile_px + tile_px * 0.5, y * tile_px + tile_px * 0.5))
    if not walkable:
        walkable = [pygame.Vector2(map_w * tile_px * 0.5, map_h * tile_px * 0.5)]
    return walkable


def build_multi_maps_from_tmx(base_dir: Path, map_count=5, tile_scale=3):
    tiled_dir = base_dir / "assets" / "kenney_tiny_dungeon" / "Tiled"
    tmx_paths = sorted(tiled_dir.glob("*.tmx"))
    if not tmx_paths:
        return []
    maps = []
    for tmx_path in tmx_paths:
        root = ET.parse(str(tmx_path)).getroot()
        map_w = int(root.attrib.get("width", "0"))
        map_h = int(root.attrib.get("height", "0"))
        if map_w <= 0 or map_h <= 0:
            continue
        tile_cache = {}
        tile_w = 16
        tile_h = 16
        for ts_node in root.findall("tileset"):
            ts_cache, tw, th = load_tmx_tileset_cache(tmx_path.parent, ts_node, tile_scale)
            if ts_cache:
                tile_cache.update(ts_cache)
                tile_w = tw
                tile_h = th
        if not tile_cache:
            continue
        layers = parse_all_tmx_layers(root, map_w, map_h)
        tile_px = tile_w * tile_scale
        surface = build_map_surface_from_layers(layers, tile_cache, map_w, map_h, tile_px)
        walkable = build_walkable_from_layers(layers, map_w, map_h, tile_px)
        maps.append({
            "name": tmx_path.stem,
            "surface": surface,
            "width_px": surface.get_width(),
            "height_px": surface.get_height(),
            "walkable": walkable,
            "layers": layers,
            "tile_px": tile_px,
            "tile_cache": tile_cache,
        })
        if len(maps) >= map_count:
            break

    if maps and len(maps) < map_count:
        seed = maps[0]
        seed_layers = seed["layers"]
        map_w = int(seed["width_px"] // seed["tile_px"])
        map_h = int(seed["height_px"] // seed["tile_px"])
        variants = [
            {"shift": (4, 2), "mx": True, "my": False},
            {"shift": (8, 5), "mx": False, "my": True},
            {"shift": (11, 7), "mx": True, "my": True},
            {"shift": (15, 3), "mx": False, "my": False},
        ]
        variant_idx = 0
        while len(maps) < map_count:
            variant = variants[variant_idx % len(variants)]
            variant_idx += 1
            transformed_layers = [variant_transform(layer, variant["shift"][0], variant["shift"][1], variant["mx"], variant["my"]) for layer in seed_layers]
            surface = build_map_surface_from_layers(transformed_layers, seed["tile_cache"], map_w, map_h, seed["tile_px"])
            walkable = build_walkable_from_layers(transformed_layers, map_w, map_h, seed["tile_px"])
            maps.append({
                "name": f"{seed['name']}_v{len(maps) + 1}",
                "surface": surface,
                "width_px": surface.get_width(),
                "height_px": surface.get_height(),
                "walkable": walkable,
                "layers": transformed_layers,
                "tile_px": seed["tile_px"],
                "tile_cache": seed["tile_cache"],
            })
    return maps


def load_assets():
    particle_dir = Path(__file__).parent / "assets" / "kenney_particle_pack" / "PNG (Transparent)"
    particle_black_dir = Path(__file__).parent / "assets" / "kenney_particle_pack" / "PNG (Black background)"
    pixel_root = Path(__file__).parent / "assets" / "pixel_crawler_free_pack" / "Pixel Crawler - Free Pack"
    ninja_root = Path(__file__).parent / "assets" / "ninja_adventure_pack" / "Ninja Adventure - Asset Pack"

    if pixel_root.exists():
        floor_sheet = pixel_root / "Environment" / "Tilesets" / "Floors_Tiles.png"
        wall_sheet = pixel_root / "Environment" / "Tilesets" / "Wall_Tiles.png"
        props_sheet = pixel_root / "Environment" / "Props" / "Static" / "Dungeon_Props.png"
        vegetation_sheet = pixel_root / "Environment" / "Props" / "Static" / "Vegetation.png"
        esoteric_sheet = pixel_root / "Environment" / "Props" / "Static" / "Esoteric.png"
        station_root = pixel_root / "Environment" / "Structures" / "Stations"
        npc_root = pixel_root / "Entities" / "Npc's"
        mob_root = pixel_root / "Entities" / "Mobs"
        assets = {
            "floors_by_chapter": [
                [load_sheet_tile(floor_sheet, c, row, 16, 3) for c in (2, 3, 4, 5, 6, 7)]
                for row in (7, 8, 9, 10, 11)
            ],
            "walls_by_chapter": [
                [load_sheet_tile(wall_sheet, c, row, 16, 3) for c in (1, 2, 3, 4, 5, 6, 7, 8)]
                for row in (2, 4, 6, 8, 10)
            ],
            "decor_by_chapter": [
                [load_sheet_tile(vegetation_sheet, c, row, 16, 3) for c in (1, 2, 3, 4, 5, 6)]
                for row in (1, 2, 3, 4, 5)
            ],
            "relic_by_chapter": [
                [load_sheet_tile(esoteric_sheet, c, row, 16, 3) for c in (1, 2, 3, 4, 5, 6)]
                for row in (1, 2, 3, 4, 5)
            ],
            "hero": load_sheet_frame(npc_root / "Wizzard" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
            "enemies": [
                load_sheet_frame(mob_root / "Skeleton Crew" / "Skeleton - Warrior" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(mob_root / "Skeleton Crew" / "Skeleton - Mage" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(mob_root / "Skeleton Crew" / "Skeleton - Rogue" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(mob_root / "Orc Crew" / "Orc - Warrior" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(mob_root / "Orc Crew" / "Orc - Shaman" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(mob_root / "Orc Crew" / "Orc - Rogue" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
            ],
            "bosses": [
                load_sheet_frame(mob_root / "Skeleton Crew" / "Skeleton - Warrior" / "Idle" / "Idle-Sheet.png", 32, 32, 1, 1.9),
                load_sheet_frame(mob_root / "Skeleton Crew" / "Skeleton - Mage" / "Idle" / "Idle-Sheet.png", 32, 32, 1, 1.9),
                load_sheet_frame(mob_root / "Orc Crew" / "Orc - Warrior" / "Idle" / "Idle-Sheet.png", 32, 32, 1, 1.9),
                load_sheet_frame(mob_root / "Orc Crew" / "Orc - Shaman" / "Idle" / "Idle-Sheet.png", 32, 32, 1, 1.9),
            ],
            "npcs": [
                load_sheet_frame(npc_root / "Knight" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(npc_root / "Rogue" / "Idle" / "Idle-Sheet.png", 32, 32, 0, 1.5),
                load_sheet_frame(npc_root / "Wizzard" / "Idle" / "Idle-Sheet.png", 32, 32, 1, 1.5),
            ],
            "trees": [
                load_static_image(pixel_root / "Environment" / "Props" / "Static" / "Trees" / "Model_01" / "Size_03.png", 1.6),
                load_static_image(pixel_root / "Environment" / "Props" / "Static" / "Trees" / "Model_02" / "Size_03.png", 1.6),
                load_static_image(pixel_root / "Environment" / "Props" / "Static" / "Trees" / "Model_03" / "Size_03.png", 1.45),
            ],
            "landmarks_by_chapter": [
                [load_static_image(station_root / "Bonfire" / "Bonfire.png", 1.6), load_static_image(station_root / "Workbench" / "Workbench.png", 1.35)],
                [load_static_image(station_root / "Bonfire" / "Bonfire.png", 1.45), load_static_image(station_root / "Sawmill" / "Level_1.png", 1.25)],
                [load_static_image(station_root / "Anvil" / "Anvil.png", 1.5), load_static_image(station_root / "Furnace" / "Furnace.png", 1.35)],
                [load_static_image(station_root / "Furnace" / "Furnace.png", 1.45), load_static_image(station_root / "Cooking Station" / "Cooking Station.png", 1.25)],
                [load_static_image(station_root / "Bonfire" / "Bonfire.png", 1.65), load_static_image(station_root / "Anvil" / "Anvil.png", 1.45)],
            ],
            "altar": load_sheet_tile(props_sheet, 6, 8, 16, 3),
            "chest": load_sheet_tile(props_sheet, 9, 8, 16, 3),
        }
    else:
        assets = {
            "floors_by_chapter": [[load_tile(i, 3) for i in chapter["floor_ids"]] for chapter in STORY_CHAPTERS],
            "walls_by_chapter": [[load_tile(i, 3) for i in chapter["wall_ids"]] for chapter in STORY_CHAPTERS],
            "hero": load_tile(84, 3),
            "enemies": [load_tile(i, 3) for i in (108, 110, 120, 121, 122, 124)],
            "bosses": [load_tile(i, 4) for i in (96, 97, 100, 121, 122)],
            "npcs": [load_tile(i, 3) for i in (84, 85, 86)],
            "trees": [],
            "decor_by_chapter": [[] for _ in STORY_CHAPTERS],
            "relic_by_chapter": [[] for _ in STORY_CHAPTERS],
            "landmarks_by_chapter": [[] for _ in STORY_CHAPTERS],
            "altar": load_tile(56, 3),
            "chest": load_tile(89, 3),
        }
    assets["maps"] = build_reference_image_maps(Path(__file__).parent)
    if not assets["maps"]:
        assets["maps"] = build_valley_maps(Path(__file__).parent, 3)
    if not assets["maps"]:
        assets["maps"] = build_ninja_maps(Path(__file__).parent, len(STORY_CHAPTERS), 3)
    for idx, map_data in enumerate(assets.get("maps", [])):
        if idx < len(STORY_CHAPTERS) and str(map_data.get("name", "")).lower().startswith("map"):
            map_data["name"] = STORY_CHAPTERS[idx]["name"]
    assets["ninja_tile_gallery"] = []
    ninja_tiles = ninja_root / "Backgrounds" / "Tilesets"
    if ninja_tiles.exists():
        for tile_path in sorted(ninja_tiles.glob("*.png")):
            tile = pygame.image.load(str(tile_path)).convert_alpha()
            sample = pygame.transform.smoothscale(tile, (24, 24))
            assets["ninja_tile_gallery"].append(sample)
    if ninja_root.exists():
        hero_path = ninja_root.joinpath(*NINJA_HERO["path"])
        hero_frame_w, hero_frame_h = NINJA_HERO["frame"]
        assets["hero_anim"] = load_strip_anim(hero_path, hero_frame_w, hero_frame_h, NINJA_HERO["scale"])
        assets["npc_anims"] = [
            load_strip_anim(ninja_root.joinpath(*item["path"]), 16, 16, item["scale"])
            for item in NINJA_NPCS
        ]
        assets["npc_names"] = [item["name"] for item in NINJA_NPCS]
        assets["enemy_anims"] = [
            load_strip_anim(ninja_root / "Actor" / "Monster" / "Skull" / "SpriteSheet.png", 16, 16, 3),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "Spirit" / "SpriteSheet.png", 16, 16, 3),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "LanternRed" / "SpriteSheet.png", 16, 16, 3),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "BlueBat" / "SpriteSheet.png", 16, 16, 3),
        ]
        assets["boss_anims"] = [
            load_strip_anim(ninja_root / "Actor" / "Monster" / "TRex" / "SpriteSheet.png", 16, 16, 4),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "Grey Trex" / "SpriteSheet.png", 16, 16, 4),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "RedOctopus" / "SpriteSheet.png", 16, 16, 4),
            load_strip_anim(ninja_root / "Actor" / "Monster" / "Panda" / "SpriteSheet.png", 16, 16, 4),
        ]
        assets["skill_fx_anim"] = [
            load_strip_anim(ninja_root.joinpath(*item["path"]), 32, 32, 2)
            for item in NINJA_SKILL_FX
        ]
        assets["skill_fx_names"] = [item["name"] for item in NINJA_SKILL_FX]
        assets["bgm_path"] = ninja_root / "Audio" / "Musics" / "10 - Dark Castle.ogg"
        assets["skill_sfx_paths"] = {skill_id: ninja_root.joinpath(*path) for skill_id, path in SKILL_SFX.items()}
        boss_root = ninja_root / "Actor" / "Boss"
        reserved_bosses = {item["name"] for item in BOSS_BY_MAP}
        all_boss_dirs = sorted([path for path in boss_root.iterdir() if path.is_dir()], key=lambda path: path.name.lower()) if boss_root.exists() else []
        mob_actor_dirs = [path for path in all_boss_dirs if path.name not in reserved_bosses and path.name not in EXCLUDED_MOB_ACTORS]
        enemy_pool_count = 3
        assets["map_enemy_pools"] = [[] for _ in range(enemy_pool_count)]
        for idx, actor_dir in enumerate(mob_actor_dirs):
            enemy_scale = MOB_ACTOR_SCALE_OVERRIDES.get(actor_dir.name, DEFAULT_MOB_ACTOR_SCALE)
            enemy_pack = load_actor_state_pack(actor_dir, enemy_scale)
            if enemy_pack is not None:
                assets["map_enemy_pools"][idx % enemy_pool_count].append(enemy_pack)
        assets["map_boss_pools"] = []
        for boss_info in BOSS_BY_MAP:
            pack = load_actor_state_pack(boss_root / boss_info["name"], boss_info["scale"])
            assets["map_boss_pools"].append([pack] if pack is not None else [])
        assets["map_enemy_pools"] = [[anim for anim in pool if anim] for pool in assets["map_enemy_pools"]]
        assets["map_boss_pools"] = [[anim for anim in pool if anim] for pool in assets["map_boss_pools"]]
        ui_theme = ninja_root / "Ui" / "Theme" / "Theme Wood"
        if ui_theme.exists():
            panel_path = ui_theme / "nine_path_panel.png"
            inner_path = ui_theme / "nine_path_panel_interior.png"
            if panel_path.exists() and inner_path.exists():
                assets["ui_panel"] = pygame.image.load(str(panel_path)).convert_alpha()
                assets["ui_panel_inner"] = pygame.image.load(str(inner_path)).convert_alpha()
        assets["ui_skill_icons"] = []
        for icon_path_parts in SKILL_ICONS:
            icon_path = ninja_root.joinpath(*icon_path_parts)
            if icon_path.exists():
                icon = pygame.image.load(str(icon_path)).convert_alpha()
                assets["ui_skill_icons"].append(pygame.transform.smoothscale(icon, (28, 28)))
            else:
                assets["ui_skill_icons"].append(None)
    texture_roots = {
        "transparent": particle_dir,
        "black": particle_black_dir,
    }
    for asset_key, (root_key, filename) in PARTICLE_TEXTURES.items():
        assets[asset_key] = load_particle_texture(texture_roots[root_key] / filename, root_key == "black")
    return assets


