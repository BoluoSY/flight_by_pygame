# -*- coding: utf-8 -*-
"""一架飞机的模型：负责用自己的状态画出自己 + 移动。"""
import os
import math
import pygame
from paths import assets_dir
from config import (PLANE_SIZE, NAME_COLOR, DEATH_SIZE,
                    IDLE_BOB, IDLE_BREATH, FLAME_LEN, FLAME_FLICK, TURN_TILT,
                    PLAYER_MAX_HP)

ASSETS_DIR = assets_dir()
# 方向图命名放 assets 里（无 plane_ 前缀）：
#   right.png / left.png / up.png / down.png
DIRS = ("right", "left", "up", "down")
# 机头朝向 → 尾焰要伸向的反方向（单位向量）
REAR = {"right": (-1, 0), "left": (1, 0), "up": (0, 1), "down": (0, -1)}


def _hard_alpha(surface):
    """把半透明像素硬化为全透明(0)或全不透明(255)，
    避免边缘半透明像素与品红背景混色产生紫色描边。"""
    a = pygame.surfarray.pixels_alpha(surface)
    a[a < 128] = 0        # 原本半透明→全透明
    a[a >= 128] = 255     # 原本较实→全不透明
    del a                 # 释放像素视图，避免表面被锁
    return surface


def _load_img(path, size=PLANE_SIZE):
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, (size, size))
        return _hard_alpha(img)
    return None


# 打包成 exe 后 pygame.font.SysFont() 会崩溃（扫描系统字体目录时报错），
# 这里直接按系统字体文件路径加载，绕开会崩溃的逻辑，且仍能显示中文。
_FONT_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",   # 微软雅黑
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf", # 黑体
]


def _make_font(size):
    for path in _FONT_PATHS:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                continue
    return pygame.font.Font(None, size)   # 兜底：用 pygame 自带默认字体


