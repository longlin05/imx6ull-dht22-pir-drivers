/*
 * HC-SR501 PIR -> input 子系统
 *
 * v0.2 是 misc 字符设备（/dev/pir），用户态要自己 read() 解析 "1\n"。
 * 这次改成标准输入设备：EV_KEY，事件从 /dev/input/eventX 出来，
 * evtest / udev / 上层输入栈都能直接用。
 *
 * 两种绑定方式：
 *   1) 设备树：compatible = "zulong,pir-input"，irq-gpios 指定 OUT 脚
 *   2) 回退：没有设备树节点时用模块参数 gpio_num
 *
 * 中断：threaded IRQ，双沿
 *   顶半部只唤醒线程
 *   线程半部等消抖时间再读电平，上升沿报按下，下降沿报抬起
 *   holdoff 用来压住一次动作里的重复触发
 */
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/gpio.h>
#include <linux/gpio/consumer.h>
#include <linux/input.h>
#include <linux/interrupt.h>
#include <linux/jiffies.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/slab.h>

/* 没有设备树节点时的回退参数 */
static int gpio_num = 9;
static int debounce_ms = 200;
static int holdoff_ms = 3000;
static int key_code = KEY_PROG1;

module_param(gpio_num, int, 0444);
module_param(debounce_ms, int, 0644);
module_param(holdoff_ms, int, 0644);
module_param(key_code, int, 0444);
MODULE_PARM_DESC(gpio_num, "global GPIO number for PIR OUT (used only without DT node)");
MODULE_PARM_DESC(debounce_ms, "stable time before reporting an edge (ms)");
MODULE_PARM_DESC(holdoff_ms, "minimum interval between two detections (ms)");
MODULE_PARM_DESC(key_code, "input key code reported on detection (default KEY_PROG1)");

struct pir_state {
    struct device *dev;
    struct gpio_desc *out;
    struct input_dev *input;
    int irq;
    bool pressed;
    unsigned long last_event;
};

static bool pir_probed;

static irqreturn_t pir_hardirq(int irq, void *data)
{
    (void)irq;
    (void)data;

    return IRQ_WAKE_THREAD;
}

static irqreturn_t pir_thread(int irq, void *data)
{
    struct pir_state *st = data;
    int value;

    (void)irq;

    /* 边沿来了，等电平稳定再采样 */
    msleep(debounce_ms > 0 ? debounce_ms : 1);
    value = gpiod_get_value(st->out);

    if (value && !st->pressed) {
        /* 上升沿：holdoff 压住同一次动作里的重复触发 */
        if (!holdoff_ms ||
            time_after(jiffies,
                       st->last_event + msecs_to_jiffies(holdoff_ms))) {
            st->last_event = jiffies;
            st->pressed = true;
            input_report_key(st->input, key_code, 1);
            input_sync(st->input);
        }
    } else if (!value && st->pressed) {
        /* 下降沿：抬起。被 holdoff 压掉的上升沿不会走到这里，
         * 因为 pressed 还是 false */
        st->pressed = false;
        input_report_key(st->input, key_code, 0);
        input_sync(st->input);
    }

    return IRQ_HANDLED;
}

