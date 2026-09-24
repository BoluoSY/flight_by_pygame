# -*- coding: utf-8 -*-
"""
桌面悬浮小飞机
单机模式（就你一个人，不连服务器）：
    python main.py --solo
联机模式（需要先有人跑 python server.py）：
    python main.py
方向键移动自己的飞机 | ESC 退出 | 鼠标可穿透操作桌面其它应用。
"""
import os
import sys
import ctypes
from ctypes import wintypes

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from config import (KEY_COLOR, SPEED, FPS, NICKNAME, PLAYER_COLOR, FAKE_COLORS,
                    BULLET_SPEED, MONSTER_LIMIT, MONSTER_INTERVAL,
                    RESPAWN_INVINCIBLE, PLAYER_HIT_INVINCIBLE,
                    MONSTER_DAMAGE, BULLET_DAMAGE, BOSS_BULLET_DAMAGE,
                    BOSS_BULLET_RADIUS)
from plane import Plane
from bullet import Bullet, draw_bullet
from netclient import NetClient
import monster as monster_mod
from boss import Boss
import keymap

# ---------- Win32 透明穿透 ----------
WS_EX_LAYERED     = 0x00080000
WS_EX_TOPMOST     = 0x00000008
GWL_EXSTYLE       = -20
SWP_NOMOVE        = 0x0002
SWP_NOSIZE        = 0x0001
HWND_TOPMOST      = -1
LWA_COLORKEY      = 0x00000001

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def focus_window(screen):
    """把游戏窗口强制拉到前台并聚焦，让方向键/空格进游戏（而不是被 cmd 抢走）。"""
    hwnd = pygame.display.get_wm_info()["window"]
    user32.ShowWindow(hwnd, 5)                 # SW_SHOW
    cur = kernel32.GetCurrentThreadId()
    fg = user32.GetForegroundWindow()
    try:
        fgtid = user32.GetWindowThreadProcessId(fg, None)
        if fgtid != cur:
            user32.AttachThreadInput(cur, fgtid, True)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
    finally:
        if fgtid != cur:
            user32.AttachThreadInput(cur, fgtid, False)


def make_click_through(screen):
    hwnd = pygame.display.get_wm_info()["window"]
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    # 去掉 WS_EX_TRANSPARENT：它会使窗口对鼠标命中测试透明，
    # 在部分 Windows 上会导致窗口无法真正持有键盘焦点，按键输入全被丢弃（飞机不动但能开火）。
    # 保留 LAYERED + TOPMOST + 色彩键，透明效果不变，但窗口能正常接收键盘。
    ex |= WS_EX_LAYERED | WS_EX_TOPMOST
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
    user32.SetWindowPos(hwnd, wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE)
    key = (KEY_COLOR[2] << 16) | (KEY_COLOR[1] << 8) | KEY_COLOR[0]
    user32.SetLayeredWindowAttributes(hwnd, key, 0, LWA_COLORKEY)
    # 摘除系统中文输入法(IME)关联：IME 会在拼音组合时吞掉字母类按键，
    # 导致 W/A/S/D 这类字符键收不到 KEYDOWN（空格/ESC 能透传，故能开火不能移动）。
    # 把窗口的 IME 上下文改为 0 = 禁用，所有按键都作为原生 KEYDOWN 透传。
    try:
        imm32 = ctypes.windll.imm32
        imm32.ImmAssociateContext(hwnd, 0)
    except Exception:
        pass


