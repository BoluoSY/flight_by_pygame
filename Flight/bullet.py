# -*- coding: utf-8 -*-
"""子弹：朝飞机的朝向飞行。素材只放一张 assets\bullet.png（朝上），按方向旋转。
注意：图片在第一次开火时才加载（需要显示已 init），避免 import 阶段报错。"""
import os
import pygame
from paths import assets_dir
from config import BULLET_SIZE
from plane import _hard_alpha

ASSETS_DIR = assets_dir()
DIRS = ("right", "left", "up", "down")
VEL  = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}  # 单位向量
ROT  = {"up": 0, "right": -90, "down": 180, "left": 90}   # 从"朝上"图旋转的角度

_BULLET_IMAGES = None   # 缓存，首次用到再构建


def _ensure_loaded():
    """初始化 4 个方向的子弹贴图（只在第一次开火时执行一次）。"""
    global _BULLET_IMAGES
    if _BULLET_IMAGES is not None:
        return
    _BULLET_IMAGES = {}
    src = os.path.join(ASSETS_DIR, "bullet.png")
    if os.path.exists(src):
        base = _hard_alpha(pygame.transform.scale(
            pygame.image.load(src).convert_alpha(),
            (BULLET_SIZE, BULLET_SIZE)))
        for d in DIRS:
            _BULLET_IMAGES[d] = _hard_alpha(
                pygame.transform.rotate(base, ROT[d]))
    else:
        for d in DIRS:   # 没素材时兜底：朝上的小三角
            s = pygame.Surface((BULLET_SIZE, BULLET_SIZE), pygame.SRCALPHA)
            half = BULLET_SIZE // 2
            pygame.draw.polygon(s, (255, 220, 60),
                                [(half, 2), (BULLET_SIZE - 4, BULLET_SIZE - 4),
                                 (half, BULLET_SIZE - 9), (4, BULLET_SIZE - 4)])
            _BULLET_IMAGES[d] = s


def draw_bullet(surface, x, y, direction):
    """按服务器同步的坐标直接画一颗子弹（联机模式用，省去构建对象）。"""
    _ensure_loaded()
    img = _BULLET_IMAGES.get(direction, _BULLET_IMAGES["right"])
    half = BULLET_SIZE // 2
    surface.blit(img, (int(x - half), int(y - half)))


class Bullet:
    def __init__(self, x, y, direction):
        _ensure_loaded()
        self.x = x
        self.y = y
        self.dir = direction
        self.image = _BULLET_IMAGES.get(direction, _BULLET_IMAGES["right"])

    def update(self, speed):
        vx, vy = VEL.get(self.dir, VEL["right"])
        self.x += vx * speed
        self.y += vy * speed

    def offscreen(self, w, h):
        """整颗子弹完全飞出屏幕边界后才消失。"""
        half = BULLET_SIZE // 2
        return (self.x + half < 0 or self.x - half > w or
                self.y + half < 0 or self.y - half > h)

    def rect(self):
        """返回子弹的中心矩形，用于碰撞检测。"""
        half = BULLET_SIZE // 2
        return pygame.Rect(int(self.x - half), int(self.y - half),
                           BULLET_SIZE, BULLET_SIZE)

    def draw(self, surface):
        half = BULLET_SIZE // 2
        surface.blit(self.image, (int(self.x - half), int(self.y - half)))