// SPDX-License-Identifier: GPL-2.0-only
#ifdef MT6797_HIF_HOST_TEST
#include "test-compat.h"
#else
#include <linux/align.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/ktime.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#endif
#include "hif.h"

#define MT6797_HIF_MAX_NS 1000000000ULL
#define MT6797_HIF_MAX_SECTION (1024U * 1024U)

struct mt6797_hif {
	void __iomem *base;
	/* Serializes this context, transaction and scratch; never external owners. */
	struct mutex mutex;
	struct mt6797_init_transaction *transaction;
	struct mt6797_hif_pio_io io;
	u64 deadline_ns;
	int first_error;
	u8 scratch[2560];
};

static int mt6797_hif_fail(struct mt6797_hif *hif, int error)
{
	if (!hif->first_error)
		hif->first_error = error;
	mt6797_init_abort(hif->transaction);
	return hif->first_error;
}

static int mt6797_hif_guard(struct mt6797_hif *hif)
{
	if (hif->first_error)
		return hif->first_error;
	if (ktime_get_ns() >= hif->deadline_ns)
		return mt6797_hif_fail(hif, -ETIMEDOUT);
	return 0;
}

/* Host faults exercise this same control flow. Ordered kernel MMIO cannot
 * report a recoverable bus exception: zero means only the accessor returned.
 */
static int mt6797_hif_write(void *context, unsigned int offset,
			    unsigned int value)
{
	struct mt6797_hif *hif = context;
	int error;

	if (offset != 0 && offset != 0x1000)
		return mt6797_hif_fail(hif, -EINVAL);
	error = mt6797_hif_guard(hif);
	if (error)
		return error;
#ifdef MT6797_HIF_HOST_TEST
	error = mt6797_test_write(value, (u8 *)hif->base + offset);
	if (error)
		return mt6797_hif_fail(hif, error);
#else
	writel(value, (u8 __iomem *)hif->base + offset);
#endif
	return mt6797_hif_guard(hif);
}

static int mt6797_hif_read(void *context, unsigned int offset,
			   unsigned int *value)
{
	struct mt6797_hif *hif = context;
	int error;
	u32 data;

	if (!value || offset != 0x1000)
		return mt6797_hif_fail(hif, -EINVAL);
	error = mt6797_hif_guard(hif);
	if (error)
		return error;
#ifdef MT6797_HIF_HOST_TEST
	error = mt6797_test_read((u8 *)hif->base + offset, &data);
	if (error)
		return mt6797_hif_fail(hif, error);
#else
	data = readl((u8 __iomem *)hif->base + offset);
#endif
	error = mt6797_hif_guard(hif);
	if (!error)
		*value = data;
	return error;
}

struct mt6797_hif *mt6797_hif_alloc(void __iomem *base, size_t span,
				    struct mt6797_init_transaction *transaction)
{
	struct mt6797_hif *hif;

	if (!base || span < 0x1004 || !IS_ALIGNED((unsigned long)base, 4) ||
	    !transaction)
		return ERR_PTR(-EINVAL);
	hif = kzalloc_obj(*hif, GFP_KERNEL);
	if (!hif)
		return ERR_PTR(-ENOMEM);
	hif->base = base;
	hif->transaction = transaction;
	hif->io = (struct mt6797_hif_pio_io){
		.context = hif,
		.write = mt6797_hif_write,
		.read = mt6797_hif_read,
	};
	mutex_init(&hif->mutex);
	return hif;
}

void mt6797_hif_free(struct mt6797_hif *hif)
{
	kfree(hif);
}

/* Called with the mutex held; busy callers refuse without waiting/retrying. */
static int mt6797_hif_enter(struct mt6797_hif *hif, u64 deadline_ns)
{
	u64 now = ktime_get_ns();

	hif->first_error = 0;
	hif->deadline_ns = deadline_ns;
	if (hif->transaction->phase != MT6797_INIT_IDLE &&
	    hif->transaction->phase != MT6797_START_READY)
		return mt6797_hif_fail(hif, -EIO);
	if (hif->transaction->free_pages > 104 ||
	    hif->transaction->start_free_pages > 104)
		return mt6797_hif_fail(hif, -EINVAL);
	if (deadline_ns <= now)
		return mt6797_hif_fail(hif, -ETIMEDOUT);
	if (deadline_ns - now > MT6797_HIF_MAX_NS)
		return mt6797_hif_fail(hif, -EINVAL);
	return 0;
}

static int mt6797_hif_read32_locked(struct mt6797_hif *hif, unsigned int reg,
				    u32 *value)
{
	int error;

	/* Function 1, READ, byte mode, fixed port, four bytes. Logical register
	 * numbers are encoded here, never added directly to the MMIO mapping.
	 */
	error = mt6797_hif_write(hif, 0, (1U << 28) | (reg << 9) | 4U);
	if (error)
		return error;
	return mt6797_hif_read(hif, 0x1000, value);
}

int mt6797_hif_read32(struct mt6797_hif *hif, unsigned int reg, u64 deadline_ns,
		      u32 *value)
{
	int error;

	if (!value)
		return -EINVAL;
	*value = 0;
	if (!hif || (reg != 0 && reg != 4 && reg != 0x90))
		return -EINVAL;
	if (!mutex_trylock(&hif->mutex))
		return -EBUSY;
	error = mt6797_hif_enter(hif, deadline_ns);
	if (!error)
		error = mt6797_hif_read32_locked(hif, reg, value);
	mutex_unlock(&hif->mutex);
	return error;
}

int
mt6797_hif_download_section(struct mt6797_hif *hif,
			    const struct mt6797_hif_section_request *request,
			    u64 deadline_ns, struct mt6797_hif_section_result *result)
{
	struct mt6797_ordinary_section section = {0};
	u32 lengths;
	int error;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_hif_section_result){0};
	if (!hif || !request || request->kind != MT6797_SECTION_ORDINARY ||
	    !request->data || !request->length ||
	    request->length > MT6797_HIF_MAX_SECTION)
		return -EINVAL;
	if (!mutex_trylock(&hif->mutex))
		return -EBUSY;
	error = mt6797_hif_enter(hif, deadline_ns);
	if (error)
		goto out;
	error = mt6797_section_begin(&section, hif->transaction, &hif->io,
				     request->kind, request->config,
				     request->config_bytes, request->sequence,
				     request->data, request->length);
	if (error)
		goto out;
	for (;;) {
		error = mt6797_hif_read32_locked(hif, 0x90, &lengths);
		if (error)
			goto out;
		if (lengths & 0xffffU)
			break;
		/* The next scalar guard rechecks the same absolute deadline.
		 * No sleep or software deadline can interrupt a stuck MMIO access.
		 */
		usleep_range(50, 100);
	}
	error = mt6797_section_ack(&section, &hif->io, lengths & 0xffffU,
				   &result->firmware_status);
	while (!error && section.phase == MT6797_SECTION_PAYLOAD) {
		error = mt6797_hif_guard(hif);
		if (!error)
			error = mt6797_section_next(&section, &hif->io,
						    hif->scratch,
						    sizeof(hif->scratch));
	}
out:
	result->submitted = section.submitted;
	if (error)
		error = mt6797_hif_fail(hif, error);
	mutex_unlock(&hif->mutex);
	return error;
}
