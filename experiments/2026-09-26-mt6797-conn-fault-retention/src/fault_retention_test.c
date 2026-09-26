// SPDX-License-Identifier: GPL-2.0-only
/* Host-only fault injection around actual patched SCPSYS callbacks. */
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define __iomem
#define BIT(bit) (1U << (bit))
#define MAX_CLKS 3
#define MTK_SCPD_KEEP_DEFAULT_OFF BIT(2)
#define MTK_SCPD_CLK_OFF_BEFORE_RESET BIT(3)
#define MTK_SCPD_RETAIN_FAILED_STATE BIT(4)
#define MTK_SCPD_CAPS(domain, cap) ((domain)->data->caps & (cap))
#define PWR_ON_BIT BIT(0)
#define PWR_ON_2ND_BIT BIT(1)
#define PWR_CLK_DIS_BIT BIT(4)
#define PWR_ISO_BIT BIT(1)
#define PWR_RST_B_BIT BIT(0)
#define MTK_POLL_DELAY_US 1
#define MTK_POLL_TIMEOUT 10
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define dev_err(...) ((void)0)

typedef uint32_t u32;
struct device { int unused; };
struct regulator { int vote; };
struct clk { int vote; int index; };
struct generic_pm_domain { const char *name; };
struct scp_domain_data { unsigned int caps; int ctl_offs; };
struct scp { struct device *dev; void *base; };
struct scp_domain {
	struct generic_pm_domain genpd;
	struct scp *scp;
	struct clk *clk[MAX_CLKS];
	const struct scp_domain_data *data;
	struct regulator *supply;
	int fault_error;
};

static u32 ctl_word;
static struct device device;
static struct scp scp = { .dev = &device, .base = &ctl_word };
static struct scp_domain_data data;
static struct scp_domain domain;
static struct regulator supply;
static struct clk clocks[2];
static int ack_state, clock_error_at;
static unsigned int supply_enables, supply_disables, clock_enables;
static unsigned int clock_disables, writes, protection_calls, sram_calls;
static unsigned int checks, cases;
static const char *case_name;

static void check(int condition, const char *expression, int line)
{
	checks++;
	if (!condition) {
		fprintf(stderr, "FAIL %s:%d: %s\n", case_name, line, expression);
		exit(1);
	}
}
#define CHECK(expr) check(!!(expr), #expr, __LINE__)

static u32 readl(void *address)
{
	CHECK(address == &ctl_word);
	return ctl_word;
}

static void writel(u32 value, void *address)
{
	CHECK(address == &ctl_word);
	writes++;
	ctl_word = value;
}

static int regulator_enable(struct regulator *regulator)
{
	CHECK(regulator == &supply);
	supply_enables++;
	regulator->vote++;
	return 0;
}

static int regulator_disable(struct regulator *regulator)
{
	CHECK(regulator == &supply && regulator->vote == 1);
	supply_disables++;
	regulator->vote--;
	return 0;
}

static int clk_prepare_enable(struct clk *clock)
{
	CHECK(clock && clock->index < 2);
	clock_enables++;
	if (clock_error_at == clock->index + 1)
		return -EIO;
	clock->vote++;
	return 0;
}

static void clk_disable_unprepare(struct clk *clock)
{
	if (!clock)
		return;
	CHECK(clock->vote == 1);
	clock_disables++;
	clock->vote--;
}

static int scpsys_domain_is_on(struct scp_domain *scpd)
{
	CHECK(scpd == &domain);
	return ack_state;
}

#define readx_poll_timeout(fn, arg, value, condition, delay, timeout) \
	({ (value) = fn(arg); (condition) ? 0 : -ETIMEDOUT; })

static int scpsys_sram_enable(struct scp_domain *scpd, void *ctl_addr)
{
	CHECK(scpd == &domain && ctl_addr == &ctl_word);
	sram_calls++;
	return 0;
}

static int scpsys_sram_disable(struct scp_domain *scpd, void *ctl_addr)
{
	CHECK(scpd == &domain && ctl_addr == &ctl_word);
	sram_calls++;
	return 0;
}

static int scpsys_bus_protect_enable(struct scp_domain *scpd)
{
	CHECK(scpd == &domain);
	protection_calls++;
	return 0;
}

static int scpsys_bus_protect_disable(struct scp_domain *scpd)
{
	CHECK(scpd == &domain);
	protection_calls++;
	return 0;
}

