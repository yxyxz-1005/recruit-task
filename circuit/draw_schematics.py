# -*- coding: utf-8 -*-
"""
画三个电路的电路图（任务书要求「电路图自己画」）。

用 matplotlib 而不是手绘拍照，原因有两个：
  1. 矢量输出放进 README 不会因拍照角度/光线糊掉；
  2. 参数改了可以重跑，图和脚本里的元件值永远一致。

输出：rc_circuit.png / thevenin_circuit.png /
      nmos_circuit.png / nmos_dc.png / nmos_small_signal.png

    python circuit/draw_schematics.py
"""

import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C = "#2C2C2A"      # 导线与元件
MUT = "#5F5E5A"    # 说明文字
BLUE = "#185FA5"   # 强调

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
_ax = None
_fig = None


def newfig(W, H):
    global _ax, _fig
    _fig, _ax = plt.subplots(figsize=(W / 110.0, H / 110.0), dpi=110)
    _ax.set_xlim(0, W)
    _ax.set_ylim(H, 0)          # y 向下增大，跟画图时的直觉一致
    _ax.set_aspect("equal")
    _ax.axis("off")
    _fig.subplots_adjust(0, 0, 1, 1)
    return _fig, _ax


def save(name):
    p = os.path.join(OUT_DIR, name)
    _fig.savefig(p, dpi=110, facecolor="white")
    plt.close(_fig)
    print("  写出", name)


def seg(x1, y1, x2, y2, color=C, lw=1.8, dash=False):
    _ax.plot([x1, x2], [y1, y2], color=color, lw=lw,
             ls="--" if dash else "-", solid_capstyle="round", zorder=2)


def poly(pts, color=C, lw=1.8):
    _ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw,
             solid_joinstyle="round", solid_capstyle="round", zorder=2)


def zig_h(x1, x2, y, amp=6, n=6):
    """水平电阻：两端留直线段，中间来回折"""
    lead = 10
    a, b = x1 + lead, x2 - lead
    step = (b - a) / (n + 1)
    pts = [(x1, y), (a, y)]
    for i in range(1, n + 1):
        pts.append((a + step * i, y - amp if i % 2 == 1 else y + amp))
    pts += [(b, y), (x2, y)]
    poly(pts)


def zig_v(x, y1, y2, amp=6, n=6):
    """垂直电阻"""
    lead = 10
    a, b = y1 + lead, y2 - lead
    step = (b - a) / (n + 1)
    pts = [(x, y1), (x, a)]
    for i in range(1, n + 1):
        pts.append((x - amp if i % 2 == 1 else x + amp, a + step * i))
    pts += [(x, b), (x, y2)]
    poly(pts)


def cap_h(x1, x2, y, ph=26, gap=9):
    """水平放置的电容（两块竖板）"""
    cx = (x1 + x2) / 2.0
    seg(x1, y, cx - gap / 2, y)
    seg(cx - gap / 2, y - ph / 2, cx - gap / 2, y + ph / 2, lw=2.6)
    seg(cx + gap / 2, y - ph / 2, cx + gap / 2, y + ph / 2, lw=2.6)
    seg(cx + gap / 2, y, x2, y)


def cap_v(x, y1, y2, pw=34, gap=9):
    """垂直放置的电容（两块横板）"""
    cy = (y1 + y2) / 2.0
    seg(x, y1, x, cy - gap / 2)
    seg(x - pw / 2, cy - gap / 2, x + pw / 2, cy - gap / 2, lw=2.6)
    seg(x - pw / 2, cy + gap / 2, x + pw / 2, cy + gap / 2, lw=2.6)
    seg(x, cy + gap / 2, x, y2)


def gnd(x, y):
    seg(x, y, x, y + 7)
    seg(x - 15, y + 7, x + 15, y + 7, lw=2.0)
    seg(x - 9, y + 13, x + 9, y + 13, lw=2.0)
    seg(x - 3.5, y + 19, x + 3.5, y + 19, lw=2.0)


def dot(x, y, r=4):
    _ax.add_patch(Circle((x, y), r, color=C, zorder=3))


def term(x, y, r=5.5):
    _ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor=C, lw=1.8, zorder=3))


