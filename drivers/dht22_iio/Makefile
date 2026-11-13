obj-m += dht22_iio.o

KDIR ?= /home/lin/imx6ull/linux-imx-rel_imx_4.1.15_2.1.0_ga
ARCH ?= arm
CROSS_COMPILE ?= arm-poky-linux-gnueabi-

# 安装到 rootfs 时用：make install INSTALL_MOD_PATH=/tmp/stage
# 不带 INSTALL_MOD_PATH 就是装进本机（交叉编译时一般不要这样）
INSTALL_MOD_PATH ?=

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) modules

install:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
		INSTALL_MOD_PATH=$(INSTALL_MOD_PATH) modules_install

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) clean

.PHONY: all install clean
