# -*- coding: utf-8 -*-
"""客户端联网：负责与服务器的收发。接收在后台线程进行，主游戏循环只读结果。"""
import socket
import threading
import time
from protocol import pack, unpack
from config import SERVER_HOST, SERVER_PORT


class NetClient:
    def __init__(self, name):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1)
        self.server = (SERVER_HOST, SERVER_PORT)
        self.my_id = None              # 服务器分配的编号（welcome 后才有）
        self.players = {}              # id -> {"id":..,"name":..,"x":..,"y":..,"dead":..}  别人的
        self._players = []             # 服务器最新玩家列表，接收线程写入
        self._bullets = []             # 服务器最新子弹列表，接收线程写入
        self._last_send = 0.0
        self._running = True

    # ---------- 启动 / 停止 ----------
    def start(self, screen_w, screen_h):
        self._send({"type": "join", "name": self.name, "x": 0, "y": 0,
                    "w": screen_w, "h": screen_h})
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def stop(self):
        self._running = False
        try:
            self.sock.close()
        except OSError:
            pass

    # ---------- 供游戏调用 ----------
    def send_pos(self, x, y):
        """按节流频率向服务器上报坐标。"""
        now = time.time()
        if now - self._last_send >= 0.5 / 30:    # 约30次/秒，见 config.SEND_RATE
            self._last_send = now
            self._send({"type": "pos", "x": round(x, 1), "y": round(y, 1)})

    def others(self, ignore_id):
        """把服务器告诉我们的其他玩家（去掉自己 id）转成 {id: {name,x,y}}。"""
        return {p["id"]: p for p in self._players if p["id"] != ignore_id}

    def myself(self, ignore_id):
        """服务器对我自己的最新状态（含 dead 标志），找不到返回 None。"""
        for p in self._players:
            if p["id"] == ignore_id:
                return p
        return None

    def bullets(self):
        """服务器广播的当前子弹列表 [{id,x,y,dir}, ...]。"""
        return self._bullets

    def fire(self, x, y, direction):
        """上报一次开火，服务器会在所有客户端生成子弹。"""
        self._send({"type": "fire", "x": round(x, 1), "y": round(y, 1),
                    "dir": direction})

    def respawn(self):
        """请求重生（回到屏幕中央）。"""
        self._send({"type": "respawn"})

    # ---------- 内部 ----------
    def _send(self, msg):
        try:
            self.sock.sendto(pack(msg), self.server)
        except OSError:
            pass

    def _receive_loop(self):
        while self._running:
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                if self._running:     # 偶发连接重置(10054)，忽略继续收
                    continue
                break
            msg = unpack(data)
            t = msg.get("type")
            if t == "welcome":
                self.my_id = msg["id"]
            elif t == "state":
                self._players = msg.get("players", [])
                self._bullets = msg.get("bullets", [])