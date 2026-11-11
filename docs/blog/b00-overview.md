# i.MX6ULL 驱动笔记（00）：这个系列写什么

> 系列目录：本文
> 下一篇：[01 把 `insmod` 的 gpio_num 换成设备树](https://blog.csdn.net/longlin101/article/details/170550878)
> 代码仓库：[imx6ull-dht22-pir-drivers](https://github.com/longlin05/imx6ull-dht22-pir-drivers)
> 前置阅读（另一个系列）：[09 i.MX6ULL 驱动：DHT22 IIO + PIR 字符设备](https://blog.csdn.net/longlin101)
> 已发布：https://blog.csdn.net/longlin101/article/details/170550740

---

## 1. 为什么单独开一个系列

前 8 篇写的是 STM32 和 i.MX6ULL 之间的 CAN 诊断与 OTA；第 9 篇拐了个弯，
在 i.MX6ULL 上写了两个内核模块（DHT22 温湿度和 HC-SR501 人体红外）。

那篇解决的是"驱动能跑起来"：单总线时序、交叉编译、`insmod`、sysfs 读数。
但它还是**教科书之外最常见的野路子**——引脚号靠 `insmod` 参数传进去：

```bash
insmod dht22_iio.ko gpio_num=4
insmod pir_gpio.ko gpio_num=9
```

这个系列从"能跑"往下走一步，写真实板子上驱动该怎么落地：

```text
GPIO 由设备树描述，pinctrl 在设备树里复用
platform_driver 在 probe 里自动申请资源
中断、电源、资源释放走内核框架，而不是自己手工申请/释放
```

## 2. 和前面那个系列什么关系

```text
A 系列（前 8 篇 + 09 + 10）    STM32 ↔ i.MX6ULL 的 CAN 诊断、Bootloader、OTA、网关
B 系列（本系列）               i.MX6ULL 上的 Linux 驱动
```

- **09 是两边的桥梁**：它第一次进内核态，但只到"模块能加载"。
- 本系列不重复 09 里已经讲过的东西：单总线时序、工具链、`make -C KDIR M=`、
  模块和板子内核版本怎么对齐。这些没看过的话，先回去看 09。

## 3. 硬件

```text
i.MX6ULL ATK-IMX6U（正点原子），Linux 4.1.15-g3dc0a4b
DHT22   DATA → GPIO1_IO04   VCC 3.3V
HC-SR501 PIR OUT → GPIO1_IO09   VCC 5V
```

PIR 模块没有滤波电容也没有下拉电阻，输出会自己抖；正文里会说明驱动的
消抖和 holdoff 各自兜住了什么，但这是硬件问题，不在这条线上解决。

## 4. 路线图

```text
01 设备树 + platform driver            ← 已完成，代码和实测都有
02 IIO buffer / trigger                计划
03 用 regmap / gpiod 把驱动写规范      计划
04 Buildroot 集成，开机自动加载        计划
```

每篇的原则和前一个系列一样：**没跑过的数字不写，没测过的功能不说通过**。

## 5. 目录

```text
01 把 insmod 的 gpio_num 换成设备树
   板子跑的是哪份 DTB / dtc 反编译重建 / pin 号怎么确定 / 刷入与回退 /
   driver 改造 / 三个 bug / 板上实测
```

代码、设备树构建脚本和测试记录都在仓库里：

```text
drivers/dht22_iio    IIO 驱动
drivers/pir_gpio     PIR 字符设备
dts/                 从板子 DTB 反编译重建的节点与 build.sh
test/                板上测试脚本
docs/                测试记录、设备树调查记录
```

标签：`Linux` `i.MX6ULL` `设备树` `platform driver` `内核模块`
