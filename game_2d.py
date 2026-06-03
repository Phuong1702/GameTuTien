import math
import random
import time
from pathlib import Path

import pygame
import cv2
import mediapipe as mp

from game_assets import load_assets
from game_audio import prepare_sounds
from game_combat import draw_projectile_vfx, get_enemy_frame, get_projectile_vfx_assets, spawn_boss_skill, spawn_enemy
from game_config import *
from game_cv import detect_cv
from game_entities import Projectile
from game_input import build_keyboard_mouse_status
from game_stage import choose_spawn_points, get_stage_layout
from game_utils import clamp, draw_ui_panel
from game_vfx import draw_effect, draw_player_aura


def get_effect_life_index(effect: list) -> int:
    return 3 if effect and effect[0] == "chain_lightning" else 2


def get_normal_spawn_count(map_idx: int, wave: int) -> int:
    base = MAP_ENEMY_BASE_COUNTS[map_idx % len(MAP_ENEMY_BASE_COUNTS)]
    return base + min(MAP_ENEMY_WAVE_BONUS_MAX, max(0, wave - 1) * 2)


def choose_control_mode(screen, clock, font, small_font):
    selected = 0
    options = [
        {
            "title": "1. Keyboard + Mouse",
            "subtitle": "Ban demo de test gameplay nhanh",
            "lines": ["WASD di chuyen", "Chuot ngam / trai danh / phai skill", "C thien-dot pha"],
        },
        {
            "title": "2. Computer Vision",
            "subtitle": "Muc tieu chinh: dieu khien bang cu chi",
            "lines": ["Tay trai di chuyen", "Tay phai ngam / ngon tay chon skill", "Nam tay cast / chap tay thien"],
        },
    ]
    cards = [
        pygame.Rect(WIDTH * 0.5 - 470, HEIGHT * 0.5 - 80, 420, 245),
        pygame.Rect(WIDTH * 0.5 + 50, HEIGHT * 0.5 - 80, 420, 245),
    ]
    title_font = pygame.font.SysFont("consolas", 36, bold=True)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = 1
                elif event.key == pygame.K_1:
                    return False
                elif event.key == pygame.K_2:
                    return True
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return selected == 1
            elif event.type == pygame.MOUSEMOTION:
                for idx, card in enumerate(cards):
                    if card.collidepoint(mouse_pos):
                        selected = idx
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for idx, card in enumerate(cards):
                    if card.collidepoint(mouse_pos):
                        return idx == 1

        screen.fill((8, 12, 20))
        pygame.draw.circle(screen, (26, 46, 58), (WIDTH // 2, HEIGHT // 2), 420)
        pygame.draw.circle(screen, (42, 65, 80), (WIDTH // 2, HEIGHT // 2), 280, 2)
        screen.blit(title_font.render("TIEN LO DO KIEP 2D", True, (255, 230, 150)), (WIDTH * 0.5 - 225, 125))
        screen.blit(small_font.render("Chon kieu dieu khien truoc khi vao game", True, (180, 220, 235)), (WIDTH * 0.5 - 185, 178))

        for idx, card in enumerate(cards):
            active = idx == selected
            bg = (22, 30, 42) if not active else (43, 39, 30)
            border = (100, 230, 255) if not active else (255, 210, 95)
            pygame.draw.rect(screen, bg, card, border_radius=16)
            pygame.draw.rect(screen, border, card, 3, border_radius=16)
            pygame.draw.rect(screen, (255, 255, 255, 30), card.inflate(-18, -18), 1, border_radius=12)
            screen.blit(font.render(options[idx]["title"], True, border), (card.x + 26, card.y + 28))
            screen.blit(small_font.render(options[idx]["subtitle"], True, (230, 230, 220)), (card.x + 26, card.y + 68))
            y = card.y + 115
            for line in options[idx]["lines"]:
                screen.blit(small_font.render("- " + line, True, (190, 215, 220)), (card.x + 34, y))
                y += 34

        hint = "Nhan 1/2, click chuot, hoac phim mui ten + Enter"
        screen.blit(small_font.render(hint, True, (185, 185, 185)), (WIDTH * 0.5 - 215, HEIGHT - 86))
        pygame.display.flip()
        clock.tick(FPS)


def main():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tien Lo Do Kiep 2D CV")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small_font = pygame.font.SysFont("consolas", 15)

    selected_cv_mode = choose_control_mode(screen, clock, font, small_font)
    if selected_cv_mode is None:
        pygame.quit()
        return 0

    assets = load_assets()
    sounds = prepare_sounds(Path(__file__).parent, assets)

    use_cv_controls = bool(selected_cv_mode)
    startup_status_text = ""
    cap = None
    hands = None
    pose = None
    if use_cv_controls:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            cap = None
            use_cv_controls = False
            startup_status_text = "Khong mo duoc webcam - tu dong chuyen sang Keyboard + Mouse"
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
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

    current_map_idx = 0
    maps = assets.get("maps", [])
    if maps:
        arena_w = float(maps[current_map_idx]["width_px"])
        arena_h = float(maps[current_map_idx]["height_px"])
        player = pygame.Vector2(arena_w * 0.5, arena_h * 0.5)
    else:
        arena_w = float(ARENA_W)
        arena_h = float(ARENA_H)
        player = pygame.Vector2(arena_w * 0.5, arena_h * 0.5)
    aim = pygame.Vector2(1, 0)
    level = 0
    exp = 0
    gold = 0
    wave = 1
    chapter_idx = 0
    current_walkable = maps[current_map_idx]["walkable"] if maps else None
    stage_layout = get_stage_layout(current_map_idx, arena_w, arena_h)
    player.update(stage_layout["altar"].x, stage_layout["altar"].y + 80)
    enemies = [spawn_enemy(player, wave, assets, arena_w, arena_h, current_walkable, False, current_map_idx, choose_spawn_points(stage_layout, player)) for _ in range(get_normal_spawn_count(current_map_idx, wave))]
    map_kills = [0 for _ in range(max(1, len(maps)))]
    map_boss_spawned = [False for _ in range(max(1, len(maps)))]
    map_boss_defeated = [False for _ in range(max(1, len(maps)))]
    kill_targets = [MAP_KILL_TARGETS[i % len(MAP_KILL_TARGETS)] for i in range(max(1, len(maps)))]
    projectiles = []
    effects = []
    selected_skill = 1
    skill_armed = 0.0
    skill_lock_timer = 0.0
    skill_switch_cooldown = 0.0
    prev_fist_casting = False
    cooldown = 0.0
    basic_cooldown = 0.0
    player_max_hp = MAX_HP_BASE
    player_hp = float(player_max_hp)
    player_max_mana = MAX_MANA_BASE
    player_mana = float(player_max_mana)
    player_hit_cooldown = 0.0
    meditation_time = 0.0
    status_text = startup_status_text
    status_time = 2.4 if startup_status_text else 0.0
    breakthrough_ready = False
    breakthrough_hold = 0.0
    cv_status = {}
    webcam_surface = None
    boss_wave = False
    map_transition_ready = False
    stage_phase = "farm"
    pending_purchase = ""
    select_hold = 0.0
    select_candidate = 0
    fist_hold = 0.0
    cast_fist_hold = 0.0
    calibrated = False
    calibration_timer = 0.0
    clasp_baseline = 0.0
    clasp_state = False
    fist_state = False
    right_seen_smooth = 0.0
    display_fingers = 0
    finger_stability = [0.0 for _ in range(6)]
    release_gate = False
    release_hold = 0.0
    hero_anim_timer = 0.0
    npc_anim_timer = [0.0, 0.5, 1.0]
    running = True

    kbm_fist = False
    prev_kbm_fist = False
    kbm_clasp = False
    while running:
        dt = clock.tick(FPS) / 1000.0
        trigger_skill_cast = False
        trigger_basic_attack = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_n and map_transition_ready and maps:
                    current_map_idx = (current_map_idx + 1) % len(maps)
                    chapter_idx = current_map_idx
                    arena_w = float(maps[current_map_idx]["width_px"])
                    arena_h = float(maps[current_map_idx]["height_px"])
                    current_walkable = maps[current_map_idx]["walkable"]
                    stage_layout = get_stage_layout(current_map_idx, arena_w, arena_h)
                    player.update(stage_layout["altar"].x, stage_layout["altar"].y + 80)
                    wave += 1
                    boss_wave = False
                    map_transition_ready = False
                    stage_phase = "farm"
                    normal_count = get_normal_spawn_count(current_map_idx, wave)
                    enemies = [spawn_enemy(player, wave, assets, arena_w, arena_h, current_walkable, False, current_map_idx, choose_spawn_points(stage_layout, player)) for _ in range(normal_count)]
                    status_text = f"Tien vao {maps[current_map_idx]['name']}"
                    status_time = 1.2
                elif event.key == pygame.K_SPACE:
                    skill_limit = 5 if use_cv_controls else len(SKILLS)
                    selected_skill = selected_skill % skill_limit + 1
                    skill_armed = 2.0
                elif event.key == pygame.K_j:
                    pending_purchase = "blood"
                elif event.key == pygame.K_k:
                    pending_purchase = "spirit"
                elif event.key == pygame.K_l:
                    pending_purchase = "essence"
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8):
                    pressed_skill = int(event.unicode)
                    if use_cv_controls and pressed_skill > 5:
                        continue
                    selected_skill = pressed_skill
                    if not use_cv_controls:
                        trigger_skill_cast = True
                    else:
                        skill_armed = SKILL_LOCK_EXTENDED
                        skill_lock_timer = SKILL_LOCK_EXTENDED
            elif (not use_cv_controls) and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    trigger_basic_attack = True
                elif event.button == 3:
                    trigger_skill_cast = True

        if use_cv_controls:
            ok, frame = cap.read() if cap is not None else (False, None)
            if ok:
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hand_result = hands.process(rgb)
                pose_result = pose.process(rgb)
                cv_status = detect_cv(hand_result, pose_result)
                if hand_result.multi_hand_landmarks:
                    draw_utils = mp.solutions.drawing_utils
                    landmark_style = draw_utils.DrawingSpec(color=(80, 255, 255), thickness=2, circle_radius=2)
                    connection_style = draw_utils.DrawingSpec(color=(80, 255, 120), thickness=2, circle_radius=1)
                    for hand_landmarks in hand_result.multi_hand_landmarks:
                        draw_utils.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp.solutions.hands.HAND_CONNECTIONS,
                            landmark_style,
                            connection_style,
                        )
                cv2.putText(frame, f"F:{cv_status.get('fingers', 0)} N:{cv_status.get('fist', 0.0):.2f}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (80, 255, 255), 2)
                preview = cv2.resize(frame, (260, 146), interpolation=cv2.INTER_AREA)
                preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                webcam_surface = pygame.image.frombuffer(preview.tobytes(), (preview.shape[1], preview.shape[0]), "RGB")
        else:
            keys = pygame.key.get_pressed()
            cv_status, kbm_fist, kbm_clasp = build_keyboard_mouse_status(
                keys,
                pygame.mouse.get_pos(),
                pygame.mouse.get_pressed(3),
                player,
                arena_w,
                arena_h,
            )

        move = cv_status.get("move", pygame.Vector2())
        if move.length() > 0.01:
            player += move * (230 + level * 12) * dt
        player.x = clamp(player.x, 50, arena_w - 50)
        player.y = clamp(player.y, 50, arena_h - 50)
        right_pos = cv_status.get("right_pos", None)
        if right_pos is not None:
            aim_from_pos = pygame.Vector2((right_pos.x - 0.5) * 1.8, (right_pos.y - 0.5) * 1.8)
            if aim_from_pos.length() > 0.08:
                aim = aim.lerp(aim_from_pos.normalize(), AIM_SMOOTH)
        elif cv_status.get("aim", pygame.Vector2()).length() > 0.01:
            aim = aim.lerp(cv_status["aim"], AIM_SMOOTH)
        if aim.length() > 0.001:
            aim = aim.normalize()
        right_seen_smooth = clamp(right_seen_smooth + (dt if cv_status.get("right_seen", False) else -dt * 1.4), 0.0, 1.0)
        nearest_enemy_dir = None
        nearest_dist = 1e9
        for enemy in enemies:
            to_enemy = enemy.pos - player
            distance = to_enemy.length()
            if 0.001 < distance < nearest_dist:
                nearest_dist = distance
                nearest_enemy_dir = to_enemy.normalize()
        if nearest_enemy_dir is not None:
            aim = aim.lerp(nearest_enemy_dir, 0.15).normalize()

        cooldown = max(0.0, cooldown - dt)
        basic_cooldown = max(0.0, basic_cooldown - dt)
        if use_cv_controls and skill_armed > 0.0:
            skill_lock_timer = max(skill_lock_timer, 0.0)
        else:
            skill_lock_timer = max(0.0, skill_lock_timer - dt)
        skill_switch_cooldown = max(0.0, skill_switch_cooldown - dt)
        player_hit_cooldown = max(0.0, player_hit_cooldown - dt)
        status_time = max(0.0, status_time - dt)

        if not calibrated:
            clasp_baseline += cv_status.get("clasp", 0.0) * dt
            calibration_timer += dt
            if calibration_timer >= CALIBRATION_SECONDS:
                clasp_baseline = clasp_baseline / max(0.001, calibration_timer)
                calibrated = True
        clasp_on_thr = clamp(clasp_baseline + CLASP_ON_MARGIN, 0.20, 0.82)
        clasp_off_thr = clamp(clasp_baseline + CLASP_OFF_MARGIN, 0.15, clasp_on_thr - 0.04)
        detected_fingers = cv_status.get("fingers", 0)
        index_select_pose = cv_status.get("index_pose", False)
        if detected_fingers <= 2 and index_select_pose:
            detected_fingers = 1
        display_fingers = detected_fingers
        selecting_allowed = skill_switch_cooldown <= 0.0 and not release_gate
        select_hand_open = cv_status.get("fist", 0.0) < 0.64 or index_select_pose
        select_signal = selecting_allowed and right_seen_smooth > 0.45 and select_hand_open and detected_fingers > 0
        for finger_id in range(1, 6):
            if select_signal and detected_fingers == finger_id:
                finger_stability[finger_id] = clamp(finger_stability[finger_id] + dt, 0.0, 2.2)
            else:
                finger_stability[finger_id] = clamp(finger_stability[finger_id] - dt * 2.2, 0.0, 2.2)

        stable_finger = 0
        stable_time = 0.0
        for finger_id in range(1, 6):
            if finger_stability[finger_id] > stable_time:
                stable_time = finger_stability[finger_id]
                stable_finger = finger_id

        if stable_finger > 0 and stable_time >= SKILL_SELECT_STABLE_TIME:
            if select_candidate != stable_finger:
                select_candidate = stable_finger
                select_hold = 0.0
            else:
                select_hold += dt
            if select_hold >= SKILL_SELECT_HOLD:
                selected_skill = stable_finger
                skill_armed = 999.0 if use_cv_controls else SKILL_LOCK_EXTENDED
                skill_lock_timer = 999.0 if use_cv_controls else SKILL_LOCK_EXTENDED
                select_candidate = 0
                select_hold = 0.0
                release_gate = False if use_cv_controls else True
                release_hold = 0.0
                for finger_id in range(1, 6):
                    finger_stability[finger_id] = 0.0
        else:
            select_candidate = 0
            select_hold = max(0.0, select_hold - dt * 3.0)
            if not use_cv_controls:
                skill_armed = max(0.0, skill_armed - dt)

        if release_gate:
            if detected_fingers == 0 and cv_status.get("fist", 0.0) < 0.40:
                release_hold += dt
            else:
                release_hold = max(0.0, release_hold - dt * 2.0)
            if release_hold >= SKILL_RELEASE_TIME:
                release_gate = False
                release_hold = 0.0

        clasp_score = cv_status.get("clasp", 0.0)
        if not clasp_state:
            clasp_state = clasp_score > clasp_on_thr
        else:
            clasp_state = clasp_score > clasp_off_thr
        clasp_on = clasp_state

        if clasp_on:
            meditation_time += dt
            player_mana = min(player_max_mana, player_mana + (22 + level * 2) * dt)
            if meditation_time > 1.2:
                player_hp = min(player_max_hp, player_hp + 6 * dt)
        else:
            meditation_time = max(0.0, meditation_time - dt * 2.0)

        fist_score = cv_status.get("fist", 0.0)
        if not fist_state:
            fist_state = fist_score > FIST_ON_THRESHOLD
        else:
            fist_state = fist_score > FIST_OFF_THRESHOLD
        fist_casting = fist_state and right_seen_smooth > RIGHT_HAND_MIN_CONF and not index_select_pose
        fist_edge = fist_casting and (not prev_fist_casting)
        if fist_casting:
            fist_hold += dt
            cast_fist_hold += dt
        else:
            fist_hold = 0.0
            cast_fist_hold = 0.0
        cast_trigger = fist_edge or (fist_casting and cast_fist_hold >= CAST_FIST_HOLD)
        if trigger_skill_cast:
            cast_trigger = True
            skill_armed = SKILL_LOCK_EXTENDED
            skill_lock_timer = SKILL_LOCK_EXTENDED
        cast_consumed = False
        if skill_armed > 0.0 and skill_lock_timer > 0.0 and cast_trigger and cooldown <= 0:
            name, radius, damage, cd, color = SKILLS[selected_skill - 1]
            mana_need = SKILL_MANA[selected_skill - 1]
            skill_vec = aim if aim.length() > 0.01 else pygame.Vector2(1, 0)
            aim_assist_target = None
            best_score = -1.0
            for enemy in enemies:
                to_enemy = enemy.pos - player
                dist = to_enemy.length()
                if dist <= 0.001 or dist > AIM_ASSIST_RANGE:
                    continue
                direction = to_enemy.normalize()
                dot = clamp(skill_vec.dot(direction), -1.0, 1.0)
                angle_deg = math.degrees(math.acos(dot))
                if angle_deg > AIM_ASSIST_ANGLE_DEG:
                    continue
                score = dot * 1.25 + (1.0 - dist / AIM_ASSIST_RANGE) * 0.55
                if score > best_score:
                    best_score = score
                    aim_assist_target = direction
            if aim_assist_target is not None:
                skill_vec = skill_vec.lerp(aim_assist_target, AIM_ASSIST_BLEND).normalize()
            if player_mana >= mana_need:
                if selected_skill == 1:
                    projectiles.append(Projectile(player, skill_vec * 760, damage + 8, radius - 2, 1.0, color, selected_skill))
                elif selected_skill == 2:
                    for angle in range(0, 360, 45):
                        vec = pygame.Vector2(math.cos(math.radians(angle)), math.sin(math.radians(angle)))
                        projectiles.append(Projectile(player, vec * 420, damage + 3, radius + 2, 0.75, color, selected_skill))
                elif selected_skill == 3:
                    for i in range(3):
                        spread = (i - 1) * 0.16
                        vec = skill_vec.rotate_rad(spread)
                        projectiles.append(Projectile(player, vec * 700, damage + 6, radius, 1.0, color, selected_skill))
                elif selected_skill == 4:
                    chain_targets = []
                    for enemy in sorted(enemies, key=lambda item: item.pos.distance_to(player)):
                        if enemy.pos.distance_to(player) <= 420:
                            chain_targets.append(enemy)
                        if len(chain_targets) >= 4:
                            break
                    if chain_targets:
                        for idx, enemy in enumerate(chain_targets):
                            enemy.hp -= damage + 8 - idx * 3
                            effects.append(["chain_lightning", player.copy(), enemy.pos.copy(), 0.24, 0.24, color])
                            effects.append(["hit", enemy.pos.copy(), 0.18, 54, 0, color])
                        for enemy in list(enemies):
                            if enemy.hp <= 0:
                                enemies.remove(enemy)
                                exp += 12 + wave * 3
                                gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                                map_kills[current_map_idx] += 1
                    else:
                        projectiles.append(Projectile(player, skill_vec * 700, damage, radius, 0.9, color, selected_skill))
                elif selected_skill == 5:
                    effects.append(["skill5_array", player.copy(), 3.0, 3.0, radius * 3.0, damage + 10, 0.05, 0])
                elif selected_skill == 6:
                    for angle in range(0, 360, 30):
                        vec = pygame.Vector2(1, 0).rotate(angle)
                        projectiles.append(Projectile(player, vec * 620, damage + 2, radius - 1, 0.75, color, selected_skill))
                elif selected_skill == 7:
                    chain_targets = sorted(enemies, key=lambda item: item.pos.distance_to(player))
                    hit_count = 0
                    for enemy in chain_targets:
                        if enemy.pos.distance_to(player) <= 560:
                            enemy.hp -= damage + 12 - hit_count * 2
                            hit_count += 1
                            effects.append(["enemy_attack", enemy.pos.copy(), 0.22, 54, 0, (190, 235, 255)])
                        if hit_count >= 7:
                            break
                    for enemy in list(enemies):
                        if enemy.hp <= 0:
                            enemies.remove(enemy)
                            exp += 12 + wave * 3
                            gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                            map_kills[current_map_idx] += 1
                elif selected_skill == 8:
                    for ring in (150, 230, 320):
                        for angle in range(0, 360, 24):
                            vec = pygame.Vector2(1, 0).rotate(angle)
                            spawn_pos = player + vec * ring
                            vel = vec.rotate(90) * (240 + ring * 0.2)
                            projectiles.append(Projectile(spawn_pos, vel, damage + 6, radius, 0.9, color, selected_skill))
                    for enemy in list(enemies):
                        if enemy.pos.distance_to(player) <= 340:
                            enemy.hp -= damage + 18
                            if enemy.hp <= 0:
                                enemies.remove(enemy)
                                exp += 12 + wave * 3
                                gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                                map_kills[current_map_idx] += 1
                sounds.get(f"skill{selected_skill}", sounds["skill5"]).play()
                if selected_skill != 5:
                    effects.append(["skillfx", player.copy(), 0.45, selected_skill])
                cooldown = cd
                skill_armed = 0.0
                skill_lock_timer = 0.0
                skill_switch_cooldown = SKILL_SWITCH_COOLDOWN
                cast_fist_hold = 0.0
                player_mana = max(0.0, player_mana - mana_need)
                cast_consumed = True
            else:
                melee_damage = MELEE_DAMAGE_BASE + level * 4
                for enemy in list(enemies):
                    to_enemy = enemy.pos - player
                    dist = to_enemy.length()
                    if dist <= 0.001 or dist > MELEE_RANGE:
                        continue
                    direction = to_enemy.normalize()
                    if skill_vec.dot(direction) < MELEE_ARC_COS:
                        continue
                    enemy.hp -= melee_damage
                    if enemy.hp <= 0:
                        enemies.remove(enemy)
                        exp += 12 + wave * 3
                        gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                        map_kills[current_map_idx] += 1
                sounds["hit"].play()
                status_text = "Het mana - trien khai khi tram gan"
                status_time = 0.9
                cooldown = 0.42
                skill_armed = 0.0
                skill_lock_timer = 0.0
                skill_switch_cooldown = SKILL_SWITCH_COOLDOWN
                cast_fist_hold = 0.0
                cast_consumed = True

        basic_trigger = fist_edge if use_cv_controls else trigger_basic_attack
        if basic_trigger and not cast_consumed and skill_armed <= 0.0 and basic_cooldown <= 0.0:
            basic_vec = aim if aim.length() > 0.01 else pygame.Vector2(1, 0)
            if player_mana <= 0.1:
                melee_damage = MELEE_DAMAGE_BASE + level * 3
                for enemy in list(enemies):
                    to_enemy = enemy.pos - player
                    dist = to_enemy.length()
                    if dist <= 0.001 or dist > MELEE_RANGE:
                        continue
                    direction = to_enemy.normalize()
                    if basic_vec.dot(direction) < MELEE_ARC_COS:
                        continue
                    enemy.hp -= melee_damage
                    if enemy.hp <= 0:
                        enemies.remove(enemy)
                        exp += 12 + wave * 3
                        gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                        map_kills[current_map_idx] += 1
                sounds["hit"].play()
                basic_cooldown = 0.32
            else:
                projectiles.append(Projectile(player, basic_vec * BASIC_ATTACK_SPEED, BASIC_ATTACK_DAMAGE, BASIC_ATTACK_RADIUS, 0.8, (255, 245, 180), 0))
                basic_cooldown = BASIC_ATTACK_CD
                sounds["hit"].play()
        prev_fist_casting = fist_casting
        prev_kbm_fist = kbm_fist

        exp_needed = EXP_PER_LEVEL[min(level, len(EXP_PER_LEVEL) - 1)]
        breakthrough_ready = exp >= exp_needed and level < len(LEVELS) - 1
        if breakthrough_ready and clasp_on:
            breakthrough_hold += dt
            if breakthrough_hold >= 1.05:
                level += 1
                exp = 0
                chapter_idx = current_map_idx % len(STORY_CHAPTERS)
                old_max_hp = player_max_hp
                old_max_mana = player_max_mana
                player_max_hp = MAX_HP_BASE + HP_GAIN_PER_LEVEL * level
                player_max_mana = MAX_MANA_BASE + MANA_GAIN_PER_LEVEL * level
                player_hp = min(player_max_hp, player_hp + (player_max_hp - old_max_hp) + 45)
                player_mana = min(player_max_mana, player_mana + (player_max_mana - old_max_mana) + 40)
                status_text = f"Dot pha {LEVELS[level]} | +{player_max_hp - old_max_hp} HP | +{player_max_mana - old_max_mana} Mana"
                status_time = 1.8
                breakthrough_hold = 0
                effects.append(["break", player.copy(), 1.8, 300, 0, REALM_AURAS[level]])
                sounds["break"].play()
        else:
            breakthrough_hold = max(0.0, breakthrough_hold - dt * 0.7)

        for enemy in enemies:
            direction = player - enemy.pos
            dist = direction.length()
            move_dir = direction.normalize() if dist > 0.001 else pygame.Vector2()
            enemy.attack_flash = max(0.0, enemy.attack_flash - dt * 2.8)
            enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - dt)
            if enemy.is_boss:
                enemy.passive_skill_cooldown = max(0.0, enemy.passive_skill_cooldown - dt)
            else:
                enemy.skill_cooldown = max(0.0, enemy.skill_cooldown - dt)
            enemy.state_time += dt
            if enemy.is_boss and enemy.attack_anim_timer <= 0.0 and enemy.passive_skill_cooldown <= 0.0:
                spawn_boss_skill(enemy, player, wave, projectiles, effects, sounds, "passive")
                hp_ratio_for_passive = enemy.hp / max(1, enemy.max_hp)
                enemy.passive_skill_cooldown = 2.25 if hp_ratio_for_passive > 0.5 else 1.55
            if (not enemy.is_boss) and enemy.attack_anim_timer <= 0.0 and enemy.skill_cooldown <= 0.0 and NORMAL_ENEMY_SKILL_MIN_RANGE <= dist <= NORMAL_ENEMY_SKILL_MAX_RANGE:
                shot_dir = move_dir if move_dir.length() > 0.001 else pygame.Vector2(1, 0)
                shot_damage = 7 + wave * 0.55
                shot_speed = 320 + min(90, wave * 10)
                if enemy.skill_style == "split" and wave >= 3:
                    for spread in (-0.16, 0.16):
                        projectiles.append(Projectile(enemy.pos, shot_dir.rotate_rad(spread) * (shot_speed * 0.94), shot_damage * 0.8, 10, 1.0, (170, 235, 255), 92, True))
                elif enemy.skill_style == "orb":
                    projectiles.append(Projectile(enemy.pos, shot_dir * (shot_speed * 0.82), shot_damage * 1.1, 14, 1.25, (160, 255, 210), 92, True))
                else:
                    projectiles.append(Projectile(enemy.pos, shot_dir * shot_speed, shot_damage, 10, 1.05, (255, 210, 145), 91, True))
                effects.append(["enemy_attack", enemy.pos.copy(), 0.18, 46, 0, (255, 210, 140)])
                enemy.attack_flash = 0.75
                enemy.skill_cooldown = random.uniform(NORMAL_ENEMY_SKILL_COOLDOWN_MIN, NORMAL_ENEMY_SKILL_COOLDOWN_MAX) + random.uniform(0.0, 0.55)
            if enemy.attack_anim_timer > 0.0:
                enemy.attack_anim_timer = max(0.0, enemy.attack_anim_timer - dt)
                enemy.state = "attack"
                progress = 1.0 - (enemy.attack_anim_timer / max(0.001, enemy.attack_anim_total))
                # Keep attack readable by adding forward motion during the first part of the swing.
                if progress < 0.65 and dist > 6:
                    lunge_speed = enemy.speed * (0.62 if enemy.is_boss else 0.78)
                    enemy.pos += move_dir * lunge_speed * dt
                if (not enemy.attack_damage_done) and progress >= 0.5 and dist < enemy.attack_range + 14 and player_hit_cooldown <= 0:
                    incoming = (13 + wave * 1.05) * enemy.attack_damage_mul
                    player_hp = max(0.0, player_hp - incoming)
                    player_hit_cooldown = 0.6
                    enemy.attack_flash = 1.0
                    enemy.attack_damage_done = True
                    spawn_boss_skill(enemy, player, wave, projectiles, effects, sounds)
                    effects.append(["hit", player.copy(), 0.22, 80, 0, (255, 90, 90)])
                    status_text = f"Bi trung don! -{int(incoming)} HP"
                    status_time = 0.9
                if enemy.attack_anim_timer <= 0.0:
                    enemy.attack_damage_done = False
            elif dist > enemy.attack_range * 0.92:
                enemy.state = "walk"
                if dist > 4:
                    enemy.pos += move_dir * enemy.speed * dt
            else:
                enemy.state = "idle"
                if enemy.attack_cooldown <= 0.0:
                    if enemy.is_boss:
                        boss_hp_ratio = enemy.hp / max(1, enemy.max_hp)
                        enemy.attack_anim_total = 0.52 if boss_hp_ratio > 0.5 else 0.46
                    else:
                        enemy.attack_anim_total = 0.30
                    enemy.attack_anim_timer = enemy.attack_anim_total
                    if enemy.is_boss:
                        boss_hp_ratio = enemy.hp / max(1, enemy.max_hp)
                        enemy.attack_cooldown = 1.05 if boss_hp_ratio > 0.5 else 0.76
                    else:
                        enemy.attack_cooldown = 0.55
                    enemy.attack_damage_done = False
                    enemy.state = "attack"
                    if enemy.is_boss:
                        effects.append(["enemy_attack", enemy.pos.copy(), 0.22, 64, 0, (255, 170, 120)])
            if enemy.pos.distance_to(player) < 36:
                enemy.pos -= move_dir * 80 * dt if dist > 0 else pygame.Vector2()

        for projectile in list(projectiles):
            projectile.pos += projectile.vel * dt
            projectile.life -= dt
            if projectile.life <= 0:
                projectiles.remove(projectile)
                continue
            if projectile.hostile:
                if projectile.pos.distance_to(player) < projectile.radius + 18 and player_hit_cooldown <= 0:
                    player_hp = max(0.0, player_hp - projectile.damage)
                    player_hit_cooldown = 0.42
                    effects.append(["hit", player.copy(), 0.20, 66, 0, (255, 120, 120)])
                    status_text = f"Bi trung skill! -{int(projectile.damage)} HP"
                    status_time = 0.7
                    if projectile in projectiles:
                        projectiles.remove(projectile)
                continue
            for enemy in list(enemies):
                if projectile.pos.distance_to(enemy.pos) < projectile.radius + 20:
                    if enemy in projectile.hit_targets:
                        continue
                    projectile.hit_targets.add(enemy)
                    enemy.hp -= projectile.damage
                    enemy.hit_flash = 0.12
                    sounds["hit"].play()
                    if projectile.skill != 4 and projectile in projectiles:
                        projectiles.remove(projectile)
                    if enemy.hp <= 0:
                        enemies.remove(enemy)
                        exp += 12 + wave * 3
                        gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                        map_kills[current_map_idx] += 1
                    break

        for effect in list(effects):
            if effect[0] == "skill5_array":
                center = effect[1]
                radius = effect[4]
                damage = effect[5]
                effect[6] -= dt
                if effect[6] <= 0.0:
                    effect[6] = 0.30
                    tick_index = int(effect[7])
                    effect[7] = tick_index + 1
                    array_points = [center.copy()]
                    for point_idx in range(5):
                        angle = -90 + point_idx * 72 + tick_index * 18
                        array_points.append(center + pygame.Vector2(1, 0).rotate(angle) * radius * 0.62)
                    strike_points = [
                        array_points[tick_index % len(array_points)],
                        array_points[(tick_index * 2 + 2) % len(array_points)],
                    ]
                    if tick_index % 3 == 0:
                        strike_points.append(array_points[(tick_index + 4) % len(array_points)])
                    for strike_pos in strike_points:
                        effects.append(["black_lightning", strike_pos.copy(), 0.28, 0.28, 98])
                        for enemy in enemies:
                            if enemy.pos.distance_to(strike_pos) <= 72:
                                enemy.hp -= damage
                    for enemy in list(enemies):
                        if enemy.hp <= 0:
                            enemies.remove(enemy)
                            exp += 12 + wave * 3
                            gold += 7 + wave * 2 + (18 if enemy.is_boss else 0)
                            map_kills[current_map_idx] += 1
            life_index = get_effect_life_index(effect)
            effect[life_index] -= dt
            if effect[life_index] <= 0:
                effects.remove(effect)

        if (not enemies) and (not map_transition_ready):
            target_kills = kill_targets[current_map_idx]
            if (not map_boss_spawned[current_map_idx]) and map_kills[current_map_idx] >= target_kills:
                map_boss_spawned[current_map_idx] = True
                boss_wave = True
                stage_phase = "boss"
                boss = spawn_enemy(player, wave + 2, assets, arena_w, arena_h, current_walkable, True, current_map_idx, [stage_layout["boss"]])
                boss.pos.update(stage_layout["boss"])
                enemies = [boss]
                boss_name = enemies[0].name if enemies else "Boss"
                status_text = f"{boss_name} xuat hien tai {maps[current_map_idx]['name']}!"
                status_time = 1.4
            elif map_boss_spawned[current_map_idx] and (not map_boss_defeated[current_map_idx]):
                map_boss_defeated[current_map_idx] = True
                map_transition_ready = True
                stage_phase = "clear"
                status_text = f"Da thu phuc {maps[current_map_idx]['name']} - nhan N de sang man"
                status_time = 1.8
                boss_wave = False
            else:
                wave += 1
                boss_wave = False
                stage_phase = "farm"
                normal_count = get_normal_spawn_count(current_map_idx, wave)
                enemies = [spawn_enemy(player, wave, assets, arena_w, arena_h, current_walkable, False, current_map_idx, choose_spawn_points(stage_layout, player)) for _ in range(normal_count)]

        hero_anim_timer += dt * 8.0
        for idx in range(len(npc_anim_timer)):
            npc_anim_timer[idx] += dt * (6.0 + idx)
        for enemy in enemies:
            state_mul = 1.35 if enemy.state == "attack" else (0.65 if enemy.state == "idle" else 1.0)
            enemy.anim_timer += dt * enemy.anim_speed * state_mul

        stage_layout = get_stage_layout(current_map_idx, arena_w, arena_h)
        altar_pos = stage_layout["altar"]
        near_altar = player.distance_to(altar_pos) < SHOP_RADIUS
        if pending_purchase:
            pill = PILLS[pending_purchase]
            if not near_altar:
                status_text = "Can dung gan dan lo de mua dan duoc"
                status_time = 1.1
            elif gold < pill["cost"]:
                status_text = "Khong du linh thach"
                status_time = 1.1
            else:
                gold -= pill["cost"]
                player_hp = min(player_max_hp, player_hp + pill["hp"])
                player_mana = min(player_max_mana, player_mana + pill["mana"])
                status_text = f"Mua {pending_purchase} pill thanh cong"
                status_time = 1.1
            pending_purchase = ""

        if player_hp <= 0:
            status_text = "Da bi ha guc - hoi sinh va mat mot phan vang"
            status_time = 2.0
            player_hp = player_max_hp * 0.7
            player_mana = player_max_mana * 0.6
            gold = max(0, int(gold * 0.75))
            player.update(arena_w / 2, arena_h / 2)

        camera = pygame.Vector2(player.x - WIDTH / 2, player.y - HEIGHT / 2)
        camera.x = clamp(camera.x, 0, max(0.0, arena_w - WIDTH))
        camera.y = clamp(camera.y, 0, max(0.0, arena_h - HEIGHT))

        chapter = STORY_CHAPTERS[chapter_idx]
        screen.fill(chapter["bg"])
        shake_x = 0.0
        shake_y = 0.0
        if maps:
            map_surface = maps[current_map_idx]["surface"]
            screen.blit(map_surface, (-camera.x, -camera.y))
        else:
            tile_size = 48
            start_x = int(camera.x // tile_size) - 1
            start_y = int(camera.y // tile_size) - 1
            for yy in range(start_y, start_y + HEIGHT // tile_size + 3):
                for xx in range(start_x, start_x + WIDTH // tile_size + 3):
                    floor_tiles = assets["floors_by_chapter"][chapter_idx]
                    tile = floor_tiles[(xx * 7 + yy * 5) % len(floor_tiles)]
                    screen.blit(tile, (xx * tile_size - camera.x, yy * tile_size - camera.y))

        if not maps:
            decor_tiles = assets.get("decor_by_chapter", [[]])[chapter_idx]
            relic_tiles = assets.get("relic_by_chapter", [[]])[chapter_idx]
            for i in range(130):
                x = (i * 131 + chapter_idx * 219) % arena_w
                y = (i * 89 + chapter_idx * 151) % arena_h
                tile_pool = relic_tiles if (i + chapter_idx) % 9 == 0 and relic_tiles else decor_tiles
                if not tile_pool:
                    continue
                tile = tile_pool[(i * 3 + chapter_idx) % len(tile_pool)]
                screen.blit(tile, (x - camera.x, y - camera.y))

            wall_tiles = assets["walls_by_chapter"][chapter_idx]
            for i in range(90):
                x = (i * 173 + chapter_idx * 47) % arena_w
                y = (i * 97 + chapter_idx * 133) % arena_h
                deco = wall_tiles[i % len(wall_tiles)]
                screen.blit(deco, (x - camera.x, y - camera.y))

            for i, tree in enumerate(assets.get("trees", [])):
                for repeat in range(7):
                    idx = i * 7 + repeat
                    x = (idx * 281 + chapter_idx * 193) % arena_w
                    y = (idx * 167 + chapter_idx * 241) % arena_h
                    if player.distance_to(pygame.Vector2(x, y)) < 140:
                        continue
                    screen.blit(tree, (x - camera.x - tree.get_width() // 2, y - camera.y - tree.get_height() + 22))

        landmarks = assets.get("landmarks_by_chapter", [[]])[chapter_idx]
        landmark_offsets = [pygame.Vector2(-132, -56), pygame.Vector2(138, -46)]
        for idx, landmark in enumerate(landmarks[:2]):
            pos = altar_pos + landmark_offsets[idx]
            screen.blit(landmark, (pos.x - camera.x - landmark.get_width() // 2, pos.y - camera.y - landmark.get_height() // 2))

        altar_sprite = assets["altar"]
        screen.blit(altar_sprite, (altar_pos.x - camera.x - altar_sprite.get_width() // 2, altar_pos.y - camera.y - altar_sprite.get_height() // 2))
        if near_altar:
            pygame.draw.circle(screen, (255, 220, 120), (int(altar_pos.x - camera.x), int(altar_pos.y - camera.y)), int(SHOP_RADIUS), 2)
        if stage_phase == "boss":
            boss_center = stage_layout["boss"] - camera
            boss_radius = int(stage_layout["boss_radius"])
            arena = pygame.Surface((boss_radius * 2 + 16, boss_radius * 2 + 16), pygame.SRCALPHA)
            pulse_alpha = int(42 + 22 * math.sin(time.time() * 5.0))
            pygame.draw.circle(arena, (255, 95, 80, max(10, pulse_alpha)), (boss_radius + 8, boss_radius + 8), boss_radius, 0)
            pygame.draw.circle(arena, (255, 190, 110, 150), (boss_radius + 8, boss_radius + 8), boss_radius, 3)
            pygame.draw.circle(arena, (255, 235, 150, 110), (boss_radius + 8, boss_radius + 8), max(18, boss_radius - 28), 1)
            screen.blit(arena, (boss_center.x - boss_radius - 8, boss_center.y - boss_radius - 8))
        if map_transition_ready:
            portal_pos = stage_layout["portal"] - camera
            portal = pygame.transform.rotozoom(assets["fx_magic"], time.time() * 70, 0.72 + 0.06 * math.sin(time.time() * 4.0))
            portal.set_alpha(170)
            screen.blit(portal, (portal_pos.x - portal.get_width() // 2, portal_pos.y - portal.get_height() // 2))
            portal_label = small_font.render("CONG DICH CHUYEN", True, (255, 245, 180))
            screen.blit(portal_label, (portal_pos.x - portal_label.get_width() // 2, portal_pos.y - 58))

        hero_tick = int(hero_anim_timer)
        npc_names = ["Truong lao", "Dan su", "Kiem tu"]
        npc_offsets = [pygame.Vector2(-86, 86), pygame.Vector2(0, 104), pygame.Vector2(88, 82)]
        npc_anims = assets.get("npc_anims", [])
        for idx, npc in enumerate(assets.get("npcs", [])[:3]):
            if idx < len(npc_anims) and npc_anims[idx]:
                npc = npc_anims[idx][int(npc_anim_timer[idx]) % len(npc_anims[idx])]
            pos = altar_pos + npc_offsets[idx]
            screen.blit(npc, (pos.x - camera.x - npc.get_width() // 2, pos.y - camera.y - npc.get_height() // 2))
            label = small_font.render(npc_names[idx], True, (245, 230, 160))
            screen.blit(label, (pos.x - camera.x - label.get_width() // 2, pos.y - camera.y - 38))

        for effect in effects:
            draw_effect(screen, camera, assets, effect)

        for projectile in projectiles:
            draw_projectile_vfx(screen, camera, assets, projectile)

        for enemy in enemies:
            pos = enemy.pos - camera
            shadow = pygame.Surface((36, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 95), shadow.get_rect())
            screen.blit(shadow, (pos.x - 18, pos.y + 14))
            enemy_sprite = get_enemy_frame(enemy)
            if enemy.is_boss:
                screen.blit(enemy_sprite, (pos.x - enemy_sprite.get_width() // 2, pos.y - enemy_sprite.get_height() // 2 - 8))
                if enemy.attack_flash > 0.0:
                    slash = pygame.transform.rotozoom(assets["fx_slash"], random.uniform(-40, 40), 0.65)
                    slash.set_alpha(int(180 * enemy.attack_flash))
                    screen.blit(slash, (pos.x - slash.get_width() // 2, pos.y - slash.get_height() // 2))
            else:
                screen.blit(enemy_sprite, (pos.x - enemy_sprite.get_width() // 2, pos.y - enemy_sprite.get_height() // 2))
                if enemy.attack_flash > 0.0:
                    spark = pygame.transform.rotozoom(assets["fx_spark"], random.uniform(-25, 25), 0.36)
                    spark.set_alpha(int(170 * enemy.attack_flash))
                    screen.blit(spark, (pos.x - spark.get_width() // 2, pos.y - spark.get_height() // 2))
            hp_ratio = clamp(enemy.hp / max(1, enemy.max_hp), 0, 1)
            pygame.draw.rect(screen, (50, 20, 30), (pos.x - 22, pos.y - 32, 44, 5))
            bar_col = (255, 120, 80) if enemy.is_boss else (230, 70, 90)
            pygame.draw.rect(screen, bar_col, (pos.x - 22, pos.y - 32, int(44 * hp_ratio), 5))

        ppos = player - camera
        pshadow = pygame.Surface((40, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(pshadow, (0, 0, 0, 110), pshadow.get_rect())
        screen.blit(pshadow, (ppos.x - 20, ppos.y + 16))
        hero_anim = assets.get("hero_anim", [])
        hero_sprite = hero_anim[hero_tick % len(hero_anim)] if hero_anim else assets["hero"]
        draw_player_aura(screen, camera, assets, player, level, clasp_on, breakthrough_ready)
        screen.blit(hero_sprite, (ppos.x - hero_sprite.get_width() // 2, ppos.y - hero_sprite.get_height() // 2))
        pygame.draw.circle(screen, (80, 255, 225), ppos, 20, 2)
        pygame.draw.circle(screen, (240, 255, 245), ppos, 12, 1)
        pygame.draw.line(screen, (255, 240, 120), ppos, ppos + aim * 70, 4)
        hero_name = small_font.render("TU SI", True, (210, 255, 240))
        hero_name_bg = pygame.Rect(int(ppos.x - hero_name.get_width() // 2 - 6), int(ppos.y - 44), hero_name.get_width() + 12, 18)
        pygame.draw.rect(screen, (8, 24, 26, 180), hero_name_bg)
        pygame.draw.rect(screen, (80, 255, 225), hero_name_bg, 1)
        screen.blit(hero_name, (hero_name_bg.x + 6, hero_name_bg.y + 2))
        if breakthrough_ready:
            hold_ratio = clamp(breakthrough_hold / 1.05, 0.0, 1.0)
            pygame.draw.circle(screen, (255, 235, 160), ppos, 56, 2)
            pygame.draw.arc(screen, (120, 255, 190), (ppos.x - 56, ppos.y - 56, 112, 112), -math.pi / 2, -math.pi / 2 + math.tau * hold_ratio, 5)

        panel_l = pygame.Rect(18, 16, 520, 190)
        draw_ui_panel(screen, panel_l, assets, (100, 210, 255), 235)
        screen.blit(font.render(f"Canh gioi: {LEVELS[level]}", True, (245, 235, 140)), (34, 30))
        boss_text = " | BOSS WAVE" if boss_wave else ""
        quota_text = f"Kills {map_kills[current_map_idx]}/{kill_targets[current_map_idx]}"
        screen.blit(small_font.render(f"Wave {wave}{boss_text} | Quai {len(enemies)} | {quota_text}", True, (205, 245, 255)), (34, 64))
        exp_ratio = clamp(exp / exp_needed, 0, 1)
        hp_ratio = clamp(player_hp / max(1, player_max_hp), 0, 1)
        mana_ratio = clamp(player_mana / max(1, player_max_mana), 0, 1)
        shimmer = 0.5 + 0.5 * math.sin(time.time() * 4.0)

        pygame.draw.rect(screen, (38, 40, 54), (34, 90, 460, 11))
        pygame.draw.rect(screen, (120, 255, 170), (34, 90, int(460 * exp_ratio), 11))
        pygame.draw.rect(screen, (200, 255, 220), (34, 90, 460, 11), 1)

        pygame.draw.rect(screen, (38, 40, 54), (34, 109, 224, 10))
        pygame.draw.rect(screen, (255, 110, 110), (34, 109, int(224 * hp_ratio), 10))
        pygame.draw.rect(screen, (255, 180, 180), (34, 109, 224, 10), 1)

        pygame.draw.rect(screen, (38, 40, 54), (270, 109, 224, 10))
        pygame.draw.rect(screen, (110, 180, 255), (270, 109, int(224 * mana_ratio), 10))
        pygame.draw.rect(screen, (170, 220, 255), (270, 109, 224, 10), 1)

        if stage_phase == "boss":
            boss_glow = pygame.Surface((460, 8), pygame.SRCALPHA)
            pygame.draw.rect(boss_glow, (255, 100, 100, int(70 + 50 * shimmer)), (0, 0, 460, 8))
            screen.blit(boss_glow, (34, 124))
        if map_transition_ready:
            ready_text = "MAN HOAN TAT: N de qua man tiep theo"
        elif stage_phase == "boss":
            ready_text = "BOSS WAVE: ha boss de mo khoa man"
        else:
            ready_text = "CO THE DOT PHA: chap 2 tay!" if breakthrough_ready else "Farm quai de du EXP"
        ready_col = (255, 220, 120) if (breakthrough_ready or map_transition_ready or stage_phase == "boss") else (180, 190, 205)
        screen.blit(small_font.render(ready_text, True, ready_col), (34, 136))
        if use_cv_controls:
            left_ok = "OK" if cv_status.get("left_seen", False) else "--"
            right_ok = "OK" if cv_status.get("right_seen", False) else "--"
            screen.blit(small_font.render(f"CV raw | tay trai {left_ok} | tay phai {right_ok}", True, (180, 220, 255)), (34, 154))
        elif not calibrated:
            cali_ratio = clamp(calibration_timer / CALIBRATION_SECONDS, 0.0, 1.0)
            screen.blit(small_font.render(f"Dang canh chinh CV... {int(cali_ratio * 100)}%", True, (180, 220, 255)), (34, 154))
        else:
            screen.blit(small_font.render(f"CV clasp ON/OFF: {clasp_on_thr:.2f}/{clasp_off_thr:.2f}", True, (180, 220, 255)), (34, 154))
        map_label = f"Map {current_map_idx + 1}/{len(maps)}" if maps else "Map procedural"
        screen.blit(small_font.render(f"Chuong: {chapter['name']} | {map_label}", True, (255, 235, 160)), (34, 172))
        screen.blit(small_font.render(f"HP {int(player_hp)}/{player_max_hp}  MP {int(player_mana)}/{player_max_mana}  Linh thach {gold}  EXP {exp}/{exp_needed}", True, (255, 235, 160)), (34, 190))

        panel_r = pygame.Rect(WIDTH - 458, 16, 440, 168)
        draw_ui_panel(screen, panel_r, assets, (180, 150, 255), 235)
        skill_name = SKILLS[selected_skill - 1][0]
        icon_list = assets.get("ui_skill_icons", [])
        icon = icon_list[selected_skill - 1] if selected_skill - 1 < len(icon_list) else None
        if icon is not None:
            screen.blit(icon, (WIDTH - 440, 28))
            screen.blit(font.render(f"Skill {selected_skill}: {skill_name}", True, (255, 235, 150)), (WIDTH - 404, 30))
        else:
            screen.blit(font.render(f"Skill {selected_skill}: {skill_name}", True, (255, 235, 150)), (WIDTH - 440, 30))
        if use_cv_controls:
            control_line_1 = "Move: tay trai | Aim: tay phai"
            control_line_2 = "1-5 ngon chon | Nam tay cast/danh"
        else:
            control_line_1 = "Move: WASD | Aim: chuot"
            control_line_2 = "Click trai danh | phai skill | 1-8 cast"
        screen.blit(small_font.render(control_line_1, True, (205, 245, 255)), (WIDTH - 440, 64))
        screen.blit(small_font.render(control_line_2, True, (205, 245, 255)), (WIDTH - 440, 84))
        lock_txt = "ARM" if use_cv_controls and skill_armed > 0.0 else ("LOCK" if skill_lock_timer > 0.0 else "FREE")
        lock_value = 0.0 if use_cv_controls and skill_armed > 0.0 else skill_lock_timer
        if use_cv_controls:
            clasp_dbg = cv_status.get("clasp", 0.0)
            status_line = f"RAW | F {display_fingers} | Nam {cv_status.get('fist', 0):.2f} | Chap {clasp_dbg:.2f} | {lock_txt} {lock_value:.1f}s"
        else:
            status_line = f"F {display_fingers} | N {cv_status.get('fist', 0):.2f} | {lock_txt} {lock_value:.1f}s"
        screen.blit(small_font.render(status_line, True, (160, 255, 180)), (WIDTH - 440, 106))
        pygame.draw.rect(screen, (38, 40, 54), (WIDTH - 440, 126, 200, 10))
        pygame.draw.rect(screen, (255, 210, 130), (WIDTH - 440, 126, int(200 * clamp(1.0 - cooldown / max(0.001, SKILLS[selected_skill - 1][3]), 0.0, 1.0)), 10))
        pygame.draw.rect(screen, (255, 230, 170), (WIDTH - 440, 126, 200, 10), 1)
        pygame.draw.rect(screen, (38, 40, 54), (WIDTH - 228, 126, 200, 10))
        pygame.draw.rect(screen, (170, 220, 255), (WIDTH - 228, 126, int(200 * clamp(1.0 - basic_cooldown / max(0.001, BASIC_ATTACK_CD), 0.0, 1.0)), 10))
        pygame.draw.rect(screen, (220, 240, 255), (WIDTH - 228, 126, 200, 10), 1)
        shop_text = "Shop: J HP | K Mana | L Hybrid"
        shop_col = (255, 220, 120) if near_altar else (170, 180, 195)
        screen.blit(small_font.render(shop_text, True, shop_col), (WIDTH - 440, 146))

        if status_time > 0.0:
            status_surf = font.render(status_text, True, (255, 245, 170))
            box = pygame.Rect(WIDTH // 2 - status_surf.get_width() // 2 - 16, HEIGHT - 86, status_surf.get_width() + 32, 44)
            draw_ui_panel(screen, box, assets, (255, 210, 120), 230)
            screen.blit(status_surf, (box.x + 14, box.y + 10))

        if boss_wave:
            warning_rect = pygame.Rect(WIDTH // 2 - 170, 12, 340, 34)
            draw_ui_panel(screen, warning_rect, assets, (255, 120, 120), 215)
            screen.blit(font.render("BOSS BATTLE", True, (255, 225, 190)), (warning_rect.x + 90, warning_rect.y + 6))
            boss_enemy = next((enemy for enemy in enemies if enemy.is_boss), None)
            if boss_enemy is not None:
                boss_ratio = clamp(boss_enemy.hp / max(1, boss_enemy.max_hp), 0.0, 1.0)
                boss_bar = pygame.Rect(WIDTH // 2 - 280, 52, 560, 28)
                draw_ui_panel(screen, boss_bar, assets, (255, 140, 100), 205)
                pygame.draw.rect(screen, (44, 18, 22), (boss_bar.x + 12, boss_bar.y + 10, boss_bar.width - 24, 8))
                pygame.draw.rect(screen, (255, 90, 80), (boss_bar.x + 12, boss_bar.y + 10, int((boss_bar.width - 24) * boss_ratio), 8))
                pygame.draw.rect(screen, (255, 220, 150), (boss_bar.x + 12, boss_bar.y + 10, boss_bar.width - 24, 8), 1)
                boss_name = small_font.render(f"{boss_enemy.name}  {int(boss_enemy.hp)}/{boss_enemy.max_hp}", True, (255, 235, 180))
                screen.blit(boss_name, (boss_bar.centerx - boss_name.get_width() // 2, boss_bar.y + 5))

        if webcam_surface is not None:
            preview_w = 260
            preview_h = 146
            preview_x = WIDTH - 286
            preview_y = HEIGHT - 174
            screen.blit(webcam_surface, (preview_x, preview_y))
            pygame.draw.rect(screen, (130, 210, 255), (preview_x, preview_y, preview_w, preview_h), 2)
            screen.blit(small_font.render("CV Preview", True, (220, 240, 255)), (preview_x + 4, preview_y - 20))
        elif use_cv_controls:
            cv_box = pygame.Rect(WIDTH - 286, HEIGHT - 174, 260, 146)
            draw_ui_panel(screen, cv_box, assets, (255, 120, 120), 210)
            screen.blit(small_font.render("Dang cho webcam...", True, (255, 220, 180)), (cv_box.x + 18, cv_box.y + 58))

        pygame.display.flip()

    if cap is not None:
        cap.release()
    if hands is not None:
        hands.close()
    if pose is not None:
        pose.close()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
