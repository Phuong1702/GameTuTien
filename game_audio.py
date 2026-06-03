from pathlib import Path

import pygame

from game_utils import create_tone


def prepare_sounds(base_dir: Path, assets: dict) -> dict:
    sound_dir = base_dir / "assets" / "audio_2d"
    sound_dir.mkdir(exist_ok=True)
    sound_paths = {
        "hit": sound_dir / "hit.wav",
        "break": sound_dir / "break.wav",
        "ambient": sound_dir / "ambient.wav",
        "skill1": sound_dir / "skill1.wav",
        "skill2": sound_dir / "skill2.wav",
        "skill3": sound_dir / "skill3.wav",
        "skill4": sound_dir / "skill4.wav",
        "skill5": sound_dir / "skill5.wav",
        "skill6": sound_dir / "skill6.wav",
        "skill7": sound_dir / "skill7.wav",
        "skill8": sound_dir / "skill8.wav",
    }
    create_tone(sound_paths["hit"], [180, 95], 0.13, 0.55, -80)
    create_tone(sound_paths["break"], [146, 220, 440], 0.9, 0.9, 260)
    create_tone(sound_paths["ambient"], [73, 110, 146, 220], 10.0, 0.18, 18)
    create_tone(sound_paths["skill1"], [520, 880], 0.26, 0.8, 420)
    create_tone(sound_paths["skill2"], [180, 260, 340], 0.55, 0.75, 60)
    create_tone(sound_paths["skill3"], [1320, 880], 0.22, 0.9, -360)
    create_tone(sound_paths["skill4"], [90, 170, 480], 0.62, 0.95, 500)
    create_tone(sound_paths["skill5"], [130, 196, 392, 588], 0.78, 0.92, 120)
    create_tone(sound_paths["skill6"], [860, 1180, 1520], 0.32, 0.92, 280)
    create_tone(sound_paths["skill7"], [110, 170, 260, 520], 0.68, 0.95, 480)
    create_tone(sound_paths["skill8"], [92, 138, 207, 414], 0.88, 1.0, 40)

    sounds = {key: pygame.mixer.Sound(str(path)) for key, path in sound_paths.items()}
    for skill_id, custom_sfx in assets.get("skill_sfx_paths", {}).items():
        custom_path = Path(custom_sfx)
        if custom_path.exists():
            sounds[f"skill{int(skill_id)}"] = pygame.mixer.Sound(str(custom_path))
    sounds["ambient"].set_volume(0.22)
    sounds["ambient"].play(loops=-1)

    bgm_path = assets.get("bgm_path")
    if bgm_path is not None and Path(bgm_path).exists():
        try:
            pygame.mixer.music.load(str(bgm_path))
            pygame.mixer.music.set_volume(0.26)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass
    return sounds
