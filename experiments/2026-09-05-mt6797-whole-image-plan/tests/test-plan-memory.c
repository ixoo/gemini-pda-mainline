// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include "image-plan.h"

u32 mtke_crc32(const u8 *data, size_t size)
{
	return (u32)crc32(0, data, (uInt)size);
}

static void put32(u8 *p, u32 value)
{
	for (unsigned int i = 0; i < 4; i++)
		p[i] = (u8)(value >> (i * 8));
}

static void update_crc(u8 *data, size_t size)
{
	put32(data + 4, mtke_crc32(data + 8, size - 8));
}

static u8 *make(unsigned int count, size_t *size)
{
	u8 *data;

	*size = 24 + 20 * (size_t)count;
	data = calloc(*size, 1);
	assert(data);
	memcpy(data, "MTKE", 4);
	put32(data + 8, count);
	for (unsigned int i = 0; i < count; i++) {
		put32(data + 24 + 16 * i, 24 + 16 * count + 4 * i);
		put32(data + 24 + 16 * i + 8, 4);
		put32(data + 24 + 16 * i + 12, i < 2 ? 0x1000 + i * 4 : 0xf0000000 + i * 4);
	}
	update_crc(data, *size);
	return data;
}

int main(void)
{
	struct mt6797_image_plan plan = {0};
	struct mt6797_plan_section description;
	struct mtke_view view;
	size_t size;
	u8 *data;
	unsigned int cases = 0;

	assert(mt6797_image_plan_prepare(NULL, NULL, 0) == -1);
	assert(mt6797_image_plan_describe(NULL, 0, NULL) == -1);
	assert(mt6797_image_plan_get_ordinary(NULL, 0, NULL) == -1);
	mt6797_image_plan_invalidate(NULL);
	for (unsigned int count = 1; count <= 256; count++) {
		data = make(count, &size);
		assert(!mt6797_image_plan_prepare(&plan, data, size));
		assert(plan.sections == count);
		assert(plan.ordinary_sections + plan.emi_sections == count);
		assert(plan.ordinary_bytes + plan.emi_bytes == count * 4);
		assert(mt6797_image_plan_admit(&plan) == (count > 2 ? -3 : 0));
		for (unsigned int i = 0; i < count; i++) {
			assert(!mt6797_image_plan_describe(&plan, i, &description));
			assert(description.length == 4 && description.emi == (i >= 2));
			memset(&view, 0xff, sizeof(view));
			assert(mt6797_image_plan_get_ordinary(&plan, i, &view) == (count > 2 ? -3 : 0));
			if (count > 2)
				assert(!view.data && !view.length);
			else
				assert(view.data[0] == 0 && view.data[3] == 0);
		}
		/* Defect in the final entry must revoke even the first ordinary view. */
		put32(data + 24 + 16 * (count - 1) + 8, 0xffffffffU);
		update_crc(data, size);
		assert(mt6797_image_plan_prepare(&plan, data, size) == -1);
		assert(!plan.valid && !plan.sections && !plan.image.data);
		assert(mt6797_image_plan_get_ordinary(&plan, 0, &view) == -1);
		assert(!view.data && !view.length);
		assert(mt6797_image_plan_describe(&plan, 0, &description) == -1);
		assert(!description.length);
		free(data);
		cases++;
	}
	for (size_t length = 0; length < 24; length++) {
		data = calloc(length ? length : 1, 1);
		assert(data);
		assert(mt6797_image_plan_prepare(&plan, data, length) == -1);
		free(data);
		cases++;
	}
	data = make(4, &size);
	data[24 + 16 * 3 + 6] = 1;
	update_crc(data, size);
	assert(mt6797_image_plan_prepare(&plan, data, size) == -2);
	assert(mt6797_image_plan_admit(&plan) == -1);
	free(data);
	data = make(2, &size);
	assert(!mt6797_image_plan_prepare(&plan, data, size));
	mt6797_image_plan_invalidate(&plan);
	assert(mt6797_image_plan_get_ordinary(&plan, 0, &view) == -1);
	assert(!view.data);
	free(data);
	return cases == 280 ? 0 : 1;
}