class Plane:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.x = 0.0   # 中心 x
        self.y = 0.0   # 中心 y
        self.dir = "right"

        # 只用 4 张方向图；缺失的方向就沿用当前方向（不报错）
        self.images = {}
        for d in DIRS:
            img = _load_img(os.path.join(ASSETS_DIR, f"{d}.png"))
            if img is not None:
                self.images[d] = img
        self.image = self.images.get(self.dir)

        # 名字标签 Surface（白色描边文字）
        font = _make_font(18)
        self.label = font.render(self.name, True, NAME_COLOR)

        # ---- 生命/爆炸状态 ----
        self.alive = True                # 是否存活；血量扣完就 False，按 R 重生恢复
        self.hp = PLAYER_MAX_HP          # 当前血量（起始为满血），受怪撞击扣血
        self.death_img = _load_img(os.path.join(ASSETS_DIR, "death.png"),
                                   DEATH_SIZE)

        # ---- 动画状态 ----
        self.frame = 0.0                 # 全局帧计数（驱动待机浮动/呼吸/尾焰）
        self.moving = False              # 是否正在移动（决定尾焰是否喷发）
        self.turn = 0.0                  # 转弯侧倾角（朝 target 缓动）

    def hit(self):
        """被子弹击中：进入爆炸状态（如果是敌机被打中则直接消失）。"""
        self.alive = False

    def take_damage(self, amount):
        """主角受怪伤害：血量扣掉 amount；扣到 0 或更少时死亡，返回 True。"""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def respawn(self, x, y):
        """按 R 重生：恢复存活、回满血并挪到出生点。"""
        self.alive = True
        self.hp = PLAYER_MAX_HP
        self.x, self.y = x, y

    def _face(self, direction):
        """朝向变化时，把当前图片换成对应方向的图（缺图就沿用当前）。"""
        if direction == self.dir:
            return
        img = self.images.get(direction)
        if img is not None:
            self.dir = direction
            self.image = img

    def control(self, keys, speed, k_left, k_right, k_up, k_down):
        """我的飞机：根据按键更新位置、换图，并记录是否在移动/转弯。
        keys：当前被按住的键码集合（keycode，来自 main 的 held/事件）。"""
        moved = False
        self.turn = 0.0
        if k_left in keys:
            self.x -= speed
            self._face("left")
            self.turn = TURN_TILT          # 左移 → 机身向右微倾
            moved = True
        elif k_right in keys:
            self.x += speed
            self._face("right")
            self.turn = -TURN_TILT
            moved = True
        if k_up in keys:
            self.y -= speed
            self._face("up")
            moved = True
        elif k_down in keys:
            self.y += speed
            self._face("down")
            moved = True
        self.moving = moved

    def wrap(self, w, h):
        """穿越屏幕边界：移出最右侧→从左侧进来，上下同理。"""
        half = PLANE_SIZE // 2
        if self.x < -half:
            self.x = w + half
        elif self.x > w + half:
            self.x = -half
        if self.y < -half:
            self.y = h + half
        elif self.y > h + half:
            self.y = -half

    def rect(self):
        """返回飞机的中心矩形，用于碰撞检测。"""
        half = PLANE_SIZE // 2
        return pygame.Rect(int(self.x - half), int(self.y - half),
                           PLANE_SIZE, PLANE_SIZE)

    def draw(self, surface):
        """把飞机和头顶名字画到屏幕上；被打中时显示爆炸图。"""
        if not self.alive:
            if self.death_img is not None:
                half = DEATH_SIZE // 2
                surface.blit(self.death_img,
                             (int(self.x - half), int(self.y - half)))
            return

        self.frame += 1.0
        half = PLANE_SIZE // 2

        # ---- 待机动画：上下浮动 + 呼吸缩放 ----
        bob = 0.0
        scale = 1.0
        if not self.moving:
            bob = IDLE_BOB * math.sin(self.frame / 22.0)
            scale = 1.0 + IDLE_BREATH * math.sin(self.frame / 18.0)

        # ---- 飞行动画：先画引擎尾焰（机头朝向反方向）----
        if self.moving:
            self._draw_flame(surface, self.x, self.y + bob)

        # ---- 转弯微倾（围绕中心旋转）----
        img = self.image
        if self.turn:
            img = _hard_alpha(pygame.transform.rotate(img, self.turn))

        # 呼吸缩放
        if abs(scale - 1.0) > 0.001:
            s = max(1, int(PLANE_SIZE * scale))
            img = _hard_alpha(pygame.transform.smoothscale(img, (s, s)))
            half = s // 2

        surface.blit(img, (int(self.x - half), int(self.y + bob - half)))
        # 名字显示在机头上方
        label_w = self.label.get_width()
        surface.blit(self.label,
                     (int(self.x - label_w / 2), int(self.y + bob - half - 22)))

    def _draw_flame(self, surface, cx, cy):
        """在飞机引擎后方画一撮闪烁的尾焰（纯代码绘制，随朝向旋转）。"""
        rx, ry = REAR.get(self.dir, REAR["right"])
        # 尾焰长度：基础 + 一阶抖动
        length = FLAME_LEN + FLAME_FLICK * math.sin(self.frame / 3.0)
        # 尾焰根部位移（从机身中心朝机尾方向挪开一个机身半径）
        root = PLANE_SIZE * 0.45
        bx = cx + rx * root
        by = cy + ry * root
        tipx = cx + rx * (root + length)
        tipy = cy + ry * (root + length)
        # 垂直于朝向的半宽
        w2 = PLANE_SIZE * 0.32
        nx, ny = -ry * w2, rx * w2
        # 两片：外层橙、内层黄，形成火焰感
        outer = [(int(tipx), int(tipy)),
                 (int(bx + nx), int(by + ny)),
                 (int(bx - nx), int(by - ny))]
        nx2, ny2 = nx * 0.5, ny * 0.5
        tipx2 = cx + rx * (root + length * 0.55)
        tipy2 = cy + ry * (root + length * 0.55)
        inner = [(int(tipx2), int(tipy2)),
                 (int(bx + nx2), int(by + ny2)),
                 (int(bx - nx2), int(by - ny2))]
        pygame.draw.polygon(surface, (255, 120, 20), outer)
        pygame.draw.polygon(surface, (255, 210, 60), inner)