def src(x, y, r=20):
    _ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor=C, lw=1.8, zorder=3))


def sine_in(x, y, r=20):
    t = np.linspace(-1, 1, 60)
    _ax.plot(x + (r - 6) * t, y - (r - 9) * np.sin(t * np.pi), color=C, lw=1.6, zorder=4)


def square_in(x, y, r=20):
    pts = [(-1, .35), (-.55, .35), (-.55, -.35), (.55, -.35), (.55, .35), (1, .35)]
    _ax.plot([x + (r - 6) * p[0] for p in pts],
             [y - (r - 9) * p[1] for p in pts], color=C, lw=1.6, zorder=4)


def batt_in(x, y, r=20):
    seg(x - 11, y - 6, x + 11, y - 6, lw=2.4)     # 长板 = 正极
    seg(x - 6, y + 6, x + 6, y + 6, lw=2.4)       # 短板 = 负极
    lab(x - 17, y - 5, "+", fs=12)
    lab(x - 17, y + 7, "\u2212", fs=12)


def arrow(x1, y1, x2, y2, color=C, lw=1.6, ms=13):
    _ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=4,
                 arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=ms))


def lab(x, y, s, fs=11, ha="center", va="center", color=C, weight="normal"):
    _ax.text(x, y, s, fontsize=fs, ha=ha, va=va, color=color, weight=weight, zorder=5)


def box(x, y, w, h, label=None):
    _ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=MUT,
                            lw=1.4, linestyle="--", zorder=1))
    if label:
        lab(x + w / 2, y - 15, label, fs=12, color=MUT)


def nmos(xg, ytop, ybot, xlead, xds):
    """
    NMOS 三端符号（增强型，沟道画虚线）。
      xg    : 栅极板所在 x
      ytop/ ybot : 沟道上下端
      xlead : 栅极引线从哪个 x 进来
      xds   : 漏/源引脚拐到哪个 x
    返回 (漏极端子 y, 源极端子 y)
    """
    ymid = (ytop + ybot) / 2.0
    xc = xg + 12
    seg(xg, ytop, xg, ybot, lw=2.2)                    # 栅极板
    seg(xlead, ymid, xg, ymid)                         # 栅极引线
    seg(xc, ytop, xc, ybot, lw=2.2, dash=True)         # 沟道（增强型为虚线）
    seg(xc, ytop, xds, ytop)                           # 漏极横向引出
    seg(xds, ytop, xds, ytop - 14)
    seg(xc, ybot, xds, ybot)                           # 源极横向引出
    seg(xds, ybot, xds, ybot + 14)
    arrow(xds - 4, ybot, xc + 3, ybot)                 # 箭头指向沟道 = NMOS
    return ytop - 14, ybot + 14


# ============================================================
# 图 ①  RC 低通滤波器
# ============================================================
def draw_rc():
    newfig(560, 215)
    ytop, ybot = 60, 150
    src(75, 105, 20); square_in(75, 105, 20)
    seg(75, ytop, 75, 85)
    seg(75, 125, 75, ybot)
    seg(75, ytop, 160, ytop)
    zig_h(160, 260, ytop)
    seg(260, ytop, 440, ytop)
    dot(340, ytop)
    cap_v(340, ytop, ybot)
    seg(75, ybot, 340, ybot)
    gnd(200, ybot)
    term(440, ytop); lab(456, ytop, "Vout", ha="left", fs=12)
    lab(30, 40, "Vin：方波 0 \u2192 5 V", ha="left", fs=11)
    lab(210, 94, "R = 1 k\u03a9", fs=12)
    lab(366, 105, "C = 1 \u00b5F", fs=12, ha="left")
    lab(30, 182, "周期 T = 10 ms（高电平 5 ms，低电平 5 ms）", ha="left", fs=10, color=MUT)
    lab(280, 205, "图 \u2460  RC 低通滤波器电路图（自绘）", fs=12, color=MUT)
    save("rc_circuit.png")


