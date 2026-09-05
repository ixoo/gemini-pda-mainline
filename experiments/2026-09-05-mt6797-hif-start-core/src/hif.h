/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_PRIVATE_HIF_H
#define MT6797_PRIVATE_HIF_H

#ifdef MT6797_HIF_HOST_TEST
#include "test-compat.h"
#else
#include <linux/io.h>
#include <linux/types.h>
#endif
#include "hif_ordinary_section.h"

struct mt6797_hif;

struct mt6797_hif_section_request {
	enum mt6797_section_kind kind;
	const u8 *config;
	size_t config_bytes;
	unsigned int sequence;
	const u8 *data;
	size_t length;
};

struct mt6797_hif_section_result {
	size_t submitted;
	unsigned int firmware_status;
};

/* Allocation owns memory only. Caller retains the real powered mapping,
 * transaction, exclusive driver ownership, IRQ quiescence and reset exclusion
 * through all calls. No ownership acquisition, INIT seeding or reset occurs.
 * The mutex serializes this context only, not another driver or firmware.
 */
struct mt6797_hif *
mt6797_hif_alloc(void __iomem *base, size_t span,
		 struct mt6797_init_transaction *transaction);
/* Caller has stopped/joined every user; this frees no provider resources. */
void mt6797_hif_free(struct mt6797_hif *hif);

/* Absolute monotonic nanoseconds; positive remaining budget <= one second.
 * WCIR (0), WHLPCR (4), WRPLR (0x90) only. No register writes are exposed.
 */
int mt6797_hif_read32(struct mt6797_hif *hif, unsigned int reg, u64 deadline_ns,
		      u32 *value);
/* One ordinary section only, <=1 MiB. Caller supplies immutable, validated,
 * distinct metadata/data and retains them until return. Successful submission
 * is neither whole-image completion nor permission to issue START.
 */
int
mt6797_hif_download_section(struct mt6797_hif *hif,
			    const struct mt6797_hif_section_request *request,
			    u64 deadline_ns, struct mt6797_hif_section_result *result);

/* Caller proves complete image/EMI sealing and retains all owner resources
 * before calling: an uncertain write can already have started firmware.
 * Same mapping, IRQ/reset exclusion and immutable storage contract as download.
 * One attempt per context. Zero means START TX submitted, never readiness.
 * No ACK read, image completeness check, ownership acquisition or retry occurs.
 */
int mt6797_hif_start_submit(struct mt6797_hif *hif, const u8 *command,
			    size_t bytes, unsigned int sequence, u64 deadline_ns);
/* One actual WCIR read under the unchanged START absolute deadline. Zero means
 * the ready level was observed, -EAGAIN means pending; neither proves causality.
 * Pending observations may repeat only before that deadline. Other failures
 * poison the retained transaction. No internal polling or renewed budget.
 */
int mt6797_hif_start_observe_ready(struct mt6797_hif *hif, u32 *wcir);

#endif
