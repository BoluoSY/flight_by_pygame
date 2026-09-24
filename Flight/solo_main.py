# -*- coding: utf-8 -*-
"""打包入口：双击生成的 exe 直接进入单机模式（无需 --solo 参数）。"""
from main import main

if __name__ == "__main__":
    main(solo=True)