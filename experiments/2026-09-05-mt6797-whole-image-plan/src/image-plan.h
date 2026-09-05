/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_IMAGE_PLAN_H
#define MT6797_IMAGE_PLAN_H

#include "mtke.h"

#define MT6797_PLAN_EMI_OWNER_REQUIRED (-3)

/* All fields are private except the accounting summary. Caller owns immutable
 * input until every view is discarded, serializes all access, and keeps input,
 * context and output storage distinct. No ownership/transfer admission occurs.
 */
struct mt6797_image_plan {
	struct mtke_context image;
	unsigned int sections;
	unsigned int ordinary_sections;
	unsigned int emi_sections;
	size_t ordinary_bytes;
	size_t emi_bytes;
	int valid;
};

/* Descriptive metadata never includes a payload pointer or transfer handle. */
struct mt6797_plan_section {
	u32 offset;
	u32 length;
	u32 destination;
	u32 emi_offset;
	unsigned int emi;
	unsigned int raw_encrypted;
	unsigned int raw_key_index;
	unsigned int encrypted;
	unsigned int key_index;
};

/* Zero means the complete descriptive plan is valid, including EMI sections.
 * Parser errors (-1/-2) invalidate the whole plan. No execution is admitted.
 */
int mt6797_image_plan_prepare(struct mt6797_image_plan *plan,
			      const u8 *data, size_t size);
int mt6797_image_plan_describe(const struct mt6797_image_plan *plan,
			       unsigned int index,
			       struct mt6797_plan_section *section);
/* This implementation has no real EMI owner binding. Mixed images return -3;
 * there is deliberately no owner Boolean or callback that can bypass it.
 * Ordinary-only success still requires separate image and HIF admission.
 */
int mt6797_image_plan_admit(const struct mt6797_image_plan *plan);
int mt6797_image_plan_get_ordinary(const struct mt6797_image_plan *plan,
				   unsigned int index, struct mtke_view *view);
void mt6797_image_plan_invalidate(struct mt6797_image_plan *plan);

#endif
