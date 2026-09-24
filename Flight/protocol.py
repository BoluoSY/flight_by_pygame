# -*- coding: utf-8 -*-
"""消息格式统一封装（JSON）。所有收发都走这几个函数，保证两端格式一致。"""
import json


def pack(msg: dict) -> bytes:
    """dict -> bytes，用于发送"""
    return json.dumps(msg).encode("utf-8")


def unpack(data: bytes) -> dict:
    """bytes -> dict，用于接收"""
    return json.loads(data.decode("utf-8"))


# ---------- 约定好的消息结构 ----------
# 客户端 -> 服务器
#   {"type": "join",  "name": "我的昵称", "w": 1920, "h": 1080}  # w/h=屏幕尺寸
#   {"type": "pos",   "x": 100, "y": 50}          # 客户端周期性上报坐标
#   {"type": "fire",  "x": 100, "y": 50, "dir": "right"}   # 开火（含朝向）
#   {"type": "respawn", }                          # 请求重生回屏幕中央
# 服务器 -> 客户端
#   {"type": "welcome", "id": 1}                  # 告诉客户端自己的编号
#   {"type": "state",                            # 广播：当前所有玩家与子弹状态
#    "players": [{"id":1,"name":"我","x":100,"y":50,"dead":False}, ...],
#    "bullets": [{"id":3,"x":200,"y":80,"dir":"right"}, ...]}