// SPDX-License-Identifier: GPL-2.0-only
/*
 * Host fixtures for actual extracted legacy SCPSYS registration functions.
 * Only kernel API boundaries and their minimal types are replaced here.
 * All register words, resources and domains are synthetic. No hardware,
 * kernel, filesystem or ownership behavior is emulated or established.
 */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef CONFIG_PM_GENERIC_DOMAINS
#define CONFIG_PM_GENERIC_DOMAINS 1
#endif
#define CONFIG_PM CONFIG_PM_GENERIC_DOMAINS
#define IS_ENABLED(option) (option)
#define __iomem
#define BIT(bit) (1U << (bit))
#define GFP_KERNEL 0
#define EPROBE_DEFER 517
#define ERR_PTR(error) ((void *)(intptr_t)(error))
#define PTR_ERR(pointer) ((long)(intptr_t)(pointer))
#define IS_ERR(pointer) ((uintptr_t)(pointer) >= (uintptr_t)-4095)
#define ERR_CAST(pointer) ((void *)(pointer))
#define MAX_CLKS 3
#define MTK_SCPD_ACTIVE_WAKEUP BIT(0)
#define MTK_SCPD_FWAIT_SRAM BIT(1)
#define MTK_SCPD_KEEP_DEFAULT_OFF BIT(2)
#define MTK_SCPD_CAPS(domain, cap) ((domain)->data->caps & (cap))
#define GENPD_FLAG_ACTIVE_WAKEUP BIT(0)

typedef uint32_t u32;
typedef uint8_t u8;

enum clk_id {
	CLK_NONE, CLK_MM, CLK_MFG, CLK_VENC, CLK_VENC_LT, CLK_ETHIF,
	CLK_VDEC, CLK_HIFSEL, CLK_JPGDEC, CLK_AUDIO, CLK_MAX,
};
static const char * const clk_names[] = {
	NULL, "mm", "mfg", "venc", "venc_lt", "ethif", "vdec",
	"hif_sel", "jpgdec", "audio", NULL,
};

struct device { void *of_node; };
struct platform_device { struct device dev; };
struct clk { int id; };
struct regulator { int id; };
struct regmap { int unused; };
struct generic_pm_domain {
	const char *name;
	int (*power_on)(struct generic_pm_domain *domain);
	int (*power_off)(struct generic_pm_domain *domain);
	unsigned int flags;
};
struct genpd_onecell_data {
	struct generic_pm_domain **domains;
	unsigned int num_domains;
};
struct of_phandle_args {
	int args_count;
	u32 args[2];
};
struct scp_domain_data {
	const char *name;
	u32 sta_mask;
	int ctl_offs;
	u32 sram_pdn_bits, sram_pdn_ack_bits, bus_prot_mask;
	enum clk_id clk_id[MAX_CLKS];
	u8 caps;
};
struct scp;
struct scp_domain {
	struct generic_pm_domain genpd;
	struct scp *scp;
	struct clk *clk[MAX_CLKS];
	const struct scp_domain_data *data;
	struct regulator *supply;
};
struct scp_ctrl_reg { int pwr_sta_offs, pwr_sta2nd_offs; };
struct scp {
	struct scp_domain *domains;
	struct genpd_onecell_data pd_data;
	struct device *dev;
	void *base;
	struct regmap *infracfg;
	struct scp_ctrl_reg ctrl_reg;
	bool bus_prot_reg_update;
};
struct scp_subdomain { int origin, subdomain; };
struct scp_soc_data {
	const struct scp_domain_data *domains;
	int num_domains;
	const struct scp_subdomain *subdomains;
	int num_subdomains;
	const struct scp_ctrl_reg regs;
	bool bus_prot_reg_update;
};

#define DOMAIN_COUNT 4
#define PRIMARY_WORD (0x180 / sizeof(u32))
#define SECONDARY_WORD (0x184 / sizeof(u32))
enum event_kind { READ_PRIMARY, READ_SECONDARY, SUPPLY_GET, CLOCK_GET,
	POWER_ON, POWER_OFF, GENPD_INIT, PUBLISH, SUBDOMAIN };
