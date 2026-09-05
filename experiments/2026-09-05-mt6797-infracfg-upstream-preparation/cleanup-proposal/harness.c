/* SPDX-License-Identifier: MIT */
/* Stub external framework calls around the unchanged, extracted kernel bodies.
 * This exercises their C control flow, not real OF/devres concurrency or MMIO. */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define __iomem
#define IS_ERR_OR_NULL(p) (!(p))
#define IS_ERR(p) (false)
#define PTR_ERR(p) (-ENOMEM)
struct device_node { int unused; };
struct device { struct device_node *of_node; };
struct platform_device { struct device dev; void *data; };
struct platform_device_id { uintptr_t driver_data; };
struct clk { int unused; };
struct clk_hw { struct clk *clk; };
struct clk_hw_onecell_data { struct clk_hw **hws; };
struct mtk_clk_desc {
	const void *clks, *fixed_clks, *factor_clks, *mux_clks;
	const void *composite_clks, *divider_clks, *rst_desc, *clk_lock;
	int num_clks, num_fixed_clks, num_factor_clks, num_mux_clks;
	int num_composite_clks, num_divider_clks, mfg_clk_idx;
	bool shared_io, need_runtime_pm;
	int (*clk_notifier_func)(struct device *, struct clk *);
};

enum fault { NONE, ALLOC, GATE, PUBLISH, RESET };
static enum fault fault;
static struct mtk_clk_desc desc;
static struct clk_hw_onecell_data data;
static int published, deleted, reset_calls, freed, stale_at_free, invalid_delete;
static char trace[2048];
static void event(const char *name)
{
	if (strlen(trace) + strlen(name) + 2 >= sizeof(trace)) abort();
	strcat(trace, name);
	strcat(trace, " ");
}
static const void *device_get_match_data(struct device *dev) { (void)dev; return &desc; }
static const struct platform_device_id *platform_get_device_id(struct platform_device *pdev)
{ (void)pdev; return NULL; }
static void *mapping(void) { event("map"); return &data; }
#define devm_platform_ioremap_resource(...) mapping()
#define of_iomap(...) mapping()
#define devm_pm_runtime_enable(...) (event("pm_enable"), 0)
#define pm_runtime_resume_and_get(...) (event("pm_get"), 0)
#define pm_runtime_put(...) event("pm_put")
#define iounmap(...) event("unmap")
static struct clk_hw_onecell_data *mtk_alloc_clk_data(int count)
{ (void)count; event("alloc"); return fault == ALLOC ? NULL : &data; }
static void mtk_free_clk_data(struct clk_hw_onecell_data *value)
{ if (value != &data) abort(); event("free"); freed++; stale_at_free += published; }
#define mtk_clk_register_fixed_clks(...) (event("fixed+"), 0)
#define mtk_clk_register_factors(...) (event("factor+"), 0)
#define mtk_clk_register_muxes(...) (event("mux+"), 0)
#define mtk_clk_register_composites(...) (event("composite+"), 0)
#define mtk_clk_register_dividers(...) (event("divider+"), 0)
#define mtk_clk_register_gates(...) (event("gate+"), fault == GATE ? -EINVAL : 0)
#define mtk_clk_unregister_fixed_clks(...) event("fixed-")
#define mtk_clk_unregister_factors(...) event("factor-")
#define mtk_clk_unregister_muxes(...) event("mux-")
#define mtk_clk_unregister_composites(...) event("composite-")
#define mtk_clk_unregister_dividers(...) event("divider-")
#define mtk_clk_unregister_gates(...) event("gate-")
static int publish(struct clk_hw_onecell_data *value)
{
	if (value != &data) abort();
	event("provider+");
	if (fault == PUBLISH) return -EBUSY;
	published = 1;
	return 0;
}
#define of_clk_add_hw_provider(node, get, value) ((void)(node), publish(value))
static void of_clk_del_provider(struct device_node *node)
{ (void)node; event("provider-"); invalid_delete += !published; published = 0; deleted++; }
static void platform_set_drvdata(struct platform_device *pdev, void *value) { pdev->data = value; }
static void *platform_get_drvdata(struct platform_device *pdev) { return pdev->data; }
static int mtk_register_reset_controller_with_dev(struct device *dev, const void *reset)
{ (void)dev; (void)reset; event("reset"); reset_calls++; return fault == RESET ? -EIO : 0; }

/* SOURCE_FUNCTIONS: inserted from the exact hashed upstream source in memory. */

#define CHECK(condition) do { if (!(condition)) { \
	fprintf(stderr, "case=%s line=%d trace=%s\n", name, __LINE__, trace); return 1; \
} } while (0)
static int run(const char *name, enum fault selected, bool reset, bool remove)
{
	struct device_node node = {0};
	struct platform_device pdev = {.dev = {.of_node = &node}};
	fault = selected;
	published = deleted = reset_calls = freed = stale_at_free = invalid_delete = 0;
	trace[0] = '\0';
	memset(&desc, 0, sizeof(desc));
	desc.clks = desc.fixed_clks = desc.factor_clks = desc.mux_clks = &desc;
	desc.composite_clks = desc.divider_clks = &desc;
	desc.rst_desc = reset ? &desc : NULL;
	int result = __mtk_clk_simple_probe(&pdev, &node);
	if (selected == NONE) {
		CHECK(result == 0 && published == 1 && freed == 0 && deleted == 0);
		CHECK(reset_calls == (reset ? 1 : 0));
		if (remove) __mtk_clk_simple_remove(&pdev, &node);
		CHECK(published == 0 && deleted == 1 && freed == 1);
	} else if (selected == RESET) {
		CHECK(result == -EIO && reset_calls == 1 && deleted == 1 && freed == 1);
		CHECK(strstr(trace, "reset provider- gate-") != NULL);
	} else if (selected == PUBLISH) {
		CHECK(result == -EBUSY && reset_calls == 0 && deleted == 0 && freed == 1);
	} else if (selected == GATE) {
		CHECK(result == -EINVAL && reset_calls == 0 && deleted == 0 && freed == 1);
		CHECK(strstr(trace, "provider+") == NULL);
	} else {
		CHECK(result == -ENOMEM && reset_calls == 0 && deleted == 0 && freed == 0);
	}
	CHECK(published == 0 && stale_at_free == 0 && invalid_delete == 0);
	printf("PASS %s\n", name);
	return 0;
}
int main(void)
{
	int failed = 0;
	failed |= run("success-and-normal-remove", NONE, true, true);
	failed |= run("reset-failure-after-publication", RESET, true, false);
	failed |= run("clock-publication-failure", PUBLISH, true, false);
	failed |= run("gate-failure-before-publication", GATE, true, false);
	failed |= run("allocation-failure", ALLOC, true, false);
	failed |= run("no-reset-descriptor-and-remove", NONE, false, true);
	return failed;
}
