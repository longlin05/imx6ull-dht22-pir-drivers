# -*- coding: utf-8 -*-
"""b03 配图：开机到摄像头失败的时间线，说明 probe 顺序改变暴露的冲突。"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

DARK = "#1F3864"
GRAY = "#666666"
BLUE = "#2E5C8A"
ORANGE = "#B26A2E"
RED = "#B23A3A"
GREEN = "#2E7D32"

W, H = 13.0, 4.4
HERE = os.path.dirname(os.path.abspath(__file__))

fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, 10)
ax.set_ylim(0.2, 4.8)
ax.axis("off")

# 时间轴
ax.annotate("", xy=(9.7, 2.5), xytext=(0.4, 2.5),
            arrowprops=dict(arrowstyle="-|>", color=DARK, lw=1.6))
ax.text(9.55, 2.15, "启动时间（秒）", ha="right", fontsize=8.2, color=GRAY)

events = [
    (1.2, "内核初始化", "of_platform 建出 dht22 / pir\nplatform_device", BLUE, 1),
    (3.4, "S05 modutils.sh", "读 /etc/modules\nmodprobe dht22_iio / pir_input", GREEN, 1),
    (5.6, "驱动 probe", "dht22 5.58s / pir 5.66s\nGPIO1_IO04 被 dht22 持有", GREEN, 1),
    (7.2, "ov5640 probe", "csi_pwn_rstgrp 要 pin 27\n已被 dht22 占用", RED, -1),
    (9.05, "结果", "setup pinctrl failed\n摄像头不可用", RED, -1),
]


def box(x, y, text, color, w=1.35, h=0.62, size=7.2):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=1.1, edgecolor=color, facecolor="white", zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=size,
            color="#333333", zorder=4, linespacing=1.4)


for x, title, detail, color, side in events:
    y = 2.5
    ax.plot([x], [y], marker="o", markersize=6, color=color, zorder=5)
    ax.plot([x, x], [y, y + side * 0.55], color=color, lw=1.0, zorder=2)
    ax.text(x, y + side * 0.78, title, ha="center", va="bottom" if side > 0 else "top",
            fontsize=8.6, color=DARK, fontweight="bold", zorder=6)
    box(x, y + side * 1.45, detail, color)

plt.tight_layout()
out = os.path.join(HERE, "b03-boot-timeline.png")
plt.savefig(out, dpi=170, bbox_inches="tight", facecolor="white")
print("saved", out)