struct event { enum event_kind kind; int id; };
static struct event events[256];
static unsigned int event_count, checks, scenarios;
static const char *case_name;
static const char * const names[] = { "fixture0", "fixture1", "fixture2", "fixture3" };
static struct scp_domain_data domain_data[DOMAIN_COUNT];
static struct scp_subdomain links[2];
static struct scp_soc_data soc = {
	.domains = domain_data, .num_domains = DOMAIN_COUNT, .subdomains = links,
	.regs = { .pwr_sta_offs = 0x180, .pwr_sta2nd_offs = 0x184 },
	.bus_prot_reg_update = true,
};
static struct platform_device pdev;
static struct scp *current_scp;
static struct regmap fake_regmap;
static struct clk fake_clocks[CLK_MAX];
static struct regulator fake_supplies[DOMAIN_COUNT];
static u32 register_words[128];
static int supply_errors[DOMAIN_COUNT], clock_errors[CLK_MAX];
static int power_errors[DOMAIN_COUNT], init_errors[DOMAIN_COUNT];
static unsigned int supply_calls[DOMAIN_COUNT], power_calls[DOMAIN_COUNT];
static unsigned int init_calls[DOMAIN_COUNT], off_calls, provider_calls;
static unsigned int read_calls, resource_calls, subdomain_calls;
static bool initialized[DOMAIN_COUNT], initialized_off[DOMAIN_COUNT];
static void *allocations[16];
static unsigned int allocation_count;

static void check(bool condition, const char *expression, unsigned int line)
{
	checks++;
	if (!condition) {
		fprintf(stderr, "FAIL %s line %u: %s\n", case_name, line, expression);
		exit(1);
	}
}
#define CHECK(expression) check(!!(expression), #expression, __LINE__)

static void record(enum event_kind kind, int id)
{
	CHECK(event_count < sizeof(events) / sizeof(events[0]));
	events[event_count++] = (struct event) { kind, id };
}

static int name_id(const char *name)
{
	int i;

	CHECK(name != NULL);
	for (i = 0; i < DOMAIN_COUNT; i++)
		if (!strcmp(name, names[i]))
			return i;
	CHECK(false);
	return -1;
}

static void *allocate(size_t count, size_t size)
{
	void *pointer = calloc(count, size);

	CHECK(pointer != NULL);
	CHECK(allocation_count < sizeof(allocations) / sizeof(allocations[0]));
	allocations[allocation_count++] = pointer;
	return pointer;
}

static void *devm_kzalloc(struct device *dev, size_t size, int flags)
{
	(void)flags;
	CHECK(dev == &pdev.dev);
	CHECK(size == sizeof(struct scp));
	current_scp = allocate(1, size);
	return current_scp;
}

static void *devm_kcalloc(struct device *dev, size_t count, size_t size, int flags)
{
	(void)flags;
	CHECK(dev == &pdev.dev);
	return allocate(count, size);
}

static void *devm_platform_ioremap_resource(struct platform_device *device, int index)
{
	CHECK(device == &pdev && index == 0);
	resource_calls++;
	return register_words;
}

static struct regmap *syscon_regmap_lookup_by_phandle(void *node, const char *name)
{
	CHECK(node == pdev.dev.of_node && !strcmp(name, "infracfg"));
	resource_calls++;
	return &fake_regmap;
}

static struct regulator *devm_regulator_get_optional(struct device *dev, const char *name)
{
	int id = name_id(name);

	CHECK(dev == &pdev.dev);
	supply_calls[id]++;
	record(SUPPLY_GET, id);
	return supply_errors[id] ? ERR_PTR(supply_errors[id]) : &fake_supplies[id];
}

static struct clk *devm_clk_get(struct device *dev, const char *name)
{
	int id;

	CHECK(dev == &pdev.dev);
	for (id = CLK_NONE + 1; id < CLK_MAX; id++) {
		if (!strcmp(name, clk_names[id])) {
			record(CLOCK_GET, id);
			return clock_errors[id] ? ERR_PTR(clock_errors[id]) : &fake_clocks[id];
		}
	}
	CHECK(false);
	return NULL;
}

static u32 readl(const volatile void *address)
{
	read_calls++;
	if (address == &register_words[PRIMARY_WORD]) {
		record(READ_PRIMARY, 0);
		return register_words[PRIMARY_WORD];
	}
	CHECK(address == &register_words[SECONDARY_WORD]);
	record(READ_SECONDARY, 0);
	return register_words[SECONDARY_WORD];
}