# ============================================================
# 图 ②  含源二端网络（标注端口 a、b）+ 戴维南等效电路
# ============================================================
def draw_thevenin():
    newfig(780, 250)
    ytop, ybot = 70, 180

    # 左：原网络
    src(70, 125, 20); batt_in(70, 125, 20)
    seg(70, ytop, 70, 105)
    seg(70, 145, 70, ybot)
    seg(70, ytop, 150, ytop)
    zig_h(150, 250, ytop)
    seg(250, ytop, 340, ytop)
    dot(340, ytop)
    zig_v(340, ytop, ybot)          # R2
    zig_h(340, 440, ytop)           # R3
    seg(440, ytop, 490, ytop)
    seg(70, ybot, 490, ybot)
    gnd(200, ybot)
    term(490, ytop); lab(490, 50, "a", fs=13, weight="bold")
    term(490, ybot); lab(490, 204, "b", fs=13, weight="bold")
    box(40, 40, 420, 160, "含源二端网络")
    lab(98, 125, "Vs = 12 V", ha="left", fs=11)
    lab(200, 50, "R1 = 1 k\u03a9", fs=11)
    lab(390, 50, "R3 = 2 k\u03a9", fs=11)
    lab(354, 128, "R2 = 2 k\u03a9", ha="left", fs=11)

    # 右：等效电路
    src(600, 125, 20); batt_in(600, 125, 20)
    seg(600, ytop, 600, 105)
    seg(600, 145, 600, ybot)
    seg(600, ytop, 655, ytop)
    zig_h(655, 725, ytop)
    seg(725, ytop, 745, ytop)
    seg(600, ybot, 745, ybot)
    gnd(680, ybot)
    term(745, ytop); lab(745, 50, "a", fs=13, weight="bold")
    term(745, ybot); lab(745, 204, "b", fs=13, weight="bold")
    box(570, 40, 190, 160, "戴维南等效电路")
    lab(628, 125, "V_th = 8.000 V", ha="left", fs=11)
    lab(690, 94, "R_th = 2.667 k\u03a9", fs=11)

    arrow(508, 125, 552, 125, color=MUT, lw=1.6, ms=15)
    lab(530, 108, "等效", fs=11, color=MUT)

    lab(390, 236, "图 \u2461  含源二端网络（标注端口 a、b）与戴维南等效电路（自绘）",
        fs=12, color=MUT)
    save("thevenin_circuit.png")


# ============================================================
# 图 ③-a  NMOS 共源放大电路（完整）
# ============================================================
def draw_nmos_full():
    newfig(620, 330)
    yvdd, ygate, ygnd = 50, 185, 280

    seg(270, yvdd, 380, yvdd)
    seg(330, yvdd, 330, 34)
    lab(330, 24, "VDD = 5 V", fs=11)

    seg(270, yvdd, 270, 60)
    zig_v(270, 60, 180)
    seg(270, 180, 270, ygate)
    dot(270, ygate)
    seg(270, ygate, 270, 205)
    zig_v(270, 205, 272)
    seg(270, 272, 270, ygnd)

    src(110, 225, 18); sine_in(110, 225, 18)
    seg(110, ygate, 110, 207)
    seg(110, 243, 110, ygnd)
    seg(110, ygate, 180, ygate)
    cap_h(180, 270, ygate)

    d_y, s_y = nmos(348, 158, 212, 270, 380)

    seg(380, yvdd, 380, 60)
    zig_v(380, 60, d_y)
    seg(380, d_y, 480, d_y)
    dot(380, d_y)
    term(480, d_y); lab(494, d_y, "Vout", ha="left", fs=12)
    seg(380, s_y, 380, ygnd)

    seg(110, ygnd, 380, ygnd)
    gnd(320, ygnd)

    lab(110, 156, "Vi = 10 mV（1 kHz）", fs=11)
    lab(225, 158, "Cb1", fs=11)
    lab(258, 110, "Rg1 = 60 k\u03a9", ha="right", fs=11)
    lab(258, 240, "Rg2 = 40 k\u03a9", ha="right", fs=11)
    lab(396, 95, "Rd = 2 k\u03a9", ha="left", fs=11)
    lab(336, 234, "M1", fs=11)
    lab(310, 318, "图 \u2462-a  NMOS 共源放大电路（自绘，元件参数按题卡给定）",
        fs=12, color=MUT)
    save("nmos_circuit.png")


