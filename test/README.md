# 测试脚本

```text
pir-input-test.sh     v0.3 起的 PIR input 设备测试（insmod / 事件节点 / evtest / rmmod 循环）
records/              板上跑出来的原始日志
legacy/               v0.2 的 misc 字符设备时代脚本，只作对照
                      （里面的 /dev/pir 在当前版本已经不存在）
```

## pir-input-test.sh

拷到板上执行，第二个参数是 `.ko` 所在目录：

```bash
insmod 前先确认旧的 pir_gpio / pir_input 都已 rmmod
sh /tmp/pir-input-test.sh /home/root/pir_input
```

脚本会打印：

```text
/proc/bus/input/devices 里 Name="pir" 那一段
/dev/input 下对应的 eventX
evtest 60 秒的原始事件
rmmod -> insmod 二次加载结果
dmesg 里的 warn/oops
```

`evtest` 那一步会等真实事件，没人经过时它只会打印 `Testing ... (interrupt to exit)` 然后超时。