#include "scpsys-under-test.inc"

static void reset(const char *name, unsigned int caps)
{
	case_name = name;
	cases++;
	ctl_word = 0;
	data = (struct scp_domain_data) { .caps = caps };
	domain = (struct scp_domain) {
		.genpd = { .name = "test" }, .scp = &scp, .data = &data,
		.supply = &supply, .clk = { &clocks[0], &clocks[1], NULL },
	};
	supply = (struct regulator) { 0 };
	clocks[0] = (struct clk) { .index = 0 };
	clocks[1] = (struct clk) { .index = 1 };
	ack_state = 0;
	clock_error_at = 0;
	supply_enables = supply_disables = clock_enables = clock_disables = 0;
	writes = protection_calls = sram_calls = 0;
}

static void test_on_ack_fault(void)
{
	unsigned int old_writes;

	reset("retained ON ACK", MTK_SCPD_KEEP_DEFAULT_OFF |
		MTK_SCPD_RETAIN_FAILED_STATE);
	CHECK(scpsys_power_on(&domain.genpd) == -ETIMEDOUT);
	CHECK(domain.fault_error == -ETIMEDOUT);
	CHECK(supply.vote == 1 && clocks[0].vote == 1 && clocks[1].vote == 1);
	CHECK(supply_disables == 0 && clock_disables == 0);
	CHECK(writes == 2 && protection_calls == 0 && sram_calls == 0);
	old_writes = writes;
	CHECK(scpsys_power_on(&domain.genpd) == -ETIMEDOUT);
	CHECK(scpsys_power_off(&domain.genpd) == -ETIMEDOUT);
	CHECK(writes == old_writes && supply_enables == 1 && clock_enables == 2);
}

static void test_legacy_on_ack_cleanup(void)
{
	reset("legacy ON ACK", 0);
	CHECK(scpsys_power_on(&domain.genpd) == -ETIMEDOUT);
	CHECK(domain.fault_error == 0);
	CHECK(supply.vote == 0 && clocks[0].vote == 0 && clocks[1].vote == 0);
	CHECK(supply_disables == 1 && clock_disables == 2);
	CHECK(scpsys_power_on(&domain.genpd) == -ETIMEDOUT);
	CHECK(supply_enables == 2);
}

static void test_clock_failure(void)
{
	reset("clock failure", MTK_SCPD_KEEP_DEFAULT_OFF |
		MTK_SCPD_RETAIN_FAILED_STATE);
	clock_error_at = 2;
	CHECK(scpsys_power_on(&domain.genpd) == -EIO);
	CHECK(domain.fault_error == -EIO);
	CHECK(supply.vote == 1 && supply_disables == 0);
	CHECK(clocks[0].vote == 0 && clocks[1].vote == 0);
	CHECK(clock_enables == 2 && clock_disables == 1 && writes == 0);
	CHECK(scpsys_power_on(&domain.genpd) == -EIO && supply_enables == 1);
}

static void test_off_ack_fault(void)
{
	unsigned int old_writes;

	reset("retained OFF ACK", MTK_SCPD_KEEP_DEFAULT_OFF |
		MTK_SCPD_RETAIN_FAILED_STATE | MTK_SCPD_CLK_OFF_BEFORE_RESET);
	ack_state = 1;
	CHECK(scpsys_power_on(&domain.genpd) == 0);
	CHECK(supply.vote == 1 && clocks[0].vote == 1 && clocks[1].vote == 1);
	CHECK(sram_calls == 1 && protection_calls == 1);
	CHECK(scpsys_power_off(&domain.genpd) == -ETIMEDOUT);
	CHECK(domain.fault_error == -ETIMEDOUT);
	CHECK(supply.vote == 1 && clocks[0].vote == 1 && clocks[1].vote == 1);
	CHECK(supply_disables == 0 && clock_disables == 0);
	old_writes = writes;
	CHECK(scpsys_power_on(&domain.genpd) == -ETIMEDOUT);
	CHECK(scpsys_power_off(&domain.genpd) == -ETIMEDOUT);
	CHECK(writes == old_writes && protection_calls == 2 && sram_calls == 2);
}

int main(void)
{
	test_on_ack_fault();
	test_legacy_on_ack_cleanup();
	test_clock_failure();
	test_off_ack_fault();
	printf("fault_retention_cases=%u checks=%u pass\n", cases, checks);
	return 0;
}
