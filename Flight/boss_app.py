# -*- coding: utf-8 -*-
"""Boss 单独测试场景：双击 boss.bat 启动。
只跑 boss 逻辑，秒出登场动画，方便单独调警告时长/入场动画/血量：
  · WASD 移动      · 空格 开火（可攻击阶段才能打中 Boss）
  · ESC 退出       · 左上角显示当前阶段与 Boss 血量
本文件复用了 main.py 的透明穿透 + 键盘聚焦代码，窗口同样无边框可穿透。"""
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from config import (SPEED, FPS, KEY_COLOR, PLAYER_COLOR, NICKNAME,
                    BULLET_SPEED, BULLET_DAMAGE)
from plane import Plane, _make_font
from bullet import Bullet
from boss import Boss, PHASE_WARNING, PHASE_ENTER, PHASE_ACTIVE, PHASE_DEAD
from main import make_click_through, focus_window  # 复用透明穿透 + 聚焦
import keymap


def main():
    pygame.init()
    KEYS = keymap.resolve()
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    SW, SH = screen.get_size()     # 全屏无边框，沿用主模式分辨率
    make_click_through(screen)
    focus_window(screen)

    me = Plane(NICKNAME, PLAYER_COLOR)
    me.x, me.y = SW // 2, SH // 2

    boss = Boss(SW, SH)      # 立即登场（无需等击杀数/血量门槛）
    bullets = []
    held = set()
    phase_names = {PHASE_WARNING: "裂开", PHASE_ENTER: "入场",
                   PHASE_ACTIVE: "可攻击", PHASE_DEAD: "死亡"}
    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                held.add(e.key)
                if e.key == KEYS["quit"]:
                    running = False
                elif e.key == KEYS["fire"] and boss.active:
                    bullets.append(Bullet(me.x, me.y, me.dir))
            elif e.type == pygame.KEYUP:
                held.discard(e.key)

        # 移动我的飞机（只有 Boss 死了也停，方便单看入场）
        me.control(held, SPEED, KEYS["move_left"], KEYS["move_right"],
                   KEYS["move_up"], KEYS["move_down"])
        me.wrap(SW, SH)

        # 推进子弹 & Boss
        for b in bullets:
            b.update(BULLET_SPEED)
        bullets = [b for b in bullets if not b.offscreen(SW, SH)]
        if boss is not None:
            # 可攻击阶段：子弹撞上 Boss 扣血
            brect = None
            if boss.active:
                b_rect = boss.rect()
                for b in bullets:
                    if b_rect.colliderect(b.rect()):
                        brect = b
                        break
            if brect is not None:
                bullets.remove(brect)
                boss.take_damage(BULLET_DAMAGE)
            if not boss.update():
                boss = None   # 含死亡渐隐走完，从场景移除

        # 渲染
        screen.fill(KEY_COLOR)
        for b in bullets:
            b.draw(screen)
        if boss is not None:
            boss.draw(screen)
        me.draw(screen)

        # 左上角状态：阶段 + Boss 血量
        f = _make_font(22)
        state = "Boss 未登场" if boss is None else phase_names.get(boss.phase, boss.phase)
        hp = "-" if boss is None or boss.death_frame else str(boss.hp)
        info = f.render(f"阶段: {state}   Boss血量: {hp}   （WASD移动 / 空格打Boss）",
                        True, (255, 255, 255))
        out = f.render(f"阶段: {state}   Boss血量: {hp}   （WASD移动 / 空格打Boss）",
                       True, (0, 0, 0))
        screen.blit(out, (11, 11))
        screen.blit(info, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "boss_error.log")
        with open(log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)