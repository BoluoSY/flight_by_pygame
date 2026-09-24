# -*- coding: utf-8 -*-
"""全局配置：窗口、颜色、速度等统一放这里，方便修改。"""

# ---------- 桌面透明窗口相关 ----------
KEY_COLOR = (255, 0, 255)   # 品红 = 透明 / 鼠标穿透区域，请勿让飞机用到这个颜色
SPEED     = 8               # 移动速度（像素/帧）
FPS       = 60

# ---------- 联机 ----------
# 客户端连接服务器的地址：外网联机填"内网穿透工具给的外网地址"（不是本机IP）
SERVER_HOST = "127.0.0.1"
# 服务器监听地址：0.0.0.0 = 监听所有网卡（外网联机必须用这个，含穿透转发）
SERVER_BIND = "0.0.0.0"
SERVER_PORT = 8888          # 端口（用穿透时，客户端这边填"穿透开放的公网端口"）
NICKNAME    = ""          # 你的昵称（改这里自定义）
SEND_RATE   = 30            # 每秒向服务器上报几次自己坐标

# ---------- 飞机样式 ----------
PLANE_SIZE = 30             # 每架飞机所在方形贴图边长
PLAYER_COLOR  = (0, 180, 255)   # 我的飞机颜色（青蓝）
FAKE_COLORS   = [                # 假玩家的颜色（后面替换成真玩家）
    (255, 80, 80),
    (80, 255, 120),
    (180, 80, 255),
]
NAME_COLOR = (255, 255, 255)  # 名字标签颜色

# ---------- 飞机动画 ----------
IDLE_BOB    = 4            # 待机上下浮动幅度（像素）
IDLE_BREATH = 0.04         # 待机呼吸缩放幅度
FLAME_LEN   = 12           # 飞行时引擎尾焰基础长度（像素）
FLAME_FLICK = 4            # 尾焰长度抖动量（像素）
TURN_TILT   = 6            # 左右移动时侧倾角度（度）

# ---------- 爆炸 ----------
DEATH_SIZE = 60             # 爆炸贴图边长（飞机被击中的爆炸图）

# ---------- 怪物动画/行为 ----------
MONSTER_SIZE     = 28            # 怪物贴图边长
MONSTER_SPEED    = 1.3          # 怪物移动速度（像素/帧，向主角靠近）
MONSTER_LIMIT    = 10            # 场上最多同时存在的怪物数
MONSTER_INTERVAL = 90            # 每隔多少帧尝试生成一只（受上限约束）
MONSTER_WAVE     = 1.5           # S形走位：sin 摆动幅度（像素）
MONSTER_WAVEF    = 0.25          # S形走位：摆动频率（弧度/帧）
FLANK_RANGE      = 90            # 怪小于此距离（到主角）时进入"绕后"阶段
FLANK_OFFSET     = 70            # 绕后：目标点相对主角的反向偏移距离
MONSTER_DEATH_SIZE = 46          # 怪死亡贴图边长
MONSTER_DEATH_TIME = 30          # 怪死亡效果停留的帧数（30帧≈0.5秒，然后消失）
RESPAWN_INVINCIBLE = 45          # 重生后短暂无敌帧数（≈0.75秒），防止出生点有怪立即再死

# ---------- 血量/伤害（内置血量系统；血量不显示在屏幕）----------
PLAYER_MAX_HP      = 30    # 主角最大血量
PLAYER_HIT_INVINCIBLE = 60   # 受击后无敌闪烁帧数（≈1秒），期间免伤
MONSTER_HP         = 10    # 普通怪血量
MONSTER_DAMAGE     = 10    # 怪撞到主角一次的伤害（每次减10血）
BULLET_DAMAGE      = 10    # 每发子弹伤害（打中怪减10血）

# ---------- 子弹 ----------
BULLET_SIZE  = 20            # 子弹贴图边长
BULLET_SPEED = 14            # 子弹速度（像素/帧）

# ---------- Boss ----------
BOSS_W         = 170          # Boss 贴图宽（素材比例 17:13）
BOSS_H         = 130          # Boss 贴图高
BOSS_OPEN_T    = 70           # 裂开阶段帧数（屏幕右侧先撕裂，再出场）
BOSS_CRACK_LEN = 180          # 右侧裂缝向外撕开的长度（像素）
BOSS_INTRO_T   = 120          # 入场动画帧数（≈2秒，从屏幕右侧滑入+淡入）
BOSS_MAX_HP    = 100          # Boss 血量（可攻击阶段被子弹消耗）
BOSS_X_RATIO   = 0.72         # 入场目标 x = 屏幕宽 * 该比例
BOSS_Y_RATIO   = 0.30         # 入场目标 y = 屏幕高 * 该比例
# Boss 在屏幕右侧 1/3 区域内游走
BOSS_LEFT_LIMIT  = 0.666      # 活动区左边界 = 屏幕宽 * 该比例（不能越过屏幕中线往左）
BOSS_MOVE_SPEED  = 2.2        # Boss 游走速度（像素/帧）
BOSS_MOVE_DY     = 120        # 纵向游走带（围绕目标 ty 上下浮动 ±该值）
# Boss 发射的黑色炮弹（打中主角 20 伤害）
BOSS_FIRE_INTERVAL  = 60      # 隔多少帧发射一发
BOSS_BULLET_SPEED   = 6.5     # 炮弹飞向主角的速度
BOSS_BULLET_DAMAGE  = 20      # 打中主角扣的血
BOSS_BULLET_RADIUS  = 9       # 炮弹半径（热黑球）
# 声波状黑雾圈：从本体一圈一圈向外扩散（像声波放出去再散尽）
BOSS_RING_INTERVAL = 45       # 扩散频率：隔多少帧发出一圈（越小越密）
BOSS_RING_MAX      = 480      # 范围：一圈雾扩到的最大半径（再远就散尽）
BOSS_RING_SPEED    = 3.2      # 雾圈每帧向外扩展的像素
BOSS_RING_FADE     = 160      # 一圈雾从发出到散尽（＞RING_MAX/SPEED 才能铺满整圈）
# 撕裂时往外喷的黑色物质（柔软翻涌的黑烟，体量感来自预渲染径向渐变的烟团贴图）
BOSS_SMOKE_RATE = 3           # 每帧从裂缝喷出的黑烟团数（越大烟柱越浓）
BOSS_SMOKE_SPEED = 3.0        # 烟向外喷的初速（越大窜得越远越猛）
BOSS_SMOKE_LIFE = 42          # 一团烟的寿命（帧数，越长烟柱拖得越远）
BOSS_SMOKE_MAX  = 150         # 同时存活烟团上限（防止拖慢）
BOSS_SMOKE_BURSTS = 2         # 裂缝破裂成几次喷发；Boss 在第 2 次喷黑雾时从缝里出来