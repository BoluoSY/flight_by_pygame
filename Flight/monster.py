# -*- coding: utf-8 -*-
"""怪物：从屏幕左右两侧随机位置出现，自动向主角靠近，贴到就致死。
素材放 assets/monster.png。怪物始终朝向主角方向移动，跨过主角另一侧时
整图旋转 180° 转到另一面。缺素材时用代码画紫色圆兜底。"""
import math
import random
import os
import pygame
from paths import assets_dir
from config import (MONSTER_SIZE, MONSTER_SPEED, MONSTER_WAVE, MONSTER_WAVEF,
                    FLANK_RANGE, FLANK_OFFSET, MONSTER_DEATH_SIZE,
                    MONSTER_DEATH_TIME, MONSTER_HP)
from plane import _hard_alpha

ASSETS_DIR = assets_dir()

_IMG = None          # 原始朝右贴图（懒加载）
_IMG_FLIPPED = None  # 旋转 180° 后的贴图
_IMG_DEATH = None    # 怪死亡贴图（懒加载）


def _ensure_imgs():
    global _IMG, _IMG_FLIPPED, _IMG_DEATH
    if _IMG is not None:
        return
    src = os.path.join(ASSETS_DIR, "monster.png")
    if os.path.exists(src):
        _IMG = _hard_alpha(pygame.transform.scale(
            pygame.image.load(src).convert_alpha(),
            (MONSTER_SIZE, MONSTER_SIZE)))
    else:
        # 兜底：没有素材时画一个紫色怪（圆形 + 两只角），默认看向右
        s = pygame.Surface((MONSTER_SIZE, MONSTER_SIZE), pygame.SRCALPHA)
        c = MONSTER_SIZE // 2
        pygame.draw.circle(s, (150, 60, 220), (c, c), c - 4)
        pygame.draw.circle(s, (255, 255, 255), (c + 4, c), 3)  # 眼在右侧 → 朝右
        _IMG = s
    _IMG_FLIPPED = pygame.transform.flip(_IMG, True, True)
    # 死亡贴图：使用 assets/death.png（与飞机爆炸同一张），缺则红色十字星兜底
    dsrc = os.path.join(ASSETS_DIR, "death.png")
    if os.path.exists(dsrc):
        _IMG_DEATH = _hard_alpha(pygame.transform.scale(
            pygame.image.load(dsrc).convert_alpha(),
            (MONSTER_DEATH_SIZE, MONSTER_DEATH_SIZE)))
    else:
        s = pygame.Surface((MONSTER_DEATH_SIZE, MONSTER_DEATH_SIZE), pygame.SRCALPHA)
        c = MONSTER_DEATH_SIZE // 2
        pygame.draw.circle(s, (230, 60, 30), (c, c), c - 4)   # 红色爆点
        pygame.draw.line(s, (255, 200, 60), (c - 8, c), (c + 8, c), 4)
        pygame.draw.line(s, (255, 200, 60), (c, c - 8), (c, c + 8), 4)
        _IMG_DEATH = s


def spawn(w, h):
    """在屏幕右侧随机一个 y，生成一只往主角方向走的怪物。"""
    _ensure_imgs()
    x = w + MONSTER_SIZE   # 只从右侧屏幕边缘出来
    y = random.uniform(MONSTER_SIZE, h - MONSTER_SIZE)
    return Monster(x, y)


class Monster:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = True   # 当前朝向：True=朝右, False=朝左(已被翻转)
        self.image = _IMG
        self.wave_t = random.uniform(0, math.tau)  # S形摆动相位（每只不同）
        self.flanker = random.random() < 0.4       # 40% 的怪会绕后
        # 绕向：-1 或 +1，让怪绕主角时偏上或偏下（视觉有差异）
        self.steer = random.choice((-1.0, 1.0))
        self.hp = MONSTER_HP      # 血量：被子弹打中扣血，扣完死亡

    def take_damage(self, amount):
        """受到伤害；血量扣到 0 或更少时返回 True（死亡）。"""
        self.hp -= amount
        return self.hp <= 0

    def chase(self, target_x, target_y):
        """朝主角移动（带 S 形摆动）。部分怪到主角附近时绕其侧面弧线再扑入。"""
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return

        # 朝向主角的单位向量 (ux, uy) 与它的垂直方向 (px, py)
        ux, uy = dx / dist, dy / dist
        px, py = -uy, ux

        # 移动方向：普通怪直扑主角；绕后怪叠加垂直切线偏量做弧线迂回
        vx, vy = ux, uy
        if self.flanker and dist < FLANK_RANGE:
            # 越靠近主角偏量越小（衰减），否则会一直绕圈永不挨到；
            # 用 dist/FLANK_RANGE 让偏量随接近而变小，最终直线切入碰撞
            amt = self.steer * 0.9 * min(1.0, dist / max(1.0, FLANK_RANGE))
            vx += px * amt
            vy += py * amt
        vl = math.hypot(vx, vy)
        if vl > 1e-6:
            vx, vy = vx / vl, vy / vl

        # S 形走位：沿垂直于飞行方向摆动
        self.wave_t += MONSTER_WAVEF
        sway = math.sin(self.wave_t) * MONSTER_WAVE
        self.x += vx * MONSTER_SPEED + px * sway
        self.y += vy * MONSTER_SPEED + py * sway

        # 朝向：以相对主角的水平位置决定显示面
        should_face_right = target_x > self.x
        if should_face_right != self.facing_right:
            self.facing_right = should_face_right
            self.image = _IMG if should_face_right else _IMG_FLIPPED

    def rect(self):
        half = MONSTER_SIZE // 2
        return pygame.Rect(int(self.x - half), int(self.y - half),
                           MONSTER_SIZE, MONSTER_SIZE)

    def offscreen(self, w, h):
        """是否完全飞出屏幕再远一圈的范围（用于清理异常怪）。
        出生点就在屏幕外一个 MONSTER_SIZE，所以边距必须大于 MONSTER_SIZE，
        否则刚出生的怪会被误删。这里用两倍尺寸做边距。"""
        half = MONSTER_SIZE // 2
        margin = MONSTER_SIZE * 2
        return (self.x + half < -margin or self.x - half > w + margin or
                self.y + half < -margin or self.y - half > h + margin)

    def draw(self, surface):
        half = MONSTER_SIZE // 2
        surface.blit(self.image, (int(self.x - half), int(self.y - half)))


def make_death(x, y):
    """创建一个怪死亡效果（在(x,y)显示死亡贴图并渐隐）。"""
    _ensure_imgs()
    return DeathFx(x, y)


class DeathFx:
    """怪死亡效果：显示 MONSTER_DEATH_TIME 帧后逐渐消失。"""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.frame = 0
        self.image = _IMG_DEATH

    def update(self):
        """推进一帧；返回 False 表示效果结束。"""
        self.frame += 1
        return self.frame <= MONSTER_DEATH_TIME

    def draw(self, surface):
        # 后半段渐隐（越接近结束越淡）
        alive = MONSTER_DEATH_TIME - self.frame
        if alive <= 0:
            return
        img = self.image.copy()
        img.set_alpha(max(0, min(255, int(255 * alive / max(1, MONSTER_DEATH_TIME // 2)))))
        surface.blit(
            img,
            (int(self.x - MONSTER_DEATH_SIZE // 2),
             int(self.y - MONSTER_DEATH_SIZE // 2)))