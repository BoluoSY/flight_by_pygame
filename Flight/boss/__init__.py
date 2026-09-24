# -*- coding: utf-8 -*-
"""boss 独立包：Boss 本体与黑色雾气效果。
对外暴露 Boss 类与阶段常量，方便测试场景直接 `from boss import Boss`。"""
from .boss import (Boss, PHASE_WARNING, PHASE_ENTER, PHASE_ACTIVE, PHASE_DEAD)
from .mist import MistRing
from .crack import Crack

__all__ = ["Boss", "MistRing", "Crack",
           "PHASE_WARNING", "PHASE_ENTER", "PHASE_ACTIVE", "PHASE_DEAD"]