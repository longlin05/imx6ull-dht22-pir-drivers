# -*- coding: utf-8 -*-
"""b01 配图：设备树节点 → 平台设备 → 用户空间接口。"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

DARK = "#1F3864"
BLUE = "#2E5C8A"
LIGHT = "#EAF1F9"
GRAY = "#666666"
ORANGE = "#B26A2E"
ORANGE_BG = "#FBF0E6"
GREEN = "#2E7D32"
GREEN_BG = "#EAF5EA"

W, H = 14.6, 7.6
HERE = os.path.dirname(os.path.abspath(__file__))


def box(ax, x, y, w, h, title, lines=None, fc=LIGHT, ec=BLUE, lw=1.4,
        title_size=10.2, line_size=8.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.07",
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h - 0.17, title, ha="center", va="top",
            fontsize=title_size, color=DARK, fontweight="bold", zorder=3)
    if lines:
        ax.text(x + w / 2, y + h - 0.50, "\n".join(lines), ha="center", va="top",
                fontsize=line_size, color="#333333", linespacing=1.55, zorder=3)


def arrow(ax, x1, y1, x2, y2, color=BLUE, lw=1.5):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
        linewidth=lw, color=color, zorder=1))


def label(ax, x, y, text, color=GRAY, size=7.8):
    ax.text(x, y, text, ha="center", va="center", fontsize=size, color=color,
            zorder=4, bbox=dict(boxstyle="round,pad=0.22", fc="white",
                                ec="none", alpha=0.9))


fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

for x, text in ((2.4, "设备树（DTS / DTB）"), (7.4, "内核"), (12.4, "用户空间")):
    ax.text(x, 7.15, text, ha="center", fontsize=11.2, color=DARK,
            fontweight="bold")

# ---------------- DHT22 ----------------
box(ax, 0.5, 4.45, 3.8, 2.35, "dht22 节点",
    ['compatible = "zulong,dht22"',
     "data-gpios = <&gpio1 4 0>",
     "pinctrl-0 = <&pinctrl_dht22>"])

box(ax, 5.0, 4.45, 4.9, 2.35, "platform_device  dht22",
    ["of_match_table → dht22_probe()",
     "pinctrl_bind_pins() 应用 pinctrl-0",
     "devm_gpiod_get(\"data\") → GPIO1_IO04",
     "iio_device_register()"],
    fc=ORANGE_BG, ec=ORANGE)

box(ax, 10.6, 4.55, 3.6, 2.15, "sysfs",
    ["/sys/bus/iio/devices/",
     "  iio:device0/in_temp_input",
     "  iio:device0/in_humidityrelative_input",
     "  iio:device0/in_temp_raw"],
    fc=GREEN_BG, ec=GREEN, title_size=9.6, line_size=7.4)

arrow(ax, 4.3, 5.65, 5.0, 5.65)
label(ax, 4.65, 5.95, "dtc")
arrow(ax, 9.9, 5.65, 10.6, 5.65)
label(ax, 10.25, 5.95, "注册")

# ---------------- PIR ----------------
box(ax, 0.5, 1.35, 3.8, 2.35, "pir 节点",
    ['compatible = "zulong,pir"',
     "irq-gpios = <&gpio1 9 0>",
     "pinctrl-0 = <&pinctrl_pir>"])

box(ax, 5.0, 1.35, 4.9, 2.35, "platform_device  pir",
    ["of_match_table → pir_probe()",
     "pinctrl_bind_pins() 应用 pinctrl-0",
     "devm_gpiod_get(\"irq\") → GPIO1_IO09",
     "gpiod_to_irq() → irq 38",
     "devm_request_threaded_irq()"],
    fc=ORANGE_BG, ec=ORANGE)

box(ax, 10.6, 1.45, 3.6, 2.15, "/dev/pir（misc）",
    ["read()  阻塞到一次事件",
     "poll()  POLLIN",
     "  线程半部消抖 + holdoff",
     "/sys/class/misc/pir/enable"],
    fc=GREEN_BG, ec=GREEN, title_size=9.6, line_size=7.4)

arrow(ax, 4.3, 2.55, 5.0, 2.55)
label(ax, 4.65, 2.85, "dtc")
arrow(ax, 9.9, 2.55, 10.6, 2.55)
label(ax, 10.25, 2.85, "注册")

# ---------------- 说明 ----------------
ax.text(0.5, 0.62,
        "pinctrl 组：zl_dht22grp = <0x6c 0x2f8 … 0x17059>（MX6UL_PAD_GPIO1_IO04，ALT5）　"
        "zl_pirgrp = <0x80 0x30c … 0x17059>（MX6UL_PAD_GPIO1_IO09，ALT5）",
        ha="left", va="center", fontsize=7.8, color="#333333")
ax.text(0.5, 0.25,
        "判据：加载驱动前 pin 27/32 为 MUX UNCLAIMED，加载后归 dht22/pir"
        "（/sys/kernel/debug/pinctrl/20e0000.iomuxc/pinmux-pins）",
        ha="left", va="center", fontsize=7.8, color=GRAY)

plt.tight_layout()
out = os.path.join(HERE, "b01-dt-path.png")
plt.savefig(out, dpi=170, bbox_inches="tight", facecolor="white")
print("saved", out)