static int scpsys_power_on(struct generic_pm_domain *domain)
{
	int id = name_id(domain->name);

	power_calls[id]++;
	record(POWER_ON, id);
	return power_errors[id];
}

static int scpsys_power_off(struct generic_pm_domain *domain)
{
	off_calls++;
	record(POWER_OFF, name_id(domain->name));
	return 0;
}

static int pm_genpd_init(struct generic_pm_domain *domain, void *governor, bool is_off)
{
	int id = name_id(domain->name);
	int error = CONFIG_PM_GENERIC_DOMAINS ? init_errors[id] : -ENOSYS;

	CHECK(governor == NULL);
	/* Nothing may expose the slot while initialization can still fail. */
	CHECK(current_scp->pd_data.domains[id] == NULL);
	init_calls[id]++;
	initialized_off[id] = is_off;
	initialized[id] = !error;
	record(GENPD_INIT, id);
	return error;
}

static int of_genpd_add_provider_onecell(void *node, struct genpd_onecell_data *data)
{
	unsigned int i;

	CHECK(node == pdev.dev.of_node && data->num_domains == DOMAIN_COUNT);
	provider_calls++;
	for (i = 0; i < data->num_domains; i++) {
		if (!data->domains[i])
			continue;
		CHECK(!IS_ERR(data->domains[i]));
		CHECK(data->domains[i] == &current_scp->domains[i].genpd);
		if (domain_data[i].caps & MTK_SCPD_KEEP_DEFAULT_OFF)
			CHECK(initialized[i] && initialized_off[i]);
	}
	record(PUBLISH, 0);
	return 0;
}

static void message(struct device *dev, const char *format, ...)
{
	CHECK(dev == &pdev.dev && format != NULL);
}
static void pr_err(const char *format, ...)
{
	CHECK(format != NULL);
}
#define dev_warn message
#define dev_err message
#define WARN_ON(condition) (!!(condition))

static int dev_err_probe(struct device *dev, int error, const char *format, ...)
{
	CHECK(dev == &pdev.dev && format != NULL);
	return error;
}

static const struct scp_soc_data *of_device_get_match_data(struct device *dev)
{
	CHECK(dev == &pdev.dev);
	return &soc;
}

static int pm_genpd_add_subdomain(struct generic_pm_domain *parent,
				struct generic_pm_domain *child)
{
	CHECK(parent != NULL && child != NULL && !IS_ERR(parent) && !IS_ERR(child));
	subdomain_calls++;
	record(SUBDOMAIN, name_id(child->name));
	return 0;
}

/* Nine patched provider functions plus the actual core onecell translator. */
#include "scpsys-under-test.inc"

static void setup(void)
{
	unsigned int i;

	for (i = 0; i < allocation_count; i++)
		free(allocations[i]);
	allocation_count = 0;
	current_scp = NULL;
	event_count = off_calls = provider_calls = read_calls = resource_calls = 0;
	subdomain_calls = 0;
	memset(register_words, 0, sizeof(register_words));
	memset(domain_data, 0, sizeof(domain_data));
	memset(supply_errors, 0, sizeof(supply_errors));
	memset(clock_errors, 0, sizeof(clock_errors));
	memset(power_errors, 0, sizeof(power_errors));
	memset(init_errors, 0, sizeof(init_errors));
	memset(supply_calls, 0, sizeof(supply_calls));
	memset(power_calls, 0, sizeof(power_calls));
	memset(init_calls, 0, sizeof(init_calls));
	memset(initialized, 0, sizeof(initialized));
	memset(initialized_off, 0, sizeof(initialized_off));
	soc.num_subdomains = 0;
	pdev.dev.of_node = &soc;
	for (i = 0; i < DOMAIN_COUNT; i++) {
		domain_data[i].name = names[i];
		domain_data[i].sta_mask = BIT(i + 1);
	}
	scenarios++;
}

static void status_for(int id, int primary, int secondary)
{
	u32 mask = domain_data[id].sta_mask;

	register_words[PRIMARY_WORD] = (register_words[PRIMARY_WORD] & ~mask) |
		(primary ? mask : 0);
	register_words[SECONDARY_WORD] = (register_words[SECONDARY_WORD] & ~mask) |
		(secondary ? mask : 0);
}

