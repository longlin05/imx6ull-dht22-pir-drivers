# 测试记录：platform driver + 设备树 + PIR input 改造

> 日期：2026-11-09（v0.2）、2026-11-13（v0.3 PIR 改 input）
> 板子：ATK-IMX6U（i.MX6ULL），Linux 4.1.15-g3dc0a4b
> 内核模块 commit：`c89fcf7`
> 设备树：`dts/` 下从板子 DTB 反编译后追加节点重编，已刷入 SD 启动分区

原则同 `docs/test-report.md`：下面的数字都来自板子上的原始输出，没有推测。

---

## 1. 设备树（刷入并重启后）

```text
/proc/device-tree/dht22   compatible / data-gpios / pinctrl-0 / status 齐全
/proc/device-tree/pir     compatible / irq-gpios  / pinctrl-0 / status 齐全
/sys/bus/platform/devices 出现 dht22、pir
/sys/class/graphics/fb0/modes = U:480x272p-56   ← 屏参没被破坏
```

启动日志里 `mxsfb ... failed to find mxc display driver`、`ap3216c ... failed`、
`fsl-quadspi ... probe failed` 与刷 DTB 之前完全一致，不是这次引入的。

## 2. 模块加载（不带任何参数）

```text
$ insmod /home/root/dht22_iio/dht22_iio.ko
$ insmod /home/root/pir_gpio/pir_gpio.ko
[ 2247.998787] dht22 dht22: probed, from device tree
[ 2248.037562] pir pir: probed, irq=38, initial=1, from device tree
```

`from device tree` 而不是 `from module parameter`，说明 v0.1 的
`insmod xxx.ko gpio_num=N` 已经不需要了。

## 3. pinctrl 认领

```text
pin 27 (MX6UL_PAD_GPIO1_IO04): dht22 (GPIO UNCLAIMED) function imx6ul-evk group zl_dht22grp
pin 32 (MX6UL_PAD_GPIO1_IO09): pir   (GPIO UNCLAIMED) function imx6ul-evk group zl_pirgrp
```

两个脚在没加载驱动前是 `MUX UNCLAIMED`，加载后归属正确 ——
说明 pinctrl-0 从设备树里真的生效了，不是碰巧的默认复用。

## 4. DHT22 IIO

```text
$ cat /sys/bus/iio/devices/iio:device0/in_temp_input
19600
$ cat /sys/bus/iio/devices/iio:device0/in_humidityrelative_input
50500
$ cat .../in_temp_raw      19600
$ cat .../in_temp_scale    1
```

19.6 °C / 50.5 %RH。属性列表：

```text
in_temp_input in_temp_raw in_temp_scale
in_humidityrelative_input in_humidityrelative_raw in_humidityrelative_scale
```

## 5. PIR 字符设备

中断：

```text
$ grep 38: /proc/interrupts
 38:        191  gpio-mxc   9 Edge      pir-out
```

read（60 s 窗口，`timeout 60 cat /dev/pir`）：

```text
1
1
1
1
1
```

同 60 s 内中断计数 178 → 191（双沿，约 6 个脉冲 5 次事件，holdoff 3 s 生效）。

poll（板子上用 python3 `select.select()`，测试脚本 `test/pir_poll_test.py`）：

```text
event 1 at 47.5s data=b'1\n'
event 2 at 51.3s data=b'1\n'
event 3 at 58.0s data=b'1\n'
total events=3
```

前 47 s 房间里没人动，传感器不出事件；挥手之后 select() 立刻返回。
间隔 3.8 s / 6.7 s，与 holdoff=3000 ms 吻合。

## 6. rmmod / insmod 循环

```text
cycle 1 ok
cycle 2 ok
dmesg 中 "probed, from device tree" 共 3 条（1 次初始 + 2 次循环）
dmesg 无 warn / oops / call trace
```

v0.1 的 `dht22_exit()` 只打印一句就返回，`iio_device_unregister()`、
`iio_device_free()`、`gpio_free()` 都没调，rmmod 之后 GPIO 一直被占，
第二次 insmod 必然失败。改成 platform_driver + `devm_*` 之后不再出现。

---

## 7. 结论

| 验收项 | 结果 |
|---|---|
| 不需要 gpio_num | **通过**（probe 日志 `from device tree`） |
| dmesg 有 probe | **通过** |
| DHT22 读数正常 | **通过**（19.6 °C / 50.5 %RH） |
| PIR poll/read 正常 | **通过**（read 5 次事件；select 3 次事件） |
| rmmod/insmod 不 oops | **通过**（2 轮循环无告警） |

## 8. 遗留

```text
poll 只在“人挥手”的时候验证过，没有做自动化的事件注入测试
PIR 硬件依旧没滤波电容、没 10k 下拉，长时间读数仍可能抖
DHT22 的 2 s 最小采样间隔内返回的是缓存值，没有做时间戳统计
设备树回退路径（没有 DT 节点时用 gpio_num）没有在板上实测，
  因为板子现在跑的就是带节点的 DTB
```

---

# 附：v0.3 PIR 从 misc 字符设备改成 input 设备（2026-11-13）

## 背景

原计划是给 DHT22 做 IIO 触发缓冲，摸底发现板子内核没开这套机制：

```text
$ zcat /proc/config.gz | grep -E "^CONFIG_IIO"
CONFIG_IIO=y
# CONFIG_IIO_BUFFER is not set
# CONFIG_IIO_TRIGGER is not set
```

