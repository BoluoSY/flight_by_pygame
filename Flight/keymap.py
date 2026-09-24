# -*- coding: utf-8 -*-
"""
按键配置文件：修改键位只需改这个文件里的值。

可用的键名（写到下面的字符串里）：
    字母：a ~ z          数字：0 ~ 9
    方向键：left right up down
    空格：space   回车：return   退格：backspace   删除：delete   制表符：tab
    ESC：escape   分号：semicolon   点：period   斜杠：slash
    功能键：f1 f2 ... f12      小键盘：kp0 ~ kp9、kp_enter 等
    修饰键：lshift rshift lctrl rctrl lalt ralt
更多名称见 pygame.key.name() 的返回值（用小写）。

格式：动作 = "键名"
"""
import pygame

# 动作 -> 键名（小写）
MAPPING = {
    "move_up":    "W",       # 向上飞
    "move_down":  "S",     # 向下飞
    "move_left":  "A",     # 向左飞
    "move_right": "D",    # 向右飞
    "fire":       "space",    # 开火
    "respawn":    "R",        # 重生
    "quit":       "escape",   # 退出游戏
}


def _to_code(name):
    """把键名转成 pygame 键值。
    优先按 pygame 常量 K_<大写> 取准确的键值（如 left→K_LEFT），
    取不到再退回 key_code（单字符如 r、space 仍有效）。"""
    pyname = "K_" + name.upper()
    const = getattr(pygame, pyname, None)
    if isinstance(const, int):
        return const
    code = pygame.key.key_code(name.lower())
    if code == 0:
        raise ValueError(f"keymap.py：未识别的键名 {name!r}")
    return code


def resolve():
    """把 MAPPING 里的键名解析成 pygame 键值，返回 {"动作": kcode}。"""
    out = {}
    for action, name in MAPPING.items():
        out[action] = _to_code(name.strip())
    return out