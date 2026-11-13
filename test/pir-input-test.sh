#!/bin/sh
# 板上验证 PIR input 驱动：sh /tmp/pir_input_test.sh [dir]
# dir 里要有 pir_input.ko，默认 /home/root/pir_input
set -u
export PATH=$PATH:/sbin:/usr/sbin

DIR=${1:-/home/root/pir_input}
KO=$DIR/pir_input.ko

[ -f "$KO" ] || { echo "找不到 $KO"; exit 1; }

echo "===== 0. 清理"
rmmod pir_input 2>/dev/null
rmmod pir_gpio 2>/dev/null
dmesg -c >/dev/null 2>&1

echo "===== 1. insmod"
insmod "$KO" || { echo "insmod 失败"; dmesg | tail -5; exit 1; }
dmesg | tail -3

echo "===== 2. 输入设备有没有注册"
grep -A4 -i 'Name="pir"' /proc/bus/input/devices
echo "-- /dev/input:"
ls /dev/input/

EVENT=$(awk -v RS='' '/Name="pir"/{for (i=1;i<=NF;i++) if ($i ~ /^event[0-9]+$/) {print $i; exit}}' /proc/bus/input/devices)
if [ -z "${EVENT:-}" ]; then
    echo "没找到 pir 的 event 节点，直接退出"
    exit 1
fi
echo "-- 用 /dev/input/$EVENT 测"

echo "===== 3. evtest 抓 60 秒（期间在 PIR 前挥手）"
timeout 60 evtest "/dev/input/$EVENT" 2>&1 | head -30

echo "===== 4. rmmod -> insmod 再试一次"
rmmod pir_input
sleep 1
insmod "$KO" && echo "二次 insmod OK" || echo "二次 insmod 失败"
dmesg | tail -3

echo "===== 5. 告警检查"
dmesg | grep -iE "warn|oops|call trace" | head -5
echo "(以上为空则无告警)"
