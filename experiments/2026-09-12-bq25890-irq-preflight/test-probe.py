#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the actual BQ25890 probe and IRQ lookup with injected resource errors."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("driver", type=Path, help="prepared bq25890_charger.c")
args = parser.parse_args()
source = args.driver.read_text()


def function(signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]


prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define EPROBE_DEFER 517
#define GFP_KERNEL 0
#define GPIOD_IN 1
#define F_MAX_FIELDS 1
#define USB_PHY_TYPE_USB2 0
#define IRQF_TRIGGER_FALLING 1
#define IRQF_ONESHOT 2
#define BQ25890_IRQ_PIN "bq25890_irq"
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define dev_err(...) ((void)0)
#define dev_err_probe(dev, error, ...) (error)
#define mutex_init(p) ((void)(p))
#define INIT_DELAYED_WORK(p, f) ((void)(p))
#define INIT_WORK(p, f) ((void)(p))
#define i2c_set_clientdata(c, b) ((void)(c), (void)(b))
#define devm_regmap_init_i2c(c, cfg) ((void)(c), (void *)1)
#define devm_regmap_field_bulk_alloc(d, m, f, r, n) 0
#define devm_usb_get_phy(d, t) NULL
#define devm_add_action_or_reset(d, f, b) 0
#define bq25890_register_regulator(b) 0
#define bq25890_power_supply_init(b) 0
#define usb_register_notifier(p, n) ((void)0)
struct device { int unused; };
struct i2c_client { struct device dev; int irq; };
struct gpio_desc { int unused; };
struct bq25890_device {
    struct i2c_client *client;
    struct device *dev;
    int id, lock, pump_express_work, usb_work, rmap_fields;
    void *rmap, *usb_phy;
    struct { void *notifier_call; } usb_nb;
};
#define bq25890_usb_notifier NULL
static struct bq25890_device storage;
static struct gpio_desc gpio;
static int gpio_error, mapped_irq, init_error, chip_error, fw_error, request_error;
static int gpio_gets, maps, inits, requests, chip_reads, fw_reads;
static int resource_ready;
static void *devm_kzalloc(struct device *dev, size_t size, int flags)
{
    (void)dev; (void)flags;
    assert(size == sizeof(storage));
    memset(&storage, 0, sizeof(storage));
    return &storage;
}
static int bq25890_get_chip_version(struct bq25890_device *bq)
{
    (void)bq; chip_reads++;
    return chip_error;
}
static int bq25890_fw_probe(struct bq25890_device *bq)
{
    (void)bq; fw_reads++;
    return fw_error;
}
static struct gpio_desc *devm_gpiod_get(struct device *dev, const char *name, int flags)
{
    (void)dev;
    assert(!strcmp(name, BQ25890_IRQ_PIN) && flags == GPIOD_IN);
    gpio_gets++;
    return gpio_error ? ERR_PTR(gpio_error) : &gpio;
}
static int gpiod_to_irq(struct gpio_desc *desc)
{
    assert(desc == &gpio); maps++;
    resource_ready = mapped_irq > 0;
    return mapped_irq;
}
static int bq25890_hw_init(struct bq25890_device *bq)
{
    (void)bq; inits++;
    /* No reset/configuration entry before a usable IRQ resource is resolved. */
    if (!resource_ready) {
        fprintf(stderr, "FAIL: hardware initialization precedes IRQ resolution\n");
        return -EIO;
    }
    return init_error;
}
static int request_irq(void)
{
    assert(inits == 1 && !init_error && resource_ready);
    requests++;
    return request_error;
}
#define devm_request_threaded_irq(...) request_irq()
'''

tests = r'''
int main(void)
{
    const struct test {
        int irq, get, map, init, chip, fw, request, result;
        int expected_gets, expected_maps, expected_inits, expected_requests;
    } cases[] = {
        {19, -EPROBE_DEFER, -ENXIO, 0, 0, 0, 0, 0, 0, 0, 1, 1},
        {19, 0, 23, -EIO, 0, 0, 0, -EIO, 0, 0, 1, 0},
        {0, -ENOENT, 23, 0, 0, 0, 0, -ENOENT, 1, 0, 0, 0},
        {0, -EPROBE_DEFER, 23, 0, 0, 0, 0, -EPROBE_DEFER, 1, 0, 0, 0},
        {0, 0, -ENXIO, 0, 0, 0, 0, -ENXIO, 1, 1, 0, 0},
        {0, 0, -EPROBE_DEFER, 0, 0, 0, 0, -EPROBE_DEFER, 1, 1, 0, 0},
        {0, 0, 23, 0, 0, 0, 0, 0, 1, 1, 1, 1},
        {0, 0, 23, -EIO, 0, 0, 0, -EIO, 1, 1, 1, 0},
        {0, 0, 23, 0, -ENODEV, 0, 0, -ENODEV, 0, 0, 0, 0},
        {0, 0, 23, 0, 0, -EINVAL, 0, -EINVAL, 0, 0, 0, 0},
        {0, 0, 23, 0, 0, 0, -EBUSY, -EBUSY, 1, 1, 1, 1},
    };
    for (unsigned int i = 0; i < sizeof(cases)/sizeof(cases[0]); i++) {
        const struct test *t = &cases[i];
        struct i2c_client client = {.irq = t->irq};
        gpio_error = t->get; mapped_irq = t->map; init_error = t->init;
        chip_error = t->chip; fw_error = t->fw; request_error = t->request;
        gpio_gets = maps = inits = requests = chip_reads = fw_reads = 0;
        resource_ready = client.irq > 0;
        int ret = bq25890_probe(&client);
        if (ret != t->result || gpio_gets != t->expected_gets || maps != t->expected_maps ||
            inits != t->expected_inits || requests != t->expected_requests) {
            fprintf(stderr, "FAIL case %u: ret=%d get/map/init/request=%d/%d/%d/%d\n",
                    i, ret, gpio_gets, maps, inits, requests);
            return 1;
        }
        assert(chip_reads == 1 && fw_reads == !chip_error);
    }
    puts("PASS: 11 probe/IRQ-error cases; later IRQ-request failure remains after hardware init");
    return 0;
}
'''

with tempfile.TemporaryDirectory(prefix="bq25890-probe-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(
        prefix + function("static int bq25890_irq_probe(")
        + function("static int bq25890_probe(") + tests
    )
    subprocess.run([
        "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        str(path / "test.c"), "-o", str(path / "test"),
    ], check=True)
    subprocess.run([str(path / "test")], check=True)
