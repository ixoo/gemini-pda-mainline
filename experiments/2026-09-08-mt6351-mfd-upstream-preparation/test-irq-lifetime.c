// SPDX-License-Identifier: MIT
/* Userspace control-flow model; no physical addresses or hardware access. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define IRQF_ONESHOT 1
#define GFP_KERNEL 0
#define dev_err(...) ((void)0)
#define dev_err_probe(dev, error, ...) (error)
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
struct notifier_block { void (*notifier_call)(void); };
struct irq_domain { unsigned int revmap_size; void (*exit)(struct irq_domain *); };
struct irq_domain_info {
    void *fwnode, *ops, *host_data;
    unsigned int size, hwirq_max;
    void (*exit)(struct irq_domain *);
};
struct irq_top { int num_int_regs, en_reg, en_reg_shift; };
struct pmic_irq_data {
    unsigned int num_pmic_irqs;
    int num_top;
    struct irq_top pmic_ints[1];
    int *enable_hwirq, *cache_hwirq;
};
static struct pmic_irq_data mt6357_irqd = { .num_pmic_irqs = 145, .num_top = 1,
                                         .pmic_ints = {{2, 0x100, 2}} };
static struct pmic_irq_data mt6358_irqd = { .num_pmic_irqs = 145, .num_top = 1,
                                         .pmic_ints = {{2, 0x100, 2}} };
static struct pmic_irq_data mt6359_irqd = { .num_pmic_irqs = 145, .num_top = 1,
                                         .pmic_ints = {{2, 0x100, 2}} };
struct mt6397_chip {
    void *dev, *regmap, *irq_data;
    struct irq_domain *irq_domain;
    unsigned int chip_id, num_irq_regs, int_con[4], int_status[4];
    int irqlock, irq;
    struct notifier_block pm_nb;
};
static struct { const char *name; } mt6358_irq_chip = { "fake-pmic" };
static int mt6397_irq_domain_ops, mt6358_irq_domain_ops, allocation;
static void mt6397_irq_thread(void) {}
static void mt6397_irq_pm_notifier(void) {}
static void mt6358_irq_handler(void) {}
static void mutex_init(int *lock) { *lock = 0; }
static void *dev_fwnode(void *dev) { return dev; }
static void *devm_kcalloc(void *dev, unsigned int n, unsigned int size, int flags)
{ return &allocation; }

enum failure { NONE, DOMAIN, REQUEST, NOTIFIER, ACTION, WAKE, CHILD };
static enum failure fail;
static unsigned int writes, mask_fail, maps[160], disposed, removals;
static int irq_live, notifier_live, children_live, domain_live, wake_live;
static struct irq_domain domain;
static struct { void (*release)(void *); void *data; } resources[4];
static unsigned int resource_count;
static int enable_irq_wake(int irq)
{
    assert(irq_live && domain_live && !wake_live);
    if (fail == WAKE)
        return -EINVAL;
    wake_live = 1;
    return 0;
}
static void disable_irq_wake(int irq)
{
    assert(wake_live && irq_live && domain_live && !children_live);
    wake_live = 0;
}
static void add_resource(void (*release)(void *), void *data)
{
    assert(resource_count < 4);
    resources[resource_count].release = release;
    resources[resource_count++].data = data;
}
static void unwind(void)
{
    while (resource_count) {
        resource_count--;
        resources[resource_count].release(resources[resource_count].data);
    }
}
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{ return ++writes == mask_fail ? -121 : 0; }
static unsigned int irq_find_mapping(struct irq_domain *d, unsigned int hwirq)
{ assert(d == &domain && domain_live); return maps[hwirq]; }
static void irq_dispose_mapping(unsigned int virq)
{
    assert(domain_live && !children_live && !irq_live && !notifier_live && !wake_live);
    assert(virq > 0 && maps[virq - 1] == virq);
    maps[virq - 1] = 0;
    disposed++;
}
static void release_domain(void *data)
{
    assert(domain_live && !children_live && !irq_live && !notifier_live && !wake_live);
    domain.exit(&domain);
    for (unsigned int i = 0; i < domain.revmap_size; i++)
        assert(!maps[i]);
    domain_live = 0;
    removals++;
}
static struct irq_domain *devm_irq_domain_instantiate(void *dev,
                                                    struct irq_domain_info *info)
{
    if (fail == DOMAIN)
        return ERR_PTR(-ENOMEM);
    assert(info->size == info->hwirq_max && info->size <= 160 && info->exit);
    domain = (struct irq_domain){ info->size, info->exit };
    domain_live = 1;
    add_resource(release_domain, &domain);
    return &domain;
}
static void release_irq(void *data)
{
    assert(irq_live && domain_live && !notifier_live && !children_live && !wake_live);
    irq_live = 0; /* Models free_irq() completing before the next release. */
}
static int devm_request_threaded_irq(void *dev, int irq, void *top,
        void (*thread)(void), int flags, const char *name, void *chip)
{
    assert(domain_live);
    if (fail == REQUEST)
        return -EBUSY;
    irq_live = 1;
    add_resource(release_irq, chip);
    return 0;
}
static int register_pm_notifier(struct notifier_block *nb)
{
    assert(irq_live && domain_live && !notifier_live);
    if (fail == NOTIFIER)
        return -EIO;
    notifier_live = 1;
    return 0;
}
static void unregister_pm_notifier(void *nb)
{
    assert(notifier_live && irq_live && domain_live && !children_live);
    notifier_live = 0;
}
static int devm_add_action_or_reset(void *dev, void (*action)(void *), void *data)
{
    if (fail == ACTION) {
        action(data);
        return -ENOMEM;
    }
    add_resource(action, data);
    return 0;
}
static void release_children(void *data)
{ assert(children_live && irq_live && domain_live); children_live = 0; }
/* ACTUAL SOURCE FUNCTIONS */
int main(void)
{
    const unsigned int ids[] = { MT6323_CHIP_ID, MT6328_CHIP_ID, MT6331_CHIP_ID,
        MT6351_CHIP_ID, MT6391_CHIP_ID, MT6397_CHIP_ID,
        MT6357_CHIP_ID, MT6358_CHIP_ID, MT6366_CHIP_ID, MT6359_CHIP_ID };
    unsigned int cases = 0;
    for (unsigned int i = 0; i < sizeof(ids) / sizeof(ids[0]); i++) {
        for (fail = NONE; fail <= CHILD; fail++) {
            if ((i >= 6 && fail == NOTIFIER) || (i < 6 && fail == WAKE))
                continue;
            struct mt6397_chip chip = { .chip_id = ids[i] };
            writes = disposed = removals = 0;
            assert(!resource_count && !domain_live && !irq_live && !notifier_live);
            int ret = i < 6 ? mt6397_irq_init(&chip) : mt6358_irq_init(&chip);
            int expected = fail == DOMAIN || fail == ACTION ? -ENOMEM :
                           fail == REQUEST ? -EBUSY : fail == NOTIFIER ? -EIO : 0;
            assert(ret == expected);
            if (!ret) {
                assert(notifier_live == (i < 6));
                assert(wake_live == (i >= 6 && fail != WAKE));
                const unsigned int positions[] = { 0, domain.revmap_size / 2,
                                                   domain.revmap_size - 1 };
                for (unsigned int j = 0; j < 3; j++)
                    maps[positions[j]] = positions[j] + 1;
                /* mfd_add_devices removes partial children on failure. */
                if (fail != CHILD) {
                    children_live = 1;
                    add_resource(release_children, &chip);
                }
            }
            unwind();
            assert(!irq_live && !notifier_live && !domain_live && !children_live && !wake_live);
            assert(disposed == (ret ? 0u : 3u));
            assert(removals == (fail == DOMAIN ? 0u : 1u));
            cases++;
        }
    }
    fail = NONE;
    for (mask_fail = 1; mask_fail <= 4; mask_fail++) {
        struct mt6397_chip chip = { .chip_id = MT6351_CHIP_ID };
        writes = 0;
        assert(mt6397_irq_init(&chip) == -121);
        assert(writes == mask_fail && !resource_count && !domain_live);
        cases++;
    }
    printf("PASS: %u initializer/failure/teardown cases; mappings released after users\n", cases);
    return 0;
}
