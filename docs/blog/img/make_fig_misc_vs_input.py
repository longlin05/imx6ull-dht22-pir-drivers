# -*- coding: utf-8 -*-
"""b02 配图：misc 字符设备 vs input 子系统的数据通路对比。"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

DARK = "#1F3864"
GRAY = "#666666"
BLUE = "#2E5C8A"
BLUE_BG = "#EAF1F9"
ORANGE = "#B26A2E"
ORANGE_BG = "#FBF0E6"
GREEN = "#2E7D32"
GREEN_BG = "#EAF5EA"

W, H = 14.0, 7.2
HERE = os.path.dirname(os.path.abspath(__file__))


def box(ax, x, y, w, h, title, sub=None, fc=BLUE_BG, ec=BLUE, title_size=9.6,
        sub_size=7.6):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=2))
    if sub:
        ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top",
                fontsize=title_size, color=DARK, fontweight="bold", zorder=3)
        ax.text(x + w / 2, y + h - 0.52, sub, ha="center", va="top",
                fontsize=sub_size, color="#333333", linespacing=1.45, zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=title_size, color=DARK, fontweight="bold", zorder=3)


def arrow(ax, x1, y1, x2, y2, color=BLUE, ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
        linewidth=1.5, color=color, linestyle=ls, zorder=1))


fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

ax.text(0.4, 6.85, "v0.2  misc 字符设备（自己定义接口）", fontsize=10.5,
        color=ORANGE, fontweight="bold")
ax.text(0.4, 3.45, "v0.3  input 子系统（标准接口）", fontsize=10.5,
        color=GREEN, fontweight="bold")

# ---------- v0.2 行 ----------
y0 = 4.85
h0 = 1.35
box(ax, 0.4, y0, 2.1, h0, "PIR OUT", "GPIO1_IO09")
box(ax, 3.0, y0, 2.1, h0, "gpio-mxc", "irq 38")
box(ax, 5.6, y0, 2.4, h0, "驱动", "timer 消抖\nholdoff + wake_up")
box(ax, 8.5, y0, 2.2, h0, "/dev/pir", "misc_register", fc=ORANGE_BG, ec=ORANGE)
box(ax, 11.2, y0, 2.4, h0, "用户态", "自己 read() 解析 \"1\\n\"",
    fc=ORANGE_BG, ec=ORANGE)

for x in (2.5, 5.1, 8.0, 10.7):
    arrow(ax, x, y0 + h0 / 2, x + 0.5, y0 + h0 / 2, color=ORANGE)

ax.text(0.45, 4.45,
        "接口是私有的：换一个驱动，用户态就得改解析代码",
        fontsize=7.8, color=GRAY)

# ---------- v0.3 行 ----------
y1 = 1.55
h1 = 1.35
box(ax, 0.4, y1, 2.1, h1, "PIR OUT", "GPIO1_IO09")
box(ax, 3.0, y1, 2.1, h1, "gpio-mxc", "irq 38")
box(ax, 5.6, y1, 2.4, h1, "驱动", "threaded IRQ 双沿\ninput_report_key")
box(ax, 8.5, y1, 2.2, h1, "input core", "EV_KEY / KEY_PROG1",
    fc=GREEN_BG, ec=GREEN)
box(ax, 11.2, y1, 2.4, h1, "evdev", "evtest / 上层输入栈",
    fc=GREEN_BG, ec=GREEN)

for x in (2.5, 5.1, 8.0, 10.7):
    arrow(ax, x, y1 + h1 / 2, x + 0.5, y1 + h1 / 2, color=GREEN)

ax.text(0.45, 1.15,
        "接口是标准的：/dev/input/event2，evtest、udev、libinput 都能直接用",
        fontsize=7.8, color=GRAY)

ax.text(0.45, 0.45,
        "同一份硬件、同一份设备树，只换驱动实现；"
        "compatible 仍是 zulong,pir，所以不用重刷 DTB",
        fontsize=8.2, color=DARK)

plt.tight_layout()
out = os.path.join(HERE, "b02-misc-vs-input.png")
plt.savefig(out, dpi=170, bbox_inches="tight", facecolor="white")
print("saved", out)
