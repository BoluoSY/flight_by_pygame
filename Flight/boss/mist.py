# -*- coding: utf-8 -*-
"""声波状黑雾圈：从 Boss 本体一圈一圈向外扩散。
每圈 MistRing 从本体中心发出，像一个扩大的同心圆环向外张开并逐圈变淡，
类似声波/anchor 扩散，形成"一圈圈黑雾往外放"的视觉。
由 Boss 每隔 BOSS_RING_INTERVAL 帧发出一圈。"""
import pygame
from config import BOSS_RING_MAX, BOSS_RING_SPEED, BOSS_RING_FADE


class MistRing:
    """一圈从中心向外张开、逐渐消散的黑雾环。"""

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)   # 生成时 Boss 中心
        self.r = float(BOSS_RING_SPEED)       # 起始半径（从本体处起）
        self.life = 0

    def update(self):
        """半径随时间增大；超过最大半径或寿命结束时返回 False 移除。"""
        self.r += BOSS_RING_SPEED
        self.life += 1
        return self.life <= BOSS_RING_FADE and self.r < BOSS_RING_MAX

    def draw(self, surface):
        d = int(self.r * 2)
        w = max(4, d)
        a = int(190 * (1 - self.life / float(BOSS_RING_FADE)))  # 越远越淡
        if a <= 0:
            return
        frame = pygame.Surface((w, w), pygame.SRCALPHA)
        cx = cy = w // 2
        # 外圈主环（黑），内圈略浅，贴合出"雾圈"的柔和厚度
        pygame.draw.circle(frame, (0, 0, 0, max(50, min(255, a))),
                           (cx, cy), cx - 4, width=4)
        pygame.draw.circle(frame, (0, 0, 0, max(110, min(255, a))),
                           (cx, cy), cx - 10, width=2)
        surface.blit(frame, (int(self.x - cx), int(self.y - cy)))