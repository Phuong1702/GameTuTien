# Shared gameplay constants for Tien Lo Do Kiep 2D CV.

WIDTH, HEIGHT = 1280, 720
FPS = 60
ARENA_W, ARENA_H = 2200, 1600
LEVELS = ["Luyen Khi", "Truc Co", "Ket Dan", "Nguyen Anh", "Hoa Than", "Van Dinh", "Am Duong Hu Thuc"]
SKILLS = [
    ("Nhat Chi Linh Dan", 16, 34, 1.4, (120, 245, 255)),
    ("Nhi Chi Ket Gioi", 28, 25, 2.5, (120, 210, 255)),
    ("Tam Chi Kiem Quang", 24, 52, 1.0, (255, 255, 180)),
    ("Tu Chi Loi Anh", 36, 44, 2.1, (190, 170, 255)),
    ("Ngu Chi Dai Tran", 60, 68, 4.0, (255, 180, 245)),
    ("Luc Chi Luu Quang", 22, 46, 1.6, (120, 250, 225)),
    ("That Chi Loi Tran", 44, 58, 2.8, (190, 235, 255)),
    ("Bat Chi Van Tinh", 72, 80, 4.8, (255, 210, 170)),
]
SKILL_MANA = [14, 22, 18, 28, 40, 24, 36, 52]
SKILL_VFX = {
    1: {"cast_tex": "fx_flare", "proj_tex": "fx_star", "trail_tex": "fx_trace_a", "trail": (255, 245, 180), "scale": 0.42},
    2: {"cast_tex": "fx_ring", "proj_tex": "fx_magic_b", "trail_tex": "fx_smoke", "trail": (140, 255, 255), "scale": 0.50},
    3: {"cast_tex": "fx_slash", "proj_tex": "fx_slash", "trail_tex": "fx_trace_a", "trail": (255, 255, 220), "scale": 0.46},
    4: {"cast_tex": "fx_spark", "proj_tex": "fxb_spark7", "trail_tex": "fx_trace_b", "trail": (188, 170, 255), "scale": 0.58},
    5: {"cast_tex": "fxb_magic2", "proj_tex": "fxb_magic2", "trail_tex": "fxb_ring", "trail": (255, 180, 245), "scale": 0.82},
    6: {"cast_tex": "fx_twirl", "proj_tex": "fx_twirl", "trail_tex": "fx_trace_a", "trail": (130, 255, 230), "scale": 0.62},
    7: {"cast_tex": "fxb_twirl3", "proj_tex": "fxb_spark7", "trail_tex": "fx_trace_b", "trail": (180, 240, 255), "scale": 0.78},
    8: {"cast_tex": "fx_magic", "proj_tex": "fx_flare", "trail_tex": "fx_trace_b", "trail": (255, 210, 165), "scale": 0.95},
    0: {"cast_tex": "fx_flare", "proj_tex": "fx_star", "trail_tex": "fx_trace_a", "trail": (255, 225, 170), "scale": 0.34},
}
SKILL_LOCK_SECONDS = 1.8
SKILL_SWITCH_COOLDOWN = 0.35
EXP_PER_LEVEL = [60, 95, 140, 190, 250, 320, 420]
MAX_HP_BASE = 220
MAX_MANA_BASE = 720
HP_GAIN_PER_LEVEL = 75
MANA_GAIN_PER_LEVEL = 240
SHOP_RADIUS = 120
PILLS = {
    "blood": {"cost": 30, "hp": 35, "mana": 0},
    "spirit": {"cost": 28, "hp": 0, "mana": 32},
    "essence": {"cost": 46, "hp": 22, "mana": 24},
}
BASIC_ATTACK_CD = 0.26
BASIC_ATTACK_DAMAGE = 11
BASIC_ATTACK_RADIUS = 14
BASIC_ATTACK_SPEED = 720
CALIBRATION_SECONDS = 4.0
CLASP_ON_MARGIN = 0.07
CLASP_OFF_MARGIN = 0.03
FIST_ON_THRESHOLD = 0.74
FIST_OFF_THRESHOLD = 0.62
RIGHT_HAND_MIN_CONF = 0.45
AIM_SMOOTH = 0.18
AIM_ASSIST_ANGLE_DEG = 135
AIM_ASSIST_RANGE = 620
AIM_ASSIST_BLEND = 0.85
MELEE_RANGE = 100
MELEE_ARC_COS = 0.2
MELEE_DAMAGE_BASE = 30
SKILL_SELECT_HOLD = 0.22
SKILL_SELECT_STABLE_TIME = 0.30
SKILL_RELEASE_TIME = 0.14
SKILL_LOCK_EXTENDED = 2.8
CAST_FIST_HOLD = 0.10
MAP_KILL_TARGETS = [28, 36, 44]
MAP_ENEMY_BASE_COUNTS = [10, 13, 16]
MAP_ENEMY_WAVE_BONUS_MAX = 10
NORMAL_ENEMY_SKILL_MIN_RANGE = 170
NORMAL_ENEMY_SKILL_MAX_RANGE = 560
NORMAL_ENEMY_SKILL_COOLDOWN_MIN = 2.2
NORMAL_ENEMY_SKILL_COOLDOWN_MAX = 4.4
MAP_WORLD_SCALE = 1.75
STORY_CHAPTERS = [
    {
        "name": "Ngo Mon Son",
        "story": "Son mon nhap dao, thu linh thach va thanh loc ta linh.",
        "floor_ids": (48, 49, 50, 51, 52, 53),
        "wall_ids": (14, 15, 26, 27, 40, 57, 58, 59),
        "bg": (20, 24, 30),
    },
    {
        "name": "Linh Moc Lam",
        "story": "Co moc linh vien, yeu khi an duoi tan cay va da co.",
        "floor_ids": (42, 43, 48, 49, 52, 53),
        "wall_ids": (6, 7, 8, 9, 18, 19, 20, 32),
        "bg": (14, 24, 18),
    },
    {
        "name": "Co Dien Dia Cung",
        "story": "Dia cung co dien, tran phap cu va quai vat can duong.",
        "floor_ids": (50, 51, 52, 53, 42, 43),
        "wall_ids": (22, 23, 34, 35, 45, 46, 47, 57),
        "bg": (22, 18, 14),
    },
    {
        "name": "Luyen Dan That",
        "story": "Lo dan co khoi, mua linh dan va giu mach linh luc.",
        "floor_ids": (48, 50, 52, 53, 42, 43),
        "wall_ids": (14, 26, 34, 40, 45, 57, 58, 59),
        "bg": (22, 18, 22),
    },
    {
        "name": "Ma Vuc Tran Mon",
        "story": "Tran mon cuoi cung, boss dot pha va am duong hoi tu.",
        "floor_ids": (42, 43, 50, 51, 52, 53),
        "wall_ids": (22, 23, 34, 35, 45, 46, 47, 57),
        "bg": (12, 12, 18),
    },
]
REALM_AURAS = [
    (120, 220, 255),
    (130, 255, 170),
    (255, 220, 140),
    (175, 165, 255),
    (255, 170, 210),
    (140, 250, 250),
    (255, 120, 120),
]
TMX_FLIP_MASK = 0x1FFFFFFF



