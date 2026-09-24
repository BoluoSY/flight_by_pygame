# -*- coding: utf-8 -*-
"""单机版 exe 入口：固定以 solo 模式启动，供 PyInstaller 打包用。"""
from main import main

if __name__ == "__main__":
    main(solo=True)