# -*- coding: utf-8 -*-
"""服务器：注册玩家 + 权威管理子弹 + 周期性把所有人/子弹广播给所有人。运行在开房那台电脑上。
运行：python server.py   （Ctrl+C 停止）"""
import socket
import time
from protocol import pack, unpack
from config import (SERVER_BIND, SERVER_PORT,
                    BULLET_SIZE, BULLET_SPEED, PLANE_SIZE)

BROADCAST_RATE = 0.05   # 每 0.05 秒(约20Hz)广播一次所有人状态

# 子弹移动单位向量（与 bullet.py 保持一致）
VEL = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}


class GameServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.bind((SERVER_BIND, SERVER_PORT))
        self.clients = {}      # addr -> {"id":..,"name":..,"x":..,"y":..,"w":..,"h":..,"dead":False}
        self.next_id = 1
        self.bullets = []      # {"id":..,"owner":..,"x":..,"y":..,"dir":..}
        self._next_bullet = 1

    def _spawn_bullet(self, owner, x, y, d):
        self.bullets.append({"id": self._next_bullet, "owner": owner,
                             "x": float(x), "y": float(y), "dir": d})
        self._next_bullet += 1

    def handle(self, data, addr):
        """处理一条收到的消息。"""
        msg = unpack(data)
        t = msg.get("type")
        if t == "join":
            if addr not in self.clients:      # 新玩家上线
                self.clients[addr] = {"id": self.next_id,
                                      "name": msg.get("name", "玩家"),
                                      "x": msg.get("x", 0),
                                      "y": msg.get("y", 0),
                                      "w": msg.get("w", 1280),
                                      "h": msg.get("h", 720),
                                      "dead": False,
                                      "last": time.time()}
                self.next_id += 1
                self.sendto(pack({"type": "welcome",
                                  "id": self.clients[addr]["id"]}), addr)
                print(f"[+] {msg.get('name')} 加入 (id={self.clients[addr]['id']}, {addr})")
        elif t == "pos":
            c = self.clients.get(addr)
            if c:
                c["x"], c["y"] = msg["x"], msg["y"]
                c["last"] = time.time()
        elif t == "fire":
            c = self.clients.get(addr)
            if c:
                self._spawn_bullet(c["id"], msg["x"], msg["y"], msg.get("dir", "right"))
        elif t == "respawn":
            c = self.clients.get(addr)
            if c:
                c["dead"] = False
                c["x"], c["y"] = c["w"] / 2.0, c["h"] / 2.0
                c["last"] = time.time()

    def sendto(self, payload, addr):
        """向某个客户端发数据，出错(对方已关闭等)也不影响其它玩家。"""
        try:
            self.sock.sendto(payload, addr)
        except OSError:
            pass

    def broadcast_state(self):
        """把当前所有人位置/死亡 + 子弹打包并发送给所有人。"""
        if not self.clients:
            return
        players = [{"id": c["id"], "name": c["name"],
                    "x": round(c["x"], 1), "y": round(c["y"], 1),
                    "dead": c["dead"]}
                   for c in self.clients.values()]
        bullets = [{"id": b["id"], "x": round(b["x"], 1),
                    "y": round(b["y"], 1), "dir": b["dir"]}
                   for b in self.bullets]
        payload = pack({"type": "state", "players": players, "bullets": bullets})
        for addr in list(self.clients):
            self.sendto(payload, addr)

    def step_bullets(self):
        """移动子弹、清理出屏、并与存活玩家做碰撞判定。"""
        alive = [c for c in self.clients.values() if not c["dead"]]
        keep = []
        for b in self.bullets:
            vx, vy = VEL.get(b["dir"], VEL["right"])
            b["x"] += vx * BULLET_SPEED
            b["y"] += vy * BULLET_SPEED

            # 出屏判定（用开火玩家自己的屏幕尺寸）
            owner = None
            for c in self.clients.values():
                if c["id"] == b["owner"]:
                    owner = c
                    break
            if owner is not None:
                bh = BULLET_SIZE // 2
                wx, wy = owner["w"], owner["h"]
                if (b["x"] + bh < 0 or b["x"] - bh > wx or
                        b["y"] + bh < 0 or b["y"] - bh > wy):
                    continue   # 整颗出屏，丢弃

            # 与存活玩家碰撞
            hit = False
            bh = BULLET_SIZE // 2
            ph = PLANE_SIZE // 2
            for p in alive:
                if abs(b["x"] - p["x"]) < ph + bh and \
                   abs(b["y"] - p["y"]) < ph + bh:
                    p["dead"] = True
                    print(f"[!] 玩家 id={p['id']} ({p['name']}) 被子弹命中，爆炸")
                    hit = True
                    break
            if not hit:
                keep.append(b)
        self.bullets = keep

    def prune(self, timeout=5.0):
        """移除掉线的玩家（超过 timeout 秒没收到消息就算掉线）。"""
        now = time.time()
        dead = [a for a, c in self.clients.items() if now - c["last"] > timeout]
        for a in dead:
            print(f"[-] {self.clients[a]['name']} 掉线，已移除")
            del self.clients[a]

    def run(self):
        print(f"服务器已启动，监听 {SERVER_BIND}:{SERVER_PORT}")
        last_prune = time.time()
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)
                self.handle(data, addr)
            except BlockingIOError:
                pass
            except OSError:              # 常见于收到已关闭端口的连接重置，忽略即可
                pass
            self.step_bullets()
            self.broadcast_state()
            if time.time() - last_prune > 1:   # 每秒清理一次掉线
                last_prune = time.time()
                self.prune()
            time.sleep(BROADCAST_RATE)


if __name__ == "__main__":
    GameServer().run()