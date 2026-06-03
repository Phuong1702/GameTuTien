import random

import pygame

class Enemy:
    def __init__(self, pos, wave, sprite, is_boss=False):
        self.pos = pygame.Vector2(pos)
        self.is_boss = is_boss
        self.name = "Boss" if is_boss else "Quai"
        base_hp = 24 + wave * 7
        self.hp = int(base_hp * (11.5 if is_boss else 1.12))
        self.max_hp = self.hp
        self.speed = (42 + wave * 3 + random.randint(-8, 10)) if is_boss else (56 + wave * 4 + random.randint(-8, 10))
        self.anim_states = {}
        self.state = "walk"
        self.state_time = random.uniform(0.0, 1.2)
        self.attack_cooldown = random.uniform(0.45, 1.1) if is_boss else random.uniform(0.25, 0.8)
        self.attack_anim_timer = 0.0
        self.attack_anim_total = 0.0
        self.attack_damage_done = False
        self.attack_range = 62 if is_boss else 42
        self.attack_damage_mul = 1.55 if is_boss else 0.82
        self.passive_skill_cooldown = random.uniform(1.4, 2.4) if is_boss else 0.0
        self.skill_cooldown = random.uniform(0.9, 3.8) if not is_boss else 0.0
        self.skill_style = random.choice(("bolt", "orb", "split")) if not is_boss else "boss"
        if isinstance(sprite, list):
            self.anim_frames = [frame for frame in sprite if frame is not None]
            self.sprite = self.anim_frames[0] if self.anim_frames else pygame.Surface((24, 24), pygame.SRCALPHA)
        elif isinstance(sprite, dict) and sprite.get("states"):
            self.name = sprite.get("name", self.name)
            for state_name, frames in sprite.get("states", {}).items():
                self.anim_states[state_name] = [frame for frame in frames if frame is not None]
            self.anim_frames = self.anim_states.get("walk", []) or self.anim_states.get("idle", [])
            self.sprite = self.anim_frames[0] if self.anim_frames else pygame.Surface((24, 24), pygame.SRCALPHA)
        else:
            self.anim_frames = []
            self.sprite = sprite
        self.hit_flash = 0.0
        self.anim_timer = random.uniform(0.0, 2.0)
        self.anim_speed = random.uniform(6.0, 10.0)
        self.attack_flash = 0.0


class Projectile:
    def __init__(self, pos, vel, damage, radius, life, color, skill, hostile=False):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.damage = damage
        self.radius = radius
        self.life = life
        self.color = color
        self.skill = skill
        self.hostile = hostile
        self.hit_targets = set()


