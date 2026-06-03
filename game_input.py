import pygame

from game_config import HEIGHT, WIDTH
from game_utils import clamp


def build_keyboard_mouse_status(keys, mouse_pos, mouse_buttons, player, arena_w, arena_h):
    move = pygame.Vector2(
        (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0),
        (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0),
    )
    if move.length() > 0.001:
        move = move.normalize()

    cam_x_preview = clamp(player.x - WIDTH * 0.5, 0, arena_w - WIDTH)
    cam_y_preview = clamp(player.y - HEIGHT * 0.5, 0, arena_h - HEIGHT)
    mouse_world = pygame.Vector2(mouse_pos[0] + cam_x_preview, mouse_pos[1] + cam_y_preview)
    aim_mouse = mouse_world - player
    if aim_mouse.length() > 0.001:
        aim_mouse = aim_mouse.normalize()
    else:
        aim_mouse = pygame.Vector2(1, 0)

    kbm_fist = bool(mouse_buttons[2])
    kbm_clasp = bool(keys[pygame.K_c])
    status = {
        "move": move,
        "aim": aim_mouse,
        "right_seen": True,
        "fingers": 0,
        "fist": 1.0 if kbm_fist else 0.0,
        "clasp": 1.0 if kbm_clasp else 0.0,
        "index_pose": False,
        "right_pos": None,
    }
    for idx in range(1, 6):
        if keys[getattr(pygame, f"K_{idx}")]:
            status["fingers"] = idx
            break
    return status, kbm_fist, kbm_clasp
