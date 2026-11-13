# i.MX6ULL 传感器驱动：DHT22 + PIR（设备树 / platform driver）

在正点原子 ATK-IMX6U（i.MX6ULL，Linux 4.1.15）上写的两个内核模块：

```text
drivers/dht22_iio   温湿度传感器，IIO 子系统
drivers/pir_input    HC-SR501 人体红外，input 子系统设备（EV_KEY + 中断）
```

两个驱动都是 **platform_driver + 设备树**：GPIO 由 DTS 的 `data-gpios` / `irq-gpios`
描述，pinctrl 在 DTS 里配置，`insmod` 不带任何参数。

```text
$ insmod dht22_iio.ko
$ insmod pir_input.ko
[ 2247.998787] dht22 dht22: probed, from device tree
[ 1538.409284] input: pir as /devices/platform/pir/input/input3
[ 1538.436094] pir-input pir: probed, irq=38, key=148, from device tree
```

---

## 1. 硬件接线

```text
DHT22                      i.MX6ULL
  DATA  ──────────────── GPIO1_IO04（全局 gpio 4）
  VCC   ──────────────── 3.3V
  GND   ──────────────── GND
  NC    ──────────────── 不接
  模块自带 4.7k 上拉

HC-SR501 PIR
  OUT   ──────────────── GPIO1_IO09（全局 gpio 9）
  VCC   ──────────────── 5V
  GND   ──────────────── GND
```

> PIR 模块没有滤波电容、也没有 10k 下拉，输出会自己抖。驱动里做了消抖和
> holdoff 兜底，但硬件本身不稳，这一点后面不再展开。

## 2. 目录

```text
drivers/dht22_iio/     DHT22 IIO 驱动 + Makefile
drivers/pir_input/      PIR input 设备 + Makefile
dts/                   设备树改造：厂商 DTB、追加的节点片段、可复现的构建脚本
test/                  板上测试脚本
docs/                  调查记录与测试记录
docs/blog/             系列文章「i.MX6ULL 驱动笔记」（b00 概览、b01 设备树 + platform driver）
```

## 3. 设备树：为什么不是"改源码里的 dts"

板子的 `compatible` 是 `fsl,imx6ull-14x14-evk`，但 DT 里已经有
`alientek,dht11`、`alientek,ds18b20`、`pxp_v4l2` 这些厂商加的节点——
**板子跑的是厂商改过的 EVK DTB**，不是 NXP 原版；而手头的内核源码树是原版，
用它的 dts 重编会把这些节点全丢掉。

所以反过来做：从板子启动分区取出**正在用的 DTB**，`dtc` 反编译后追加节点再编回去。

```text
dts/base/imx6ull-14x14-emmc-4.3-480x272-c.dtb   板子原版，原样保存
dts/b-dht22-pir.dtsi                            追加的节点 + pinctrl
dts/build.sh                                    反编译 → 追加 → 编译 → 自检
```

`build.sh` 有两道自检，不是"编出来就行"：

```text
1. 原 dts 编回去再反编译，必须和原反编译结果逐字节一致
2. 打补丁后再反编译，和原结果 diff 只允许有新增行，不能有删除行
```

本次结果：新增 26 行，删除 0 行，39459 → 39854 字节。

细节（引脚号怎么确定的、为什么没走 `fw_setenv`、刷入和回退）见
[dts/README.md](dts/README.md)，调查过程见
[docs/dts-investigation.md](docs/dts-investigation.md)。

## 4. 构建

交叉工具链用 NXP 4.1.15 SDK，内核树是板子内核 4.1.15-g3dc0a4b 对应的树：

```bash
source /opt/fsl-imx-x11/4.1.15-2.1.0/environment-setup-cortexa7hf-neon-poky-linux-gnueabi

make -C drivers/dht22_iio KDIR=/home/lin/imx6ull/linux-imx-rel_imx_4.1.15_2.1.0_ga
make -C drivers/pir_input  KDIR=/home/lin/imx6ull/linux-imx-rel_imx_4.1.15_2.1.0_ga
```

`.ko` 拷到板子后 `insmod`，**不需要任何参数**。