def main(solo=False):
    pygame.init()
    from plane import _make_font        # 渲染字体，供击杀数/调试用
    KEYS = keymap.resolve()        # 按键码（来自 keymap.py，可自定义）
    SW = user32.GetSystemMetrics(0)
    SH = user32.GetSystemMetrics(1)
    screen = pygame.display.set_mode((SW, SH), pygame.NOFRAME)
    make_click_through(screen)
    focus_window(screen)

    me = Plane(NICKNAME, PLAYER_COLOR)
    me.x, me.y = SW // 2, SH // 2
    held = set()               # 当前被按住的键（keycode 集合，事件驱动更新）

    bullets = []               # 我发射的子弹列表
    spawn = (SW // 2, SH // 2) # 出生点（按 R 重生时回到屏幕中央）
    monsters = []              # 单机模式：怪物列表
    monster_timer = 0          # 距下次尝试生成怪物的帧计数
    kills = 0                  # 单机模式：击杀数
    boss = None                # 单机模式：当前 Boss（每击杀 10 只怪出现一只）
    boss_kill_threshold = 10   # 下一只 Boss 出现的击杀门槛
    fx = []                    # 单机模式：怪死亡效果列表
    inv_timer = 0              # 重生后短暂无敌帧计数（防出生点被怪立即再杀）

    # ---- 联网（联机模式才启动）----
    net = None
    others = {}          # id -> Plane   别人的飞机
    color_i = 0
    if not solo:
        net = NetClient(NICKNAME)
        net.start(SW, SH)
        print(f"联机模式：已尝试连接服务器 {net.server}，昵称 {NICKNAME}")
    else:
        print(f"单机模式：就你一个人，方向键移动（昵称 {NICKNAME}）")

    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                held.add(e.key)                      # 记下按住的键（keycode）
                if e.key == KEYS["quit"]:
                    running = False
                elif e.key == KEYS["fire"] and me.alive:
                    if net is not None:
                        net.fire(me.x, me.y, me.dir)   # 联机：上报开火，服务器广播子弹
                    else:
                        bullets.append(Bullet(me.x, me.y, me.dir))   # 单机：本地造子弹
                elif e.key == KEYS["respawn"] and not me.alive:
                    # 边沿触发：覆盖"快速点按 R 同帧 KEYUP 已移除 held"的情况
                    if net is not None:
                        net.respawn()
                    else:
                        me.respawn(*spawn)
                        inv_timer = RESPAWN_INVINCIBLE
            elif e.type == pygame.KEYUP:
                held.discard(e.key)                  # 抬起时从按住集合移除

        # 每帧兜底：R 被按住时持续尝试重生，避免"按下那一下恰逢未死亡/时序"而漏掉
        if KEYS["respawn"] in held and not me.alive:
            if net is not None:
                net.respawn()                        # 联机：向服务器请求重生
            else:
                me.respawn(*spawn)                   # 单机：本地重生
                inv_timer = RESPAWN_INVINCIBLE       # 重生后短暂无敌，防止立即被怪再杀

        # ---- 1) 本地控制我的飞机（死掉时不能动，停在爆炸点等 R 重生）----
        if me.alive:
            me.control(held, SPEED,
                       KEYS["move_left"], KEYS["move_right"],
                       KEYS["move_up"], KEYS["move_down"])

            me.wrap(SW, SH)
            if net is not None:
                net.send_pos(me.x, me.y)

        # ---- 2) 联机模式：同步其他玩家；单机模式没有 ----
        if net is not None:
            cur = net.others(net.my_id)
            for pid in list(others):
                if pid not in cur:
                    del others[pid]
            for pid, info in cur.items():
                if pid not in others:
                    col = FAKE_COLORS[color_i % len(FAKE_COLORS)]
                    color_i += 1
                    others[pid] = Plane(info["name"], col)
                others[pid].x, others[pid].y = info["x"], info["y"]
                # 别人的飞机同步死亡/重生
                if info["dead"]:
                    others[pid].hit()
                else:
                    others[pid].respawn(info["x"], info["y"])
                others[pid].wrap(SW, SH)

            # 我自己：服务器认为被打中就爆炸，服务器复位后按 R 重生
            my_state = net.myself(net.my_id)
            if my_state is not None:
                if my_state["dead"] and me.alive:
                    me.hit()
                elif not my_state["dead"] and not me.alive:
                    me.respawn(*spawn)

        # ---- 3) 更新并清理我已发射的子弹（仅单机用；联机子弹由服务器同步）----
        for b in bullets:
            b.update(BULLET_SPEED)
        bullets = [b for b in bullets if not b.offscreen(SW, SH)]

        # ---- 3.5) 单机模式：生成/更新怪物，贴近主角致其死亡 ----
        if net is None:
            # 按间隔尝试生成，直到达到上限
            monster_timer += 1
            if monster_timer >= MONSTER_INTERVAL:
                monster_timer = 0
                if len(monsters) < MONSTER_LIMIT:
                    monsters.append(monster_mod.spawn(SW, SH))
            for m in monsters:
                m.chase(me.x, me.y)
            # 越界异常清理
            monsters = [m for m in monsters if not m.offscreen(SW, SH)]
            # 我的子弹命中怪物 → 扣怪血；血扣完怪死亡（子弹一并发消失）
            if bullets and monsters:
                alive_mons = []
                dead_mons = []
                consumed = set()           # 已命中某怪的子弹下标（一颗子弹只打一只怪）
                for m in monsters:
                    m_rect = m.rect()
                    died = False
                    for i, b in enumerate(bullets):
                        if i in consumed:
                            continue
                        if m_rect.colliderect(b.rect()):
                            consumed.add(i)               # 子弹命中后立即消失
                            if m.take_damage(BULLET_DAMAGE):   # 扣血，血尽则亡
                                died = True
                                break
                    if died:
                        dead_mons.append(m)
                    else:
                        alive_mons.append(m)
                if dead_mons:
                    kills += len(dead_mons)          # 记录击杀数
                    for d in dead_mons:
                        fx.append(monster_mod.make_death(d.x, d.y))  # 死亡效果
                    monsters = alive_mons
                if consumed:
                    bullets = [b for i, b in enumerate(bullets)
                               if i not in consumed]  # 命中的子弹一并消失
            # 怪物矩形与主角矩形贴合 → 主角扣血并进入短暂无敌闪烁
            if inv_timer > 0:
                inv_timer -= 1
            if me.alive and inv_timer == 0 and monsters:
                me_rect = me.rect()
                for m in monsters:
                    if me_rect.colliderect(m.rect()):
                        me.take_damage(MONSTER_DAMAGE)      # 每次撞怪减 10 血
                        inv_timer = PLAYER_HIT_INVINCIBLE   # 扣血后闪烁无敌，免后续连伤
                        break
            # 推进怪死亡效果，过期的移除
            fx = [f for f in fx if f.update()]

            # 每击杀 10 只怪 → 出现一个 Boss（100 血）
            if boss is None and kills >= boss_kill_threshold:
                boss = Boss(SW, SH)
                boss_kill_threshold += 10
            # Boss 登场动画推进；可攻击阶段我的子弹命中则扣 Boss 血
            if boss is not None:
                # 给 Boss 瞄准点（瞄准我的飞机），并推进它的游走/开火/炮弹
                if me.alive:
                    boss.set_target(me.x, me.y)
                if boss.active:
                    _bb = boss.rect()
                    remaining = [b for b in bullets
                                 if not b.rect().colliderect(_bb)]
                    if len(remaining) != len(bullets):   # 有子弹打中了 Boss
                        boss.take_damage(BULLET_DAMAGE)
                    bullets = remaining
                # Boss 的黑色炮弹命中我 → 扣 20 血 + 短暂无敌
                if me.alive and inv_timer == 0:
                    hit_r = BOSS_BULLET_RADIUS + 8
                    keep = []
                    for bl in boss.bullets:
                        dx = bl[0] - me.x
                        dy = bl[1] - me.y
                        if dx * dx + dy * dy <= hit_r * hit_r:
                            me.take_damage(BOSS_BULLET_DAMAGE)
                            inv_timer = PLAYER_HIT_INVINCIBLE
                            continue
                        keep.append(bl)
                    boss.bullets = keep
                if not boss.update():                    # 走完死亡渐隐 → 移除
                    boss = None

        # ---- 4) 渲染：铺透明底色，再画怪、子弹、所有人 ----
        screen.fill(KEY_COLOR)
        if net is not None:
            for b in net.bullets():
                draw_bullet(screen, b["x"], b["y"], b["dir"])
        else:
            for b in bullets:
                b.draw(screen)
        for m in monsters:
            m.draw(screen)
        for f in fx:
            f.draw(screen)
        if boss is not None:
            boss.draw(screen)
        for p in others.values():
            p.draw(screen)
        # 无敌期间飞机闪烁（不是随时画，而是按相位显隐，提示无敌状态）
        if inv_timer <= 0 or (inv_timer // 6) % 2 == 0:
            me.draw(screen)
        # 单机模式：右上角显示击杀数
        if net is None:
            kfont = _make_font(26)
            ksurf = kfont.render(f"{kills}", True, (255, 255, 255))
            kx = SW - ksurf.get_width() - 12
            ky = 10
            # 白字描黑边，避免被透明背景/怪遮挡看不清
            kout = kfont.render(f"{kills}", True, (0, 0, 0))
            screen.blit(kout, (kx + 1, ky + 1))
            screen.blit(ksurf, (kx, ky))

        pygame.display.flip()
        clock.tick(FPS)

    if net is not None:
        net.stop()
    pygame.quit()


if __name__ == "__main__":
    main(solo="--solo" in sys.argv)