要达到 buffer 只能重编厂商内核，风险不可控，所以改用 input 子系统
（板上 `CONFIG_INPUT=y`、`CONFIG_INPUT_EVDEV=y`，`/usr/bin/evtest` 已装）。

## 驱动

```text
compatible 沿用 "zulong,pir"，设备树不用改、不用重启、不用重刷 DTB
devm_input_allocate_device + input_register_device
input_set_capability(EV_KEY, KEY_PROG1)，key_code 模块参数可改
threaded IRQ 双沿：上升沿报按下，下降沿报抬起，中间 input_sync()
```

## 加载

```text
[ 1538.409284] input: pir as /devices/platform/pir/input/input3
[ 1538.436094] pir-input pir: probed, irq=38, key=148, from device tree

$ grep -A5 'Name="pir"' /proc/bus/input/devices
N: Name="pir"
P: Phys=pir/input0
S: Sysfs=/devices/platform/pir/input/input3
H: Handlers=kbd event2
B: PROP=0
```

`Handlers=kbd` 是因为上报的是 `EV_KEY`，内核按键盘类给它挂了 kbd handler，
真正读事件走 `event2`。

## evtest 原始事件（90 秒窗口）

```text
Event: time 1794058626.541986, type 1 (EV_KEY), code 148 (KEY_PROG1), value 1
Event: time 1794058626.541986, -------------- SYN_REPORT ------------
Event: time 1794058627.581936, type 1 (EV_KEY), code 148 (KEY_PROG1), value 0
Event: time 1794058627.581936, -------------- SYN_REPORT ------------
...
```

统计（原始日志 `test/records/20261113-pir-input-evtest.log`，用 python 解析）：

```text
按下 / 抬起次数     7 / 7（成对，无孤儿抬起）
按下次间隔          14.29  3.20  3.38  4.49  4.22  3.12 秒
按下到抬起时长      1.04  1.04  1.04  1.04  1.04  1.05  1.04 秒
```

结论：

```text
最小间隔 3.12 s ≥ holdoff 3 s    → holdoff 生效，重复触发被压住
按下时长稳定在 1.04 s 左右        → 与 HC-SR501 输出高电平宽度一致
```

## rmmod / insmod

```text
[ 1675.143379] pir: unloaded
[ 1676.185805] input: pir as /devices/platform/pir/input/input4
[ 1676.196642] pir-input pir: probed, irq=38, key=148, from device tree
dmesg 无 warn / oops
```

`input3` → `input4` 说明旧输入设备确实被 devm 回收并重新注册，
`event2` 编号复用（event0/1 是 snvs-powerkey 和 gpio_keys）。

## 未验证

```text
没有做"未加载驱动时 /dev/input/event2 不存在"这类反向检查
KEY_PROG1 只是自定按键，没有接任何用户态程序做端到端联动
```

---

# 附二：开机自动加载（v0.4，2026-11-13）

## 做法

这块板子的 rootfs 是 Yocto（`Freescale i.MX Release Distro 4.1.15-2.1.0`），
init 是 sysvinit，没有 systemd、没有包管理器，但有：

```text
/etc/init.d/modutils.sh   开机读 /etc/modules，对每一行跑 modprobe
/sbin/depmod /sbin/modprobe
/lib/modules/4.1.15-g3dc0a4b/modules.dep
```

所以走它原生那条路：

```bash
mkdir -p /lib/modules/$(uname -r)/extra
cp dht22_iio.ko pir_input.ko /lib/modules/$(uname -r)/extra/
depmod -a
printf '# i.MX6ULL 传感器驱动
dht22_iio
pir_input
' > /etc/modules
```

Makefile 里补了 `install` 目标（走内核的 `modules_install`，
交叉编译时用 `INSTALL_MOD_PATH=` 指定 staged rootfs）。

## 重启后

```text
[    5.583432] dht22 dht22: probed, from device tree
[    5.624236] input: pir as /devices/platform/pir/input/input3
[    5.661232] pir-input pir: probed, irq=38, key=148, from device tree

in_temp_input = 20000          （20.0 °C）
/proc/bus/input/devices: Name="pir" Handlers=kbd event2
```

不用再手动 `insmod`。

## 副作用：暴露了引脚冲突

自动加载把 DHT22 的 probe 提前到 rcS 阶段（5.58 s），比摄像头早，
于是设备树里两个节点抢同一个引脚的矛盾第一次显形：

```text
[ 6.38] imx6ul-pinctrl: could not request pin 27 (MX6UL_PAD_GPIO1_IO04)
        from group csi_pwn_rstgrp on device 20e0000.iomuxc
[ 6.48] ov5640 1-003c: Error applying setting, reverse things back
[ 7.01] ov5640 1-003c: setup pinctrl failed
```

反查 DTS：

```dts
ov5640@3c {
    pwn-gpios = <&gpio1 4 GPIO_ACTIVE_LOW>;   /* 同一个脚 */
    rst-gpios = <&gpio1 2 0>;
    status = "okay";
};
```

结论与后续方案写在仓库 README 第 9 节。当前选择：保持现状，
摄像头节点不删，DHT22 继续占 GPIO1_IO04。

## 这一节真正学到的东西

```text
1. 判断某个 GPIO 能不能用，只看 pinmux-pins 的 "MUX UNCLAIMED" 不够，
   要去 DTS 里反查所有 *-gpios 引用（这个坑 01 里就埋下了，现在才炸）
2. 手动 insmod 的顺序是"人决定的"，开机自动加载的顺序是内核决定的，
   后者会把时序假设全部打出来
```
