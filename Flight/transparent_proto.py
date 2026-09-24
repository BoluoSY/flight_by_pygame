# -*- coding: utf-8 -*-
"""
最小原型：验证“桌面作为背景 + 飞机悬浮 + 鼠标可穿透”这条技术链路能否在本机跑通。
运行方法：
    python transparent_proto.py
看到效果：
    - 整个屏幕变透明，能看到你桌面上打开的网页/应用
    - 屏幕上有一个品红边缘的小三角（你的飞机），用方向键移动
    - 你的鼠标仍能点击并操作桌面上的其它应用（穿透生效）
退出：
    按 ESC 键
跑不通/有问题告诉我报错信息即可。
"""
import os
import sys
import ctypes
from ctypes import wintypes

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

# ---------- Win32 常量 ----------
WS_EX_LAYERED    = 0x00080000      # 分层窗口（才能做透明）
WS_EX_TRANSPARENT = 0x00000020     # 鼠标穿透
WS_EX_TOPMOST    = 0x00000008      # 置顶
GWL_EXSTYLE      = -20
SWP_NOMOVE       = 0x0002
SWP_NOSIZE       = 0x0001
HWND_TOPMOST     = -1
LWA_COLORKEY     = 0x00000001      # 按颜色抠图
KEY_COLOR        = (255, 0, 255)   # 品红 = 透明/穿透区域

user32 = ctypes.windll.user32
gdi32  = ctypes.windll.gdi32

def make_window_click_through(hwnd):
    """把窗口设为：置顶 + 分层 + 鼠标穿透，并把品红色设为抠图透明色。"""
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    user32.SetWindowPos(hwnd, wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE)
    # key: 0x00BBGGRR
    key = (KEY_COLOR[2] << 16) | (KEY_COLOR[1] << 8) | KEY_COLOR[0]
    user32.SetLayeredWindowAttributes(hwnd, key, 0, LWA_COLORKEY)

def main():
    pygame.init()
    # 桌面分辨率（不开全屏，避免有些系统全屏下分层失效）
    SW = user32.GetSystemMetrics(0)   # 屏幕宽
    SH = user32.GetSystemMetrics(1)   # 屏幕高
    screen = pygame.display.set_mode((SW, SH), pygame.NOFRAME)

    hwnd = pygame.display.get_wm_info()["window"]
    make_window_click_through(hwnd)

    # 用 SRCALPHA 画一个透明底的小三角飞机
    plane = pygame.Surface((60, 60), pygame.SRCALPHA)
    pygame.draw.polygon(plane, (0, 180, 255, 255),
                        [(30, 4), (0, 56), (30, 42), (60, 56)])  # 蓝色飞机
    px, py = SW // 2, SH // 2          # 初始在屏幕中心
    speed = 8

    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  px -= speed
        if keys[pygame.K_RIGHT]: px += speed
        if keys[pygame.K_UP]:    py -= speed
        if keys[pygame.K_DOWN]:  py += speed

        # 先铺满抠图色（=透明穿透区域），再画飞机
        screen.fill(KEY_COLOR)
        screen.blit(plane, (px, py))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()