static int pir_probe(struct platform_device *pdev)
{
    struct pir_state *st;
    int *pdata = dev_get_platdata(&pdev->dev);
    int legacy_gpio = pdata ? *pdata : -1;
    int ret;

    pir_probed = true;

    if (!key_code) {
        dev_err(&pdev->dev, "invalid key_code\n");
        return -EINVAL;
    }

    st = devm_kzalloc(&pdev->dev, sizeof(*st), GFP_KERNEL);
    if (!st) {
        return -ENOMEM;
    }
    st->dev = &pdev->dev;

    if (pdev->dev.of_node) {
        /* irq-gpios = <&gpio1 9 GPIO_ACTIVE_HIGH> */
        st->out = devm_gpiod_get(&pdev->dev, "irq", GPIOD_IN);
        if (IS_ERR(st->out)) {
            ret = PTR_ERR(st->out);
            dev_err(&pdev->dev, "failed to get irq-gpios: %d\n", ret);
            return ret;
        }
    } else if (legacy_gpio >= 0) {
        ret = devm_gpio_request_one(&pdev->dev, legacy_gpio, GPIOF_IN, "pir-out");
        if (ret != 0) {
            dev_err(&pdev->dev, "gpio_request(%d) failed: %d\n", legacy_gpio, ret);
            return ret;
        }
        st->out = gpio_to_desc(legacy_gpio);
    } else {
        dev_err(&pdev->dev, "no DT node and no gpio_num\n");
        return -EINVAL;
    }

    st->irq = gpiod_to_irq(st->out);
    if (st->irq < 0) {
        dev_err(&pdev->dev, "gpiod_to_irq failed: %d\n", st->irq);
        return st->irq;
    }

    /* 输入设备：只上报一个按键 */
    st->input = devm_input_allocate_device(&pdev->dev);
    if (!st->input) {
        dev_err(&pdev->dev, "failed to allocate input device\n");
        return -ENOMEM;
    }
    st->input->name = "pir";
    st->input->phys = "pir/input0";
    st->input->id.bustype = BUS_HOST;
    st->input->dev.parent = &pdev->dev;

    input_set_capability(st->input, EV_KEY, key_code);

    ret = input_register_device(st->input);
    if (ret != 0) {
        dev_err(&pdev->dev, "input_register_device failed: %d\n", ret);
        return ret;
    }

    ret = devm_request_threaded_irq(&pdev->dev, st->irq,
                                    pir_hardirq, pir_thread,
                                    IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING |
                                    IRQF_ONESHOT,
                                    "pir", st);
    if (ret != 0) {
        dev_err(&pdev->dev, "request_threaded_irq %d failed: %d\n", st->irq, ret);
        return ret;
    }

    platform_set_drvdata(pdev, st);
    input_set_drvdata(st->input, st);

    dev_info(&pdev->dev, "probed, irq=%d, key=%d, %s\n",
             st->irq, key_code,
             pdev->dev.of_node ? "from device tree" : "from module parameter");
    return 0;
}

static int pir_remove(struct platform_device *pdev)
{
    struct pir_state *st = platform_get_drvdata(pdev);

    dev_info(&pdev->dev, "removed (input device unregistered by devm)\n");
    /* input 和 irq 都由 devm 释放 */
    (void)st;
    return 0;
}

static const struct of_device_id pir_of_match[] = {
    /* 沿用 v0.2 设备树里的 compatible：硬件描述没变，只换驱动实现，
     * 所以不用重新刷 DTB */
    { .compatible = "zulong,pir" },
    { .compatible = "zulong,pir-input" },
    { }
};
MODULE_DEVICE_TABLE(of, pir_of_match);

static struct platform_driver pir_driver = {
    .probe = pir_probe,
    .remove = pir_remove,
    .driver = {
        .name = "pir-input",
        .of_match_table = pir_of_match,
    },
};

static struct platform_device *pir_legacy_pdev;

static int __init pir_init(void)
{
    int ret;

    ret = platform_driver_register(&pir_driver);
    if (ret != 0) {
        pr_err("pir: platform_driver_register failed: %d\n", ret);
        return ret;
    }

    if (!pir_probed) {
        pir_legacy_pdev = platform_device_alloc("pir-input", -1);
        if (!pir_legacy_pdev) {
            platform_driver_unregister(&pir_driver);
            return -ENOMEM;
        }
        ret = platform_device_add_data(pir_legacy_pdev,
                                       &gpio_num, sizeof(gpio_num));
        if (ret == 0) {
            ret = platform_device_add(pir_legacy_pdev);
        }
        if (ret != 0) {
            platform_device_put(pir_legacy_pdev);
            pir_legacy_pdev = NULL;
            platform_driver_unregister(&pir_driver);
            return ret;
        }
        pr_info("pir: no DT node, using gpio_num=%d\n", gpio_num);
    }

    return 0;
}

static void __exit pir_exit(void)
{
    if (pir_legacy_pdev) {
        platform_device_unregister(pir_legacy_pdev);
        pir_legacy_pdev = NULL;
    }
    platform_driver_unregister(&pir_driver);
    pr_info("pir: unloaded\n");
}

module_init(pir_init);
module_exit(pir_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("project B");
MODULE_DESCRIPTION("HC-SR501 PIR as an input device (EV_KEY)");