# ============================================================
# 图 ③-b  直流通路
# ============================================================
def draw_nmos_dc():
    newfig(620, 310)
    yvdd, ygate, ygnd = 50, 195, 260

    seg(250, yvdd, 430, yvdd)
    seg(340, yvdd, 340, 34)
    lab(340, 24, "VDD = 5 V", fs=11)

    seg(250, yvdd, 250, 60)
    zig_v(250, 60, 175)
    seg(250, 175, 250, ygate)
    dot(250, ygate)
    seg(250, ygate, 250, 212)
    zig_v(250, 212, 250)
    seg(250, 250, 250, ygnd)

    d_y, s_y = nmos(398, 168, 222, 250, 430)

    seg(430, yvdd, 430, 60)
    zig_v(430, 60, d_y)
    dot(430, d_y)
    seg(430, s_y, 430, ygnd)
    seg(250, ygnd, 430, ygnd)
    gnd(340, ygnd)

    lab(262, 110, "Rg1 = 60 k\u03a9", ha="left", fs=11)
    lab(262, 235, "Rg2 = 40 k\u03a9", ha="left", fs=11)
    lab(442, 95, "Rd = 2 k\u03a9", ha="left", fs=11)
    lab(442, 146, "V_DS = 3.295 V", ha="left", fs=11, color=BLUE)
    lab(442, 240, "I_D = 0.853 mA", ha="left", fs=11, color=BLUE)
    lab(238, ygate, "V_G = 2 V", ha="right", fs=11, color=BLUE)

    lab(30, 112, "直流通路：", ha="left", fs=11, color=MUT)
    lab(30, 132, "Cb1 对直流开路，", ha="left", fs=11, color=MUT)
    lab(30, 152, "输入支路断开；", ha="left", fs=11, color=MUT)
    lab(30, 172, "栅极不取电流，", ha="left", fs=11, color=MUT)
    lab(30, 192, "故 V_G 由分压", ha="left", fs=11, color=MUT)
    lab(30, 212, "电阻直接决定", ha="left", fs=11, color=MUT)
    lab(310, 296, "图 \u2462-b  直流通路（电容视为开路）", fs=12, color=MUT)
    save("nmos_dc.png")


# ============================================================
# 图 ③-c  小信号等效模型
# ============================================================
def draw_nmos_ac():
    newfig(600, 300)
    yd, yg = 100, 240

    src(90, 170, 20); sine_in(90, 170, 20)
    seg(90, yd, 90, 150)
    seg(90, 190, 90, yg)
    seg(90, yd, 160, yd)
    dot(160, yd)
    dot(160, yg)
    seg(160, 112, 160, 228, color=MUT, lw=1.4, dash=True)
    lab(170, 170, "v_gs", ha="left", fs=11)
    lab(170, 116, "+", fs=13)
    lab(170, 224, "\u2212", fs=13)

    src(250, 170, 24)
    seg(250, yd, 250, 146)
    arrow(250, 148, 250, 192)
    seg(250, 194, 250, yg)
    lab(250, 210, "gm\u00b7v_gs", fs=11)

    zig_v(340, yd, yg)
    lab(352, 170, "ro = 62.5 k\u03a9", ha="left", fs=11)

    seg(250, yd, 480, yd)
    seg(480, yd, 480, 110)
    zig_v(480, 110, 228)
    seg(480, 228, 480, yg)
    lab(492, 170, "Rd = 2 k\u03a9", ha="left", fs=11)

    seg(300, yd, 300, 66)
    term(300, 66); lab(300, 50, "vout", fs=12)

    seg(90, yg, 480, yg)
    gnd(200, yg)

    lab(160, 84, "G", fs=11)
    lab(160, 258, "S", fs=11)
    lab(258, 84, "D", fs=11)
    lab(58, 170, "vin", ha="right", fs=11)
    lab(300, 286,
        "图 \u2462-c  小信号等效模型（低频：Cb1 短路、VDD 视为交流接地）",
        fs=12, color=MUT)
    save("nmos_small_signal.png")


if __name__ == "__main__":
    print("绘制电路图：")
    draw_rc()
    draw_thevenin()
    draw_nmos_full()
    draw_nmos_dc()
    draw_nmos_ac()
    print("完成，输出在 circuit/ 目录")
