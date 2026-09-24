# -*- coding: utf-8 -*-
"""屏幕右侧的"影视级撕裂开口"动画：Boss 出场前右侧撕开一道裂缝。
分阶段、叠加多层视觉：
  1) 颤抖闪现 + easeOutBack 猛撑：一道带过冲的锯齿裂口，四周崩开
  2) 能量内核：裂口敞开处先衬一圈暗色"能量泄漏"，再填纯黑虚空
  3) 喷涌黑物质：裂口向外喷翻涌的柔软黑烟柱（预渲染径向渐变烟团贴图做体量）
  4) 白进黑出对比：亮色碎屑被吸进虚空，黑色烟气反向喷出，张力拉满
接口不变：Crack(cx, cy, max_len, duration, seed_t) + update()/draw()。"""
import math
import random
import pygame

from config import (BOSS_SMOKE_RATE, BOSS_SMOKE_SPEED, BOSS_SMOKE_LIFE,
                    BOSS_SMOKE_MAX, BOSS_SMOKE_BURSTS)

# ---------- 预渲染径向渐变烟团贴图（只做一次，全局复用） ----------
_SMOKE_SIZES = (18, 26, 36, 50, 68, 92, 126)
_SMOKE_SPRITES = {}


def _smoke_sprite(size):
    """以 size 为边长生成一张"中心黑、边缘透明"的柔软烟团贴图。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2
    rmax = int(size / 2) - 1
    # 从外到内画一圈圈向里递增不透明度，形成柔软渐变
    for i in range(rmax):
        r = int(rmax - i)
        a = int(130 * (1.0 - (i / rmax) ** 2))   # 中心更黑 → 阴影渐变
        pygame.draw.circle(surf, (30, 30, 34, a), (int(cx), int(cy)), r)
    return surf


def _smoke_by(size):
    """按当前大小取最近的预渲染烟团尺寸，控制缩放频率。"""
    best = min(_SMOKE_SIZES, key=lambda s: abs(s - size))
    if best not in _SMOKE_SPRITES:
        _SMOKE_SPRITES[best] = _smoke_sprite(best)
    return best, _SMOKE_SPRITES[best]


def _ease_out_back(x):
    """缓动：带回弹过冲，开口时"狠撑"一下再回落。"""
    x = max(0.0, min(1.0, x))
    if x == 0:
        return 0.0
    c1, c2 = 1.70158, 2.70158
    u = x - 1
    return c2 * u * u * u + c1 * u * u + 1   # 结果可 >1，做出过冲


class Crack:
    def __init__(self, cx, cy, max_len, duration, seed_t=0):
        self.cx, self.cy = cx, cy
        self.max_len = max_len          # 裂口纵向半高（整道缝高约 2*max_len）
        self.dur = max(1, duration)
        self.life = 0
        rng = random.Random(seed_t)
        self.segs = 16                   # 纵向切片数
        self.jx = [rng.uniform(-9, 9) for _ in range(self.segs + 1)]
        self.phase = [rng.uniform(0, math.tau) for _ in range(self.segs + 1)]
        self.branch = []                 # (切片序号, 侧向偏移, 分叉角, 长度)
        for _ in range(rng.randint(4, 6)):
            self.branch.append((rng.randint(1, self.segs - 1),
                                rng.uniform(-0.4, 0.4),
                                rng.uniform(-math.pi, math.pi),
                                rng.randint(16, 36)))
        self.sparks = []                 # 被吸进虚空的亮色碎屑 [x,y,px,py,vx,vy,life]
        self.smoke = []                  # 喷涌出的黑烟团 [x,y,vx,vy,life,size]
        self.eruption = 0                # 已开始的喷发次数（从 1 计，供 Boss 对齐出场）

    # ---------- 阶段 / 进度 ----------
    def _t(self):
        return min(1.0, self.life / float(self.dur))

    def _open(self):
        """0..1 开口进度：前 15% 只颤出细缝，随后带过冲撑开并维持。"""
        if self._t() <= 0.15:
            return 0.0
        a = (self._t() - 0.15) / 0.5
        return _ease_out_back(max(0.0, min(1.0, a)))

    # ---------- 主循环：推进动画 ----------
    def update(self):
        self.life += 1
        self._step_smoke()
        self._step_sparks()
        return self.life < self.dur

    def _step_smoke(self):
        """裂缝开口时，分几次明显"喷发"往外喷柔软黑烟（每次喷一小段再停）。"""
        t = self._t()
        floor = BOSS_SMOKE_BURSTS
        # 当前处于第几次喷发的时段（0..正式开始第 k_cur 次）
        k = int(t * floor) + 1
        if k > self.eruption:                     # 进入新一次喷发
            self.eruption = k
        # 在每次喷发的前 45% 窗口内喷烟，其余时间歇口气 → 形成几次突涌
        if 1 <= k <= floor:
            pos = (min(t, 1.0) - (k - 1) / float(floor)) * floor   # 本次内 0..1
            if pos < 0.45:
                op = self._open()
                n = int(BOSS_SMOKE_RATE * 2 + op * 5)
                half = self.max_len
                for _ in range(n):
                    y = self.cy + (random.random() * 2 - 1) * half
                    x = self.cx + (random.random() * 2 - 1) * (12 + op * 30)
                    spd = BOSS_SMOKE_SPEED * (0.7 + random.random())
                    ang = math.pi + random.uniform(-0.55, 0.45)
                    self.smoke.append([
                        x, y,
                        math.cos(ang) * spd,
                        math.sin(ang) * spd - 0.25,
                        0, random.randint(9, 14 + int(op * 8))])
        # 推进 + 湍流抖动
        flow = []
        for s in self.smoke:
            s[4] += 1
            if s[4] >= BOSS_SMOKE_LIFE:
                continue
            wig = math.sin(s[4] * 0.5 + s[1] * 0.02) * 0.5
            s[0] += s[2] + wig
            s[1] += s[3]
            s[2] *= 0.99
            s[5] += 0.95
            flow.append(s)
        self.smoke = flow[-BOSS_SMOKE_MAX:]

    def _step_sparks(self):
        """裂缝开口时迸出、随后被吸进虚空的亮色碎屑（与黑烟反向，制造对比）。"""
        if self._t() < 0.9:
            for _ in range(int(2 + 8 * self._open())):
                y = self.cy + (random.random() * 2 - 1) * self.max_len * 0.9
                x = self.cx + (random.random() * 2 - 1) * 12
                ang = random.uniform(0, math.tau)
                sp = random.uniform(0.5, 2.4)
                self.sparks.append([x, y, x, y,
                                    math.cos(ang) * sp + (self.cx - x) * 0.06,
                                    math.sin(ang) * sp, random.randint(16, 30)])
        alive = []
        for s in self.sparks:
            s[6] -= 1
            if s[6] <= 0:
                continue
            s[2], s[3] = s[0], s[1]
            s[0] += s[4] * 1.2 + random.uniform(-0.3, 0.3)
            s[1] += s[5] * 0.6 + random.uniform(-0.3, 0.3)
            alive.append(s)
        self.sparks = alive[:80]

    # ---------- 绘制 ----------
    def _edge(self, sign):
        """一侧（sign=±1）锯齿边点列，锯齿随时间颤动摇摆。"""
        t = self._t()
        op = self._open()
        half = self.max_len
        full = max(40, int(self.max_len * 0.55))
        gap = full * op
        n = self.segs
        out = []
        sway = math.sin(t * 6.0) * 3.0
        for i in range(n + 1):
            p = i / float(n)
            y = int(self.cy - half + 2 * half * p + math.sin(t * 9 + self.phase[i]) * 2)
            taper = 1.0 - (p * 2 - 1) ** 2
            w = gap * max(0.1, taper)
            jitter = self.jx[i] + math.sin(t * 14 + self.phase[i]) * (2 + 4 * op)
            out.append((int(self.cx + sign * w / 2 + jitter + sway), y))
        return out, gap

    def draw(self, surface):
        t = self._t()
        if t <= 0:
            return
        left, _ = self._edge(-1)
        right, _ = self._edge(1)

        # 1) 柔软黑烟柱：先画（在裂缝底下），从裂口向外喷
        for s in self.smoke:
            size = int(s[5])
            k, img = _smoke_by(size)
            fade = min(1.0, (BOSS_SMOKE_LIFE - s[4]) / 10.0)   # 尾段渐隐
            img.set_alpha(int(210 * fade))
            surface.blit(img, (int(s[0] - size / 2), int(s[1] - size / 2)))

        # 2) 能量泄漏衬底：向两侧外扩一圈，先铺暗色"泄漏光"，再填黑虚空
        rim_gap = int(6 + 6 * t)
        rim_pts = []
        for (lx, ly) in left:
            rim_pts.append((lx - rim_gap, ly))
        for (rx, ry) in reversed(right):
            rim_pts.append((rx + rim_gap, ry))
        pygame.draw.polygon(surface, (55, 55, 70), rim_pts)
        # 3) 黑色腹腔：真正的虚空
        pygame.draw.polygon(surface, (0, 0, 0), left + right[::-1])
        # 4) 刃口高光：随开口抖动闪烁
        glow = int(180 + 60 * math.sin(t * 13))
        edge = (max(160, min(255, glow + 60)),
                max(160, min(255, glow + 60)), 250)
        pygame.draw.lines(surface, edge, False, left, 2)
        pygame.draw.lines(surface, edge, False, right, 2)
        # 5) 分叉副裂纹
        half = self.max_len
        for (seg_i, off, ang, blen) in self.branch:
            p = seg_i / float(self.segs)
            y0 = int(self.cy - half + 2 * half * p)
            x0 = int(self.cx + self.jx[seg_i] + math.copysign(40, off))
            dx, dy = math.cos(ang), math.sin(ang)
            pygame.draw.lines(surface, (0, 0, 0), False,
                              [(x0, y0),
                               (int(x0 + dx * blen * 0.5 - dy * 6),
                                int(y0 + dy * blen * 0.5 + dx * 6)),
                               (int(x0 + dx * blen), int(y0 + dy * blen))], 2)
        # 6) 亮色碎屑：被吸进虚空（与黑烟反向，制造纵深对比）
        for s in self.sparks:
            a = max(0.0, min(1.0, s[6] / 30.0))
            col = (int(255 * a), int(230 * a), 255)
            pygame.draw.line(surface, col, (int(s[2]), int(s[3])),
                             (int(s[0]), int(s[1])), 2)