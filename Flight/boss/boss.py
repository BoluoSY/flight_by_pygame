# -*- coding: utf-8 -*-
"""Boss：从屏幕右侧登场（裂开+喷烟） + 可在右侧1/3游走 + 发射黑色炮弹 + 血量。
阶段：warning(裂开前奏) → enter(右侧滑入) → active(可攻击&攻击) → dead(死亡渐隐)：
  · warning  屏幕右侧先"裂开"并喷黑烟，Boss 本体在右侧外待命
  · enter    第 2 次喷烟时从裂缝里滑进目标位（缓动自右向左）
  · active   在屏幕右侧 1/3 区域内缓动游走，向主角发射黑色炮弹，
            同时参与子弹碰撞，血量被子弹消耗；扣完进 dead
  · dead     显示死亡贴图并渐隐后清除
素材放 assets/boss.png（透明背景，默认按原图朝向；素材比例 17:13，
加载时按此比例缩放避免拉伸变形）。缺素材时用带眼的紫色圆兜底。"""
import math
import os
import pygame

from paths import assets_dir
from config import (BOSS_W, BOSS_H, BOSS_OPEN_T, BOSS_CRACK_LEN, BOSS_INTRO_T,
                    BOSS_MAX_HP, BOSS_X_RATIO, BOSS_Y_RATIO, BOSS_LEFT_LIMIT,
                    BOSS_MOVE_SPEED, BOSS_MOVE_DY, BOSS_FIRE_INTERVAL,
                    BOSS_BULLET_SPEED, BOSS_BULLET_RADIUS,
                    MONSTER_DEATH_SIZE, MONSTER_DEATH_TIME)
from plane import _hard_alpha
from .crack import Crack

ASSETS_DIR = assets_dir()

PHASE_WARNING = "warning"
PHASE_ENTER   = "enter"
PHASE_ACTIVE  = "active"
PHASE_DEAD    = "dead"

_IMG = None        # Boss 本体贴图（懒加载）
_IMG_DEATH = None  # 死亡贴图（懒加载）


def _ensure_imgs():
    global _IMG, _IMG_DEATH
    if _IMG is not None:
        return
    src = os.path.join(ASSETS_DIR, "boss.png")
    if os.path.exists(src):
        # 按素材 17:13 原比例缩放，避免拉成正方形变形
        _IMG = _hard_alpha(pygame.transform.scale(
            pygame.image.load(src).convert_alpha(), (BOSS_W, BOSS_H)))
    else:
        # 兜底：没有 boss 素材时画一只带眼的大紫圆（按 W/H 比例变椭圆），默认看向右
        s = pygame.Surface((BOSS_W, BOSS_H), pygame.SRCALPHA)
        cx, cy = BOSS_W // 2, BOSS_H // 2
        pygame.draw.ellipse(s, (120, 40, 200), (0, 0, BOSS_W, BOSS_H))
        pygame.draw.circle(s, (255, 255, 255), (int(BOSS_W * 0.72), cy), 7)
        _IMG = s
    dsrc = os.path.join(ASSETS_DIR, "death.png")
    if os.path.exists(dsrc):
        _IMG_DEATH = _hard_alpha(pygame.transform.scale(
            pygame.image.load(dsrc).convert_alpha(),
            (MONSTER_DEATH_SIZE, MONSTER_DEATH_SIZE)))
    else:
        s = pygame.Surface((MONSTER_DEATH_SIZE, MONSTER_DEATH_SIZE), pygame.SRCALPHA)
        c = MONSTER_DEATH_SIZE // 2
        pygame.draw.circle(s, (230, 60, 30), (c, c), c - 4)
        pygame.draw.line(s, (255, 200, 60), (c - 8, c), (c + 8, c), 4)
        pygame.draw.line(s, (255, 200, 60), (c, c - 8), (c, c + 8), 4)
        _IMG_DEATH = s


def _ease_out(t):
    """缓动曲线：t∈[0,1] → [0,1]，末尾减速，让"甩尾停住"更有力。"""
    u = 1 - t
    return 1 - u * u


class Boss:
    def __init__(self, sw, sh):
        _ensure_imgs()
        self.sw, self.sh = sw, sh
        self.phase = PHASE_WARNING
        self.timer = 0
        # 目标位：屏幕右侧偏上（在右 1/3 区域内的入场落点）
        self.tx, self.ty = sw * BOSS_X_RATIO, sh * BOSS_Y_RATIO
        # 出场起点：目标位右边一个身位，即从屏幕右侧外滑入
        self.sx, self.sy = sw + BOSS_W, self.ty
        self.x, self.y = float(self.sx), float(self.sy)
        self.hp = BOSS_MAX_HP
        self.death_frame = 0
        # 裂开前奏：在屏幕右侧撕开的裂纹（从右边缘向内生成）
        self.crack = Crack(sw - 30, self.ty, BOSS_CRACK_LEN, BOSS_OPEN_T, seed_t=7)

        # --- 右侧 1/3 活动区游走 ---
        self.x_min = sw * BOSS_LEFT_LIMIT + BOSS_W / 2     # 左边界（不越过中线往左）
        self.x_max = sw - BOSS_W / 2                       # 右边界
        self.y_ctr = self.ty                               # 纵向游走中心
        self.vx = BOSS_MOVE_SPEED                          # 起始向右漂
        self.vy = BOSS_MOVE_SPEED * 0.6                    # 起始向下漂

        # --- 黑色炮弹 ---
        self.bullets = []          # 每发 [x, y, vx, vy]
        self.fire_timer = 0
        self.target = (self.tx, self.ty)   # 默认朝入场落点瞄准，set_target 覆盖

    @property
    def active(self):
        """只有"可攻击"阶段才允许被子弹命中。"""
        return self.phase == PHASE_ACTIVE

    def set_target(self, px, py):
        """给 Boss 一个瞄准点（主角当前位置），active 时炮弹飞向它。"""
        self.target = (px, py)

    def update(self):
        """推进一帧；返回 False 表示走完全程（含死亡）可从场景移除。"""
        if self.phase == PHASE_DEAD:
            self.death_frame += 1
            return self.death_frame <= MONSTER_DEATH_TIME
        self.timer += 1
        if self.phase == PHASE_WARNING:
            self.crack.update()                       # 右侧裂隙撑开并喷烟
            # 第 2 次喷黑烟时 Boss 从裂缝出来（超时兜底）
            if self.crack.eruption >= 2 or self.timer >= BOSS_OPEN_T:
                self.phase, self.timer = PHASE_ENTER, 0
        elif self.phase == PHASE_ENTER:
            t = min(1.0, self.timer / float(BOSS_INTRO_T))
            e = _ease_out(t)
            self.x = self.sx + (self.tx - self.sx) * e   # 自右向左，只动 x
            if t >= 1.0:
                self.phase, self.timer = PHASE_ACTIVE, 0
                self.y_ctr = self.ty
        elif self.phase == PHASE_ACTIVE:
            self._move()
            self._fire()
        self._move_bullets()
        return True

    def _move(self):
        """在右侧 1/3 区域内缓动游走，碰到边界反向。"""
        self.x += self.vx
        self.y += self.vy
        if self.x < self.x_min:
            self.x = self.x_min
            self.vx = abs(self.vx)
        elif self.x > self.x_max:
            self.x = self.x_max
            self.vx = -abs(self.vx)
        # 纵向在 ty ± BOSS_MOVE_DY 带内游走
        y_lo = self.y_ctr - BOSS_MOVE_DY
        y_hi = self.y_ctr + BOSS_MOVE_DY
        if self.y < y_lo:
            self.y = y_lo
            self.vy = abs(self.vy)
        elif self.y > y_hi:
            self.y = y_hi
            self.vy = -abs(self.vy)

    def _fire(self):
        """朝目标（主角）发射黑色炮弹，间隔由 BOSS_FIRE_INTERVAL 控制。"""
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_INTERVAL:
            self.fire_timer = 0
            dx = self.target[0] - self.x
            dy = self.target[1] - self.y
            d = math.hypot(dx, dy) or 1.0
            sp = BOSS_BULLET_SPEED
            self.bullets.append([self.x, self.y, dx / d * sp, dy / d * sp])

    def _move_bullets(self):
        """推进所有黑色炮弹并清理越界的。"""
        nb = []
        for bb in self.bullets:
            bb[0] += bb[2]
            bb[1] += bb[3]
            if -50 <= bb[0] <= self.sw + 50 and -50 <= bb[1] <= self.sh + 50:
                nb.append(bb)
        self.bullets = nb

    def take_damage(self, amount):
        """只有可攻击阶段吃伤害；血量扣完进入死亡，返回 True 表示被击杀。"""
        if not self.active:
            return False
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.phase = PHASE_DEAD
            self.death_frame = 0
            return True
        return False

    def rect(self):
        return pygame.Rect(int(self.x - BOSS_W / 2), int(self.y - BOSS_H / 2),
                           BOSS_W, BOSS_H)

    def draw(self, surface):
        # 裂开前奏与出场阶段：屏幕右侧的撕裂裂纹（本体钻出后再淡出）
        if self.phase in (PHASE_WARNING, PHASE_ENTER):
            self.crack.draw(surface)
        # 黑色炮弹（画在 Boss 下面一层）
        for bb in self.bullets:
            px, py = int(bb[0]), int(bb[1])
            pygame.draw.circle(surface, (8, 8, 12), (px, py), BOSS_BULLET_RADIUS)
            pygame.draw.circle(surface, (60, 60, 70), (px, py),
                               BOSS_BULLET_RADIUS, 2)

        if self.phase == PHASE_WARNING:
            return
        if self.phase == PHASE_DEAD:
            alive = MONSTER_DEATH_TIME - self.death_frame
            if alive <= 0:
                return
            img = _IMG_DEATH.copy()
            img.set_alpha(max(0, min(255, int(255 * alive /
                                              max(1, MONSTER_DEATH_TIME // 2)))))
            surface.blit(img, (int(self.x - MONSTER_DEATH_SIZE // 2),
                               int(self.y - MONSTER_DEATH_SIZE // 2)))
            return
        # 入场与可攻击阶段都画本体；入场时叠加淡入
        img = _IMG
        if self.phase == PHASE_ENTER:
            alpha = max(0, min(255, int(255 * self.timer /
                                        max(1, BOSS_INTRO_T * 0.3))))
            img = img.copy()
            img.set_alpha(alpha)
        surface.blit(img, (int(self.x - BOSS_W / 2), int(self.y - BOSS_H / 2)))