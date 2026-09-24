# -*- coding: utf-8 -*-
"""统一解析资源目录：源码时取项目根/assets，PyInstaller 打包后取解压目录/assets。
这样源码运行和打包成 exe 都能正确读到贴图。"""
import os
import sys


def assets_dir():
    """返回 assets 资源目录的绝对路径。"""
    if getattr(sys, "frozen", False):
        # 打包后：onefile 解压到 _MEIPASS，onedir 为 _internal
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        # 源码：paths.py 位于项目根，assets 与它同级
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets")