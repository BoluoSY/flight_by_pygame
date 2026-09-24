# -*- coding: utf-8 -*-
"""裂缝单独测试：双击 crack.bat 启动。
只在屏幕右侧重复播放"裂开"效果（裂缝张开后稍等再重开一局），
方便单独调 BOSS_CRACK_LEN(撕开长度) / BOSS_OPEN_T(张开的帧数)。
ESC 退出；左上角显示开关提示。复用 main.py 的透明穿透 + 键盘聚焦。"""
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from config import FPS, KEY_COLOR, BOSS_CRACK_LEN, BOSS_OPEN_T
from plane import _make_font
from boss.crack import Crack
from main import make_click_through, focus_window
import keymap


def main():
    pygame.init()
    KEYS = keymap.resolve()
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    SW, SH = screen.get_size()
    make_click_through(screen)
    focus_window(screen)

    # 在屏幕右侧边缘撕开的裂缝（循环播放）
    crack = Crack(SW - 30, SH * 0.3, BOSS_CRACK_LEN, BOSS_OPEN_T, seed_t=7)
    hold_timer = 0     # 裂完稍作停顿再开下一局
    held = set()
    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                held.add(e.key)
                if e.key == KEYS["respawn"]:
                    crack = Crack(SW - 30, SH * 0.3, BOSS_CRACK_LEN,
                                  BOSS_OPEN_T, seed_t=7)     # R 手动重放
                elif e.key == KEYS["quit"]:
                    running = False
            elif e.type == pygame.KEYUP:
                held.discard(e.key)

        # 推进裂缝；走完停顿几帧再自动开下一局
        if crack.update():
            pass
        else:
            hold_timer += 1
            if hold_timer > BOSS_OPEN_T:
                hold_timer = 0
                crack = Crack(SW - 30, SH * 0.3, BOSS_CRACK_LEN,
                              BOSS_OPEN_T, seed_t=7)

        screen.fill(KEY_COLOR)
        crack.draw(screen)

        info = _make_font(20).render("右侧裂开效果  （R 重放 / ESC 退出）",
                                     True, (0, 0, 0))
        red = _make_font(20).render("右侧裂开效果  （R 重放 / ESC 退出）",
                                    True, (255, 255, 255))
        screen.blit(info, (11, 11))
        screen.blit(red, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "crack_error.log")
        with open(log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)