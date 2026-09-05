// SPDX-License-Identifier: GPL-2.0-only
#include "image-plan.h"

void mt6797_image_plan_invalidate(struct mt6797_image_plan *plan)
{
	if (plan)
		*plan = (struct mt6797_image_plan){0};
}

int mt6797_image_plan_prepare(struct mt6797_image_plan *plan,
			      const u8 *data, size_t size)
{
	struct mtke_context image = {0};
	struct mt6797_image_plan pending = {0};
	struct mtke_view view;
	unsigned int i;
	int error;

	if (!plan)
		return -1;
	mt6797_image_plan_invalidate(plan);
	error = mtke_parse(&image, data, size);
	if (error)
		return error;
	/* No partial view is published while later entries remain unchecked. */
	for (i = 0; i < image.count; i++) {
		error = mtke_get(&image, i, &view);
		if (error)
			return error;
		if (view.emi) {
			pending.emi_sections++;
			pending.emi_bytes += view.length;
		} else {
			pending.ordinary_sections++;
			pending.ordinary_bytes += view.length;
		}
		pending.sections++;
	}
	/* The parser proves disjoint payloads within the 1 MiB input cap.
	 * Consequently neither byte total nor their sum can overflow size_t.
	 */
	if (pending.sections != image.count ||
	    pending.ordinary_sections + pending.emi_sections != image.count)
		return -1;
	*plan = pending;
	plan->image = image;
	plan->valid = 1;
	return 0;
}

int mt6797_image_plan_describe(const struct mt6797_image_plan *plan,
			       unsigned int index,
			       struct mt6797_plan_section *section)
{
	struct mtke_view view;
	int error;

	if (!section)
		return -1;
	*section = (struct mt6797_plan_section){0};
	if (!plan || !plan->valid)
		return -1;
	error = mtke_get(&plan->image, index, &view);
	if (error)
		return error;
	*section = (struct mt6797_plan_section){
		.offset = view.offset,
		.length = view.length,
		.destination = view.destination,
		.emi_offset = view.emi_offset,
		.emi = view.emi,
		.raw_encrypted = view.raw_encrypted,
		.raw_key_index = view.raw_key_index,
		.encrypted = view.encrypted,
		.key_index = view.key_index,
	};
	return 0;
}

int mt6797_image_plan_admit(const struct mt6797_image_plan *plan)
{
	if (!plan || !plan->valid)
		return -1;
	if (plan->emi_sections)
		return MT6797_PLAN_EMI_OWNER_REQUIRED;
	return 0;
}

int mt6797_image_plan_get_ordinary(const struct mt6797_image_plan *plan,
				   unsigned int index, struct mtke_view *view)
{
	int error;

	if (!view)
		return -1;
	*view = (struct mtke_view){0};
	error = mt6797_image_plan_admit(plan);
	if (error)
		return error;
	return mtke_get(&plan->image, index, view);
}