## 5. 使用

```text
# DHT22
/sys/bus/iio/devices/iio:device0/in_temp_input               温度，0.001°C
/sys/bus/iio/devices/iio:device0/in_humidityrelative_input   湿度，0.001 %RH

# PIR
/dev/input/eventX  EV_KEY / KEY_PROG1（可用 key_code 模块参数改）
                    evtest /dev/input/eventX 直接看事件
                    按下 = 检测到动作，抬起 = 电平回落
```

## 6. 实测（2026-11-09，板子上跑出来的）

| 项目 | 结果 |
|---|---|
| probe 来源 | `from device tree`（不是 module parameter） |
| pinctrl | `pin 27 (GPIO1_IO04): dht22 ... zl_dht22grp`、`pin 32 (GPIO1_IO09): pir ... zl_pirgrp` |
| DHT22 | 19.6 °C / 50.5 %RH |
| PIR 输入设备 | `Name="pir"`，`Handlers=kbd event2`，支持 `EV_KEY` / `KEY_PROG1(148)` |
| PIR 事件 | evtest 抓到按下 → 1.04 s 后抬起（EV_KEY 148 value 1 / 0 + SYN_REPORT） |
| rmmod/insmod | 2 轮循环无 warn / oops |

原始输出见 [docs/test-report-b-drivers.md](docs/test-report-b-drivers.md)。

## 7. 从 v0.1 到 v0.2 修掉的三个 bug

```text
1. dht22_exit() 只打印不注销
   → iio_device_unregister/free/gpio_free 全没调，rmmod 后 GPIO 被占，二次 insmod 必失败
   → 改 platform_driver + devm_* 解决

2. IIO 通道只带 IIO_CHAN_INFO_RAW
   → 只有 in_temp_raw，没有 in_temp_input
   → 加 PROCESSED + SCALE，两套属性都在

3. PIR 只申请上升沿
   → st->level 第一次事件后停在 1，后面只能靠信号抖动偶然复位
   → 改 RISING|FALLING，下降沿只负责清 level
```

## 8. 兼容性

`gpio_num` / `debounce_ms` / `holdoff_ms` 三个模块参数仍然保留，
**没有设备树节点时会自动补一个 platform device**，老用法 `insmod dht22_iio.ko gpio_num=4`
还能用。这条回退路径没有在板上实测（板子现在跑的就是带节点的 DTB）。

## 9. 已知问题：引脚和 LCD 模块撞了

这块板子的 LCD 模块（4.3 寸屏 + 摄像头 + 触摸）把 GPIO1 占得很满，
我们用的两个脚其实都有别的主人在设备树里：

```text
GPIO1_IO04  DHT22 DATA   ← 同时是 ov5640 的 pwn-gpios
GPIO1_IO09  PIR OUT      ← 同时是触摸屏（edt-ft5x06 / goodix）的 IRQ
```

现状（2026-11-13）：

```text
驱动在 /etc/modules 里开机自动加载，所以 DHT22 比摄像头先 probe
→ ov5640 开机会报 "could not request pin 27 ... setup pinctrl failed"
→ 摄像头当前不可用（节点仍然是 status = "okay"，没删）
PIR 能用，因为触摸屏本来 probe 就失败（板上没接触摸）
```

排查结论：GPIO1 这一组里**唯一的空脚是 GPIO1_IO01**（厂商 dht11/ds18b20
示例节点占着，但没有驱动绑定）。如果要恢复摄像头，需要：

```text
1. 把 DHT22 DATA 从 GPIO_4 挪到 GPIO_1（动一根线）
2. 设备树 data-gpios 改 <&gpio1 1 0>，pinctrl 改 0x60 0x2ec
3. 摄像头节点不用动
```

暂时选择保持现状，这个冲突在 `docs/test-report-b-drivers.md` 里也有记录。

## 10. 相关

```text
STM32 + i.MX6ULL CAN 诊断与 OTA（项目 A）
https://github.com/longlin05/stm32-imx6ull-can-diag-ota
```

## License

GPL-2.0，见 [LICENSE](LICENSE)。内核模块直接使用内核内部 API，必须 GPL。
