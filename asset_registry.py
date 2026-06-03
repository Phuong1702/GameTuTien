MAP_FILES = [
    {"name": "Moc Mon Cuu Tho", "files": ["map1.png", "map1.jpg", "map1.jpeg"]},
    {"name": "Linh Hoa Dao Tam", "files": ["map2.png", "map2.jpg", "map2.jpeg"]},
    {"name": "Hai Nhai Co Lo", "files": ["map3.png", "map3.jpg", "map3.jpeg"]},
]

BOSS_BY_MAP = [
    {"map": 1, "name": "TenguRed", "scale": 3.0},
    {"map": 2, "name": "SquidGreen", "scale": 2.9},
    {"map": 3, "name": "DragonGreen", "scale": 1.35},
]

STAGE_LAYOUTS = [
    {
        "altar": (0.50, 0.38),
        "boss": (0.50, 0.50),
        "portal": (0.50, 0.36),
        "spawns": [(0.22, 0.62), (0.78, 0.62), (0.18, 0.38), (0.82, 0.38), (0.50, 0.78)],
    },
    {
        "altar": (0.50, 0.57),
        "boss": (0.50, 0.43),
        "portal": (0.50, 0.50),
        "spawns": [(0.25, 0.35), (0.75, 0.35), (0.25, 0.70), (0.75, 0.70), (0.50, 0.82)],
    },
    {
        "altar": (0.50, 0.34),
        "boss": (0.50, 0.54),
        "portal": (0.50, 0.34),
        "spawns": [(0.18, 0.45), (0.82, 0.45), (0.24, 0.74), (0.76, 0.74), (0.50, 0.82)],
    },
]

EXCLUDED_MOB_ACTORS = {
    "GiantBlueSamurai",
    "GiantRedSamurai",
    "GiantSlime",
    "GiantSlime2",
    "GiantSpirit",
    "GiantFlam",
}

MOB_ACTOR_SCALE_OVERRIDES = {
    "DragonBlue": 0.72,
    "DragonRed": 0.72,
    "DragonGreen": 0.72,
}

DEFAULT_MOB_ACTOR_SCALE = 1.95

NINJA_HERO = {
    "path": ("Actor", "Character", "NinjaGreen", "SeparateAnim", "Idle.png"),
    "frame": (16, 16),
    "scale": 2,
}

NINJA_NPCS = [
    {"name": "Truong lao", "path": ("Actor", "Character", "OldMan3", "SeparateAnim", "Idle.png"), "scale": 3},
    {"name": "Dan su", "path": ("Actor", "Character", "OldMan2", "SeparateAnim", "Idle.png"), "scale": 3},
    {"name": "Kiem tu", "path": ("Actor", "Character", "Monk2", "SeparateAnim", "Idle.png"), "scale": 3},
]

NINJA_SKILL_FX = [
    {"name": "Cut", "path": ("FX", "Attack", "Cut", "SpriteSheet.png")},
    {"name": "CutDouble", "path": ("FX", "Attack", "CutDouble", "SpriteSheet.png")},
    {"name": "CircularSlash", "path": ("FX", "Attack", "CircularSlash", "SpriteSheet.png")},
    {"name": "Claw", "path": ("FX", "Attack", "Claw", "SpriteSheet.png")},
    {"name": "ClawDouble", "path": ("FX", "Attack", "ClawDouble", "SpriteSheet.png")},
]

SKILL_ICONS = [
    ("Ui", "Skill Icon", "Spell", "Fireball.png"),
    ("Ui", "Skill Icon", "Spell", "RockSpike.png"),
    ("Ui", "Skill Icon", "Spell", "BookLight.png"),
    ("Ui", "Skill Icon", "Spell", "BookThunder.png"),
    ("Ui", "Skill Icon", "Spell", "Explosion.png"),
    ("Ui", "Skill Icon", "Spell", "WaterCanon.png"),
    ("Ui", "Skill Icon", "Spell", "OrbLight.png"),
    ("Ui", "Skill Icon", "Spell", "OrbFire.png"),
]

SKILL_SFX = {
    1: ("Audio", "Sounds", "Magic & Skill", "Magic1.wav"),
    2: ("Audio", "Sounds", "Magic & Skill", "Magic2.wav"),
    3: ("Audio", "Sounds", "Magic & Skill", "Magic3.wav"),
    4: ("Audio", "Sounds", "Magic & Skill", "Magic4.wav"),
    5: ("Audio", "Sounds", "Magic & Skill", "Magic5.wav"),
}

PARTICLE_TEXTURES = {
    "fx_ring": ("transparent", "circle_05.png"),
    "fx_magic": ("transparent", "magic_05.png"),
    "fx_magic_b": ("transparent", "magic_03.png"),
    "fx_flare": ("transparent", "flare_01.png"),
    "fx_trace": ("transparent", "trace_03.png"),
    "fx_trace_a": ("transparent", "trace_02.png"),
    "fx_trace_b": ("transparent", "trace_06.png"),
    "fx_smoke": ("transparent", "smoke_03.png"),
    "fx_star": ("transparent", "star_07.png"),
    "fx_spark": ("transparent", "spark_05.png"),
    "fx_twirl": ("transparent", "twirl_02.png"),
    "fx_slash": ("transparent", "slash_03.png"),
    "fxb_smoke": ("black", "smoke_04.png"),
    "fxb_ring": ("black", "circle_03.png"),
    "fxb_twirl": ("black", "twirl_02.png"),
    "fxb_twirl3": ("black", "twirl_03.png"),
    "fxb_magic2": ("black", "magic_02.png"),
    "fxb_spark7": ("black", "spark_07.png"),
}