static struct scp *initialize(void)
{
	struct scp *scp = init_scp(&pdev, domain_data, DOMAIN_COUNT, &soc.regs, true);

	CHECK(!IS_ERR(scp));
	CHECK(scp == current_scp && scp->bus_prot_reg_update);
	CHECK(scp->pd_data.num_domains == DOMAIN_COUNT);
	return scp;
}

static void register_domains(struct scp *scp)
{
	mtk_register_power_domains(&pdev, scp, DOMAIN_COUNT);
	CHECK(provider_calls == 1 && off_calls == 0);
}

static void expect_withheld(struct scp *scp, int id)
{
	struct of_phandle_args spec = { .args_count = 1, .args = { (u32)id } };
	struct generic_pm_domain *found;
	int i;

	CHECK(scp->pd_data.domains[id] == NULL);
	CHECK(power_calls[id] == 0 && init_calls[id] == 0);
	found = genpd_xlate_onecell(&spec, &scp->pd_data);
	CHECK(IS_ERR(found) && PTR_ERR(found) == -ENOENT);
	for (i = 0; i < DOMAIN_COUNT; i++) {
		if (i == id)
			continue;
		CHECK(scp->pd_data.domains[i] == &scp->domains[i].genpd);
		CHECK(power_calls[i] == 1 && init_calls[i] == 1);
		spec.args[0] = i;
		CHECK(genpd_xlate_onecell(&spec, &scp->pd_data) == &scp->domains[i].genpd);
	}
}

static void test_state_classification(void)
{
	struct scp *scp;
	int primary, secondary, expected;

	setup();
	scp = initialize();
	register_words[PRIMARY_WORD] = register_words[SECONDARY_WORD] = BIT(31);
	for (primary = 0; primary <= 1; primary++) {
		for (secondary = 0; secondary <= 1; secondary++) {
			status_for(1, primary, secondary);
			expected = primary == secondary ? primary : -EINVAL;
			CHECK(scpsys_domain_is_on(&scp->domains[1]) == expected);
			expected = expected > 0 ? -EBUSY : expected;
			if (!CONFIG_PM_GENERIC_DOMAINS)
				expected = -EOPNOTSUPP;
			CHECK(scpsys_check_initially_off(&scp->domains[1]) == expected);
		}
	}
	domain_data[1].sta_mask = 0;
	CHECK(scpsys_check_initially_off(&scp->domains[1]) ==
		(CONFIG_PM_GENERIC_DOMAINS ? -EINVAL : -EOPNOTSUPP));
}

static void test_ordinary_behavior(void)
{
	struct scp *scp;
	unsigned int i;

	setup();
	domain_data[0].caps = MTK_SCPD_ACTIVE_WAKEUP;
	power_errors[1] = -EIO;
	init_errors[2] = -ENOMEM;
	scp = initialize();
	CHECK(scp->domains[0].genpd.flags & GENPD_FLAG_ACTIVE_WAKEUP);
	CHECK(read_calls == 0);
	event_count = 0;
	register_domains(scp);
	CHECK(event_count == 2 * DOMAIN_COUNT + 1);
	for (i = 0; i < DOMAIN_COUNT; i++) {
		CHECK(events[2 * i].kind == POWER_ON && events[2 * i].id == (int)i);
		CHECK(events[2 * i + 1].kind == GENPD_INIT && events[2 * i + 1].id == (int)i);
		CHECK(initialized_off[i] == (i == 1));
		CHECK(scp->pd_data.domains[i] != NULL);
	}
	CHECK(events[2 * DOMAIN_COUNT].kind == PUBLISH);
}

static void test_deferred_off_positions(void)
{
	struct scp *scp;
	unsigned int event, second_read, supply;
	int id, i;

	for (id = 0; id < DOMAIN_COUNT; id++) {
		setup();
		domain_data[id].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
		register_words[PRIMARY_WORD] = register_words[SECONDARY_WORD] = BIT(31);
		scp = initialize();
		CHECK(read_calls == 2 && supply_calls[id] == 1);
		second_read = supply = event_count;
		for (event = 0; event < event_count; event++) {
			if (events[event].kind == READ_SECONDARY)
				second_read = event;
			if (events[event].kind == SUPPLY_GET && events[event].id == id)
				supply = event;
		}
		CHECK(second_read < supply);
		register_domains(scp);
		CHECK(read_calls == 4 && initialized_off[id]);
		for (i = 0; i < DOMAIN_COUNT; i++) {
			CHECK(power_calls[i] == (unsigned int)(i != id));
			CHECK(init_calls[i] == 1 && scp->pd_data.domains[i] != NULL);
		}
	}
}

static void test_state_refusal_and_recheck(void)
{
	struct scp *scp;
	int id, state, late;

	for (id = 0; id < DOMAIN_COUNT; id++) {
		for (state = 1; state < 4; state++) {
			for (late = 0; late <= 1; late++) {
				setup();
				domain_data[id].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
				if (!late)
					status_for(id, state & 1, state & 2);
				scp = initialize();
				CHECK(supply_calls[id] == (unsigned int)late);
				if (late)
					status_for(id, state & 1, state & 2);
				register_domains(scp);
				expect_withheld(scp, id);
				CHECK(read_calls == (late ? 4U : 2U));
			}
		}
	}
	setup();
	domain_data[1].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
	domain_data[1].sta_mask = 0;
	scp = initialize();
	register_domains(scp);
	expect_withheld(scp, 1);
	CHECK(read_calls == 0 && supply_calls[1] == 0);
}

static void test_resource_refusals(void)
{
	const int errors[] = { -EPROBE_DEFER, -EIO, -ENOMEM };
	struct scp *scp;
	unsigned int error;
	int id, clock;

	for (id = 0; id < DOMAIN_COUNT; id++) {
		for (clock = 0; clock <= 1; clock++) {
			for (error = 0; error < sizeof(errors) / sizeof(errors[0]); error++) {
				setup();
				domain_data[id].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
				if (clock) {
					domain_data[id].clk_id[0] = CLK_MFG;
					clock_errors[CLK_MFG] = errors[error];
				} else {
					supply_errors[id] = errors[error];
				}
				scp = initialize();
				CHECK(scp->pd_data.domains[id] == NULL);
				register_domains(scp);
				expect_withheld(scp, id);
				CHECK(read_calls == 2 && supply_calls[id] == 1);
			}
		}
	}
	setup();
	domain_data[1].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
	supply_errors[1] = -ENODEV;
	scp = initialize();
	CHECK(scp->domains[1].supply == NULL);
	register_domains(scp);
	CHECK(scp->pd_data.domains[1] != NULL && power_calls[1] == 0);
	CHECK(initialized_off[1]);
}

static void test_ordinary_resource_failure_stays_global(void)
{
	struct scp *scp;
	int clock;

	for (clock = 0; clock <= 1; clock++) {
		setup();
		if (clock) {
			domain_data[1].clk_id[0] = CLK_MFG;
			clock_errors[CLK_MFG] = -EPROBE_DEFER;
		} else {
			supply_errors[1] = -EPROBE_DEFER;
		}
		scp = init_scp(&pdev, domain_data, DOMAIN_COUNT, &soc.regs, true);
		CHECK(IS_ERR(scp) && PTR_ERR(scp) == -EPROBE_DEFER);
		CHECK(provider_calls == 0 && power_calls[0] == 0);
	}
}

static void test_init_failure_and_multiple_deferred_domains(void)
{
	struct scp *scp;
	int id, i;

	for (id = 0; id < DOMAIN_COUNT; id++) {
		setup();
		domain_data[id].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
		init_errors[id] = -ENOMEM;
		scp = initialize();
		register_domains(scp);
		CHECK(scp->pd_data.domains[id] == NULL && init_calls[id] == 1);
		CHECK(power_calls[id] == 0 && !initialized[id]);
		for (i = 0; i < DOMAIN_COUNT; i++) {
			if (i != id)
				CHECK(power_calls[i] == 1 && scp->pd_data.domains[i] != NULL);
		}
	}
	setup();
	domain_data[0].caps = domain_data[1].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
	status_for(1, 1, 1);
	scp = initialize();
	register_domains(scp);
	CHECK(scp->pd_data.domains[0] != NULL && scp->pd_data.domains[1] == NULL);
	CHECK(power_calls[0] == 0 && power_calls[1] == 0);
	CHECK(init_calls[0] == 1 && init_calls[1] == 0);
	CHECK(power_calls[2] == 1 && power_calls[3] == 1);
}

static void test_pm_disabled_refuses_before_domain_resources(void)
{
	struct scp *scp;
	int id;

	for (id = 0; id < DOMAIN_COUNT; id++) {
		setup();
		domain_data[id].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
		scp = initialize();
		register_domains(scp);
		expect_withheld(scp, id);
		CHECK(read_calls == 0 && supply_calls[id] == 0);
	}
}

static void test_actual_probe_topology_gate(void)
{
	int endpoint;

	for (endpoint = 0; endpoint <= 1; endpoint++) {
		setup();
		domain_data[endpoint].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
		links[0] = (struct scp_subdomain) { 0, 1 };
		soc.num_subdomains = 1;
		CHECK(scpsys_probe(&pdev) == -EINVAL);
		CHECK(allocation_count == 0 && resource_calls == 0 && read_calls == 0);
		CHECK(event_count == 0 && provider_calls == 0 && subdomain_calls == 0);
	}
	setup();
	links[0] = (struct scp_subdomain) { 0, 1 };
	soc.num_subdomains = 1;
	domain_data[2].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
	CHECK(scpsys_probe(&pdev) == 0);
	CHECK(provider_calls == 1 && subdomain_calls == 1 && off_calls == 0);
	CHECK(power_calls[0] == 1 && power_calls[1] == 1 && power_calls[3] == 1);
	CHECK(power_calls[2] == 0);
}

static void test_actual_onecell_refusals_and_static_withholding(void)
{
	struct of_phandle_args spec = { .args_count = 1, .args = { 1 } };
	struct generic_pm_domain *found;
	struct scp *scp;
	unsigned int before, reads, acquisitions;
	int count;

	setup();
	domain_data[1].caps = MTK_SCPD_KEEP_DEFAULT_OFF;
	status_for(1, 1, 1);
	scp = initialize();
	register_domains(scp);
	expect_withheld(scp, 1);
	status_for(1, 0, 0);
	before = event_count;
	reads = read_calls;
	acquisitions = supply_calls[1];
	for (count = 0; count < 3; count++) {
		found = genpd_xlate_onecell(&spec, &scp->pd_data);
		CHECK(IS_ERR(found) && PTR_ERR(found) == -ENOENT);
	}
	CHECK(event_count == before && read_calls == reads);
	CHECK(supply_calls[1] == acquisitions && init_calls[1] == 0);
	CHECK(provider_calls == 1 && power_calls[1] == 0);
	for (count = -1; count <= 2; count++) {
		if (count == 1)
			continue;
		spec.args_count = count;
		found = genpd_xlate_onecell(&spec, &scp->pd_data);
		CHECK(IS_ERR(found) && PTR_ERR(found) == -EINVAL);
	}
	spec.args_count = 1;
	spec.args[0] = DOMAIN_COUNT;
	found = genpd_xlate_onecell(&spec, &scp->pd_data);
	CHECK(IS_ERR(found) && PTR_ERR(found) == -EINVAL);
	spec.args[0] = UINT32_MAX;
	found = genpd_xlate_onecell(&spec, &scp->pd_data);
	CHECK(IS_ERR(found) && PTR_ERR(found) == -EINVAL);
}

#define RUN(test) do { case_name = #test; test(); } while (0)
int main(void)
{
	unsigned int i;

	RUN(test_state_classification);
	RUN(test_ordinary_behavior);
	RUN(test_ordinary_resource_failure_stays_global);
	RUN(test_actual_probe_topology_gate);
	RUN(test_actual_onecell_refusals_and_static_withholding);
	if (CONFIG_PM_GENERIC_DOMAINS) {
		RUN(test_deferred_off_positions);
		RUN(test_state_refusal_and_recheck);
		RUN(test_resource_refusals);
		RUN(test_init_failure_and_multiple_deferred_domains);
	} else {
		RUN(test_pm_disabled_refuses_before_domain_resources);
	}
	for (i = 0; i < allocation_count; i++)
		free(allocations[i]);
	printf("deferred_genpd=pass pm_generic_domains=%d scenarios=%u checks=%u\n",
		CONFIG_PM_GENERIC_DOMAINS, scenarios, checks);
	return 0;
}
