// SPDX-License-Identifier: GPL-2.0-only

#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/limits.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_reserved_mem.h>
#include <linux/platform_device.h>
#include <linux/sizes.h>
#include <linux/slab.h>
#include <linux/soc/mediatek/mtk-ram-console.h>
#include <linux/string.h>
#include <linux/unaligned.h>

#if IS_ENABLED(CONFIG_MTK_RAM_CONSOLE_READER_KUNIT_TEST)
#include <kunit/test.h>
#endif

#define MTK_RAM_CONSOLE_READER_SIZE	SZ_64K
#define MTK_RAM_CONSOLE_SIGNATURE	0x43474244
#define MTK_RAM_CONSOLE_STATUS_OFFSET	64
#define MTK_RAM_CONSOLE_OFF_LPL		128
#define MTK_RAM_CONSOLE_OFF_LK		192
#define MTK_RAM_CONSOLE_OFF_LLK		256
#define MTK_RAM_CONSOLE_OFF_LINUX	320

typedef int (*mtk_ram_console_copy_fn)(void *context, void *destination,
				       size_t size);

struct mtk_ram_console_reader_state {
	bool attempted;
	struct mtk_ram_console_snapshot snapshot;
};

struct mtk_ram_console_map_context {
	resource_size_t start;
	size_t size;
};

static DEFINE_MUTEX(mtk_ram_console_reader_lock);
static struct mtk_ram_console_reader_state mtk_ram_console_reader_state;

static int
mtk_ram_console_capture(struct mtk_ram_console_reader_state *state,
			mtk_ram_console_copy_fn copy, void *context,
			size_t size)
{
	struct mtk_ram_console_snapshot snapshot = {};
	void *buffer;
	int ret;

	if (!state || !copy)
		return -EINVAL;
	if (size != MTK_RAM_CONSOLE_READER_SIZE)
		return -EMSGSIZE;
	if (state->attempted)
		return -EALREADY;

	state->attempted = true;
	state->snapshot = (struct mtk_ram_console_snapshot){};
	buffer = kmalloc(size, GFP_KERNEL);
	if (!buffer)
		return -ENOMEM;

	ret = copy(context, buffer, size);
	if (!ret)
		ret = mtk_ram_console_parse(buffer, size, &snapshot);
	kfree_sensitive(buffer);
	if (ret)
		return ret;

	state->snapshot = snapshot;
	return 0;
}

static int
mtk_ram_console_state_get(struct mtk_ram_console_reader_state *state,
			  struct mtk_ram_console_snapshot *snapshot)
{
	if (!snapshot)
		return -EINVAL;
	*snapshot = (struct mtk_ram_console_snapshot){};
	if (!state)
		return -EINVAL;
	if (!state->snapshot.valid)
		return -ENODATA;

	*snapshot = state->snapshot;
	return 0;
}

int mtk_ram_console_snapshot_get(struct mtk_ram_console_snapshot *snapshot)
{
	int ret;

	mutex_lock(&mtk_ram_console_reader_lock);
	ret = mtk_ram_console_state_get(&mtk_ram_console_reader_state, snapshot);
	mutex_unlock(&mtk_ram_console_reader_lock);

	return ret;
}
EXPORT_SYMBOL_GPL(mtk_ram_console_snapshot_get);

static int mtk_ram_console_copy_reserved(void *context, void *destination,
					 size_t size)
{
	struct mtk_ram_console_map_context *map = context;
	void *source;

	if (!map || map->size != size)
		return -EINVAL;

	source = memremap(map->start, map->size, MEMREMAP_WB);
	if (!source)
		return -ENOMEM;

	memcpy(destination, source, size);
	memunmap(source);
	return 0;
}

static int mtk_ram_console_reader_probe(struct platform_device *pdev)
{
	struct device_node *memory;
	struct resource resource;
	struct mtk_ram_console_map_context map;
	int count;
	int ret;

	count = of_reserved_mem_region_count(pdev->dev.of_node);
	if (count != 1)
		return dev_err_probe(&pdev->dev, -EINVAL,
				     "expected one memory-region, found %d\n",
				     count);

	memory = of_parse_phandle(pdev->dev.of_node, "memory-region", 0);
	if (!memory)
		return dev_err_probe(&pdev->dev, -EINVAL,
				     "missing memory-region\n");
	if (!of_device_is_available(memory) ||
	    !of_property_read_bool(memory, "no-map")) {
		of_node_put(memory);
		return dev_err_probe(&pdev->dev, -EINVAL,
				     "memory-region must be available and no-map\n");
	}

	ret = of_reserved_mem_region_to_resource(pdev->dev.of_node, 0,
						 &resource);
	of_node_put(memory);
	if (ret)
		return dev_err_probe(&pdev->dev, ret,
				     "failed to resolve memory-region\n");
	if (resource.start > resource.end ||
	    resource_size(&resource) != MTK_RAM_CONSOLE_READER_SIZE ||
	    !IS_ALIGNED(resource.start, PAGE_SIZE))
		return dev_err_probe(&pdev->dev, -EINVAL,
				     "memory-region must be one aligned 64 KiB range\n");

	map.start = resource.start;
	map.size = resource_size(&resource);
	mutex_lock(&mtk_ram_console_reader_lock);
	ret = mtk_ram_console_capture(&mtk_ram_console_reader_state,
				      mtk_ram_console_copy_reserved, &map,
				      map.size);
	mutex_unlock(&mtk_ram_console_reader_lock);
	if (ret)
		return dev_err_probe(&pdev->dev, ret,
				     "retained ram-console capture failed\n");

	dev_info(&pdev->dev, "captured immutable retained ram-console snapshot\n");
	return 0;
}

static const struct of_device_id mtk_ram_console_reader_of_match[] = {
	{ .compatible = "mediatek,mt6797-ram-console" },
	{}
};
MODULE_DEVICE_TABLE(of, mtk_ram_console_reader_of_match);

static struct platform_driver mtk_ram_console_reader_driver = {
	.probe = mtk_ram_console_reader_probe,
	.driver = {
		.name = "mtk-ram-console-reader",
		.of_match_table = mtk_ram_console_reader_of_match,
	},
};
module_platform_driver(mtk_ram_console_reader_driver);

#if IS_ENABLED(CONFIG_MTK_RAM_CONSOLE_READER_KUNIT_TEST)
struct mtk_ram_console_test_copy {
	u8 *source;
	unsigned int calls;
	int result;
};

static void mtk_ram_console_test_word(u8 *buffer, unsigned int word, u32 value)
{
	put_unaligned_le32(value, buffer + word * sizeof(u32));
}

static void mtk_ram_console_test_fixture(u8 *buffer, u32 status)
{
	memset(buffer, 0, MTK_RAM_CONSOLE_READER_SIZE);
	mtk_ram_console_test_word(buffer, 0, MTK_RAM_CONSOLE_SIGNATURE);
	mtk_ram_console_test_word(buffer, 1, MTK_RAM_CONSOLE_STATUS_OFFSET);
	mtk_ram_console_test_word(buffer, 2, MTK_RAM_CONSOLE_OFF_LPL);
	mtk_ram_console_test_word(buffer, 3, sizeof(u32));
	mtk_ram_console_test_word(buffer, 4, MTK_RAM_CONSOLE_OFF_LK);
	mtk_ram_console_test_word(buffer, 5, MTK_RAM_CONSOLE_OFF_LLK);
	mtk_ram_console_test_word(buffer, 6, 64);
	mtk_ram_console_test_word(buffer, 10, MTK_RAM_CONSOLE_READER_SIZE);
	mtk_ram_console_test_word(buffer, 11, MTK_RAM_CONSOLE_OFF_LINUX);
	mtk_ram_console_test_word(buffer, 12, MTK_RAM_CONSOLE_OFF_LINUX);
	put_unaligned_le32(status, buffer + MTK_RAM_CONSOLE_STATUS_OFFSET);
}

static int mtk_ram_console_test_copy(void *context, void *destination,
				     size_t size)
{
	struct mtk_ram_console_test_copy *copy = context;

	copy->calls++;
	if (copy->result)
		return copy->result;
	memcpy(destination, copy->source, size);
	return 0;
}

static u8 *mtk_ram_console_test_buffer(struct kunit *test, u32 status)
{
	u8 *buffer;

	buffer = kunit_kzalloc(test, MTK_RAM_CONSOLE_READER_SIZE, GFP_KERNEL);
	if (!buffer)
		return NULL;
	mtk_ram_console_test_fixture(buffer, status);
	return buffer;
}

static void mtk_ram_console_reader_invalid_arguments_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {
		.preloader_status = U32_MAX,
		.valid = true,
	};
	struct mtk_ram_console_test_copy copy = {};

	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_capture(NULL, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_capture(&state, NULL, &copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, -EMSGSIZE,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE - 1));
	KUNIT_EXPECT_FALSE(test, state.attempted);
	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_state_get(NULL, &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_state_get(&state, NULL));
}

static void mtk_ram_console_reader_exact_copy_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {};
	struct mtk_ram_console_test_copy copy = {
		.source = mtk_ram_console_test_buffer(test, 0xa5c33ca5),
	};

	KUNIT_ASSERT_NOT_NULL(test, copy.source);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, 1U, copy.calls);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_state_get(&state, &snapshot));
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
	KUNIT_EXPECT_EQ(test, 0xa5c33ca5U, snapshot.preloader_status);
}

static void mtk_ram_console_reader_copy_failure_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {};
	struct mtk_ram_console_test_copy copy = {
		.source = mtk_ram_console_test_buffer(test, 0),
		.result = -EIO,
	};

	KUNIT_ASSERT_NOT_NULL(test, copy.source);
	KUNIT_EXPECT_EQ(test, -EIO,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, 1U, copy.calls);
	KUNIT_EXPECT_TRUE(test, state.attempted);
	KUNIT_EXPECT_EQ(test, -ENODATA,
			mtk_ram_console_state_get(&state, &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
}

static void mtk_ram_console_reader_parser_failure_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {};
	struct mtk_ram_console_test_copy copy = {
		.source = mtk_ram_console_test_buffer(test, 0),
	};

	KUNIT_ASSERT_NOT_NULL(test, copy.source);
	mtk_ram_console_test_word(copy.source, 0, 0);
	KUNIT_EXPECT_EQ(test, -EBADMSG,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, 1U, copy.calls);
	KUNIT_EXPECT_EQ(test, -ENODATA,
			mtk_ram_console_state_get(&state, &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
}

static void mtk_ram_console_reader_second_capture_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {};
	struct mtk_ram_console_test_copy copy = {
		.source = mtk_ram_console_test_buffer(test, BIT(3)),
	};

	KUNIT_ASSERT_NOT_NULL(test, copy.source);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	put_unaligned_le32(BIT(4), copy.source + MTK_RAM_CONSOLE_STATUS_OFFSET);
	KUNIT_EXPECT_EQ(test, -EALREADY,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	KUNIT_EXPECT_EQ(test, 1U, copy.calls);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_state_get(&state, &snapshot));
	KUNIT_EXPECT_EQ(test, BIT(3), snapshot.preloader_status);
}

static void mtk_ram_console_reader_source_independence_test(struct kunit *test)
{
	struct mtk_ram_console_reader_state state = {};
	struct mtk_ram_console_snapshot snapshot = {};
	struct mtk_ram_console_test_copy copy = {
		.source = mtk_ram_console_test_buffer(test, 0x12345678),
	};

	KUNIT_ASSERT_NOT_NULL(test, copy.source);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
						&copy,
						MTK_RAM_CONSOLE_READER_SIZE));
	memset(copy.source, 0, MTK_RAM_CONSOLE_READER_SIZE);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_state_get(&state, &snapshot));
	KUNIT_EXPECT_EQ(test, 0x12345678U, snapshot.preloader_status);
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
}

static void mtk_ram_console_reader_every_bit_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot;
	u8 *source = mtk_ram_console_test_buffer(test, 0);
	unsigned int bit;

	KUNIT_ASSERT_NOT_NULL(test, source);
	for (bit = 0; bit < 32; bit++) {
		struct mtk_ram_console_reader_state state = {};
		struct mtk_ram_console_test_copy copy = {
			.source = source,
		};
		int ret;

		mtk_ram_console_test_fixture(source, BIT(bit));
		ret = mtk_ram_console_capture(&state, mtk_ram_console_test_copy,
					      &copy,
					      MTK_RAM_CONSOLE_READER_SIZE);
		KUNIT_ASSERT_EQ(test, 0, ret);
		KUNIT_ASSERT_EQ(test, 0,
				mtk_ram_console_state_get(&state, &snapshot));
		KUNIT_EXPECT_EQ(test, BIT(bit), snapshot.preloader_status);
		KUNIT_EXPECT_TRUE(test, snapshot.valid);
		KUNIT_EXPECT_EQ(test, 1U, copy.calls);
	}
}

static struct kunit_case mtk_ram_console_reader_cases[] = {
	KUNIT_CASE(mtk_ram_console_reader_invalid_arguments_test),
	KUNIT_CASE(mtk_ram_console_reader_exact_copy_test),
	KUNIT_CASE(mtk_ram_console_reader_copy_failure_test),
	KUNIT_CASE(mtk_ram_console_reader_parser_failure_test),
	KUNIT_CASE(mtk_ram_console_reader_second_capture_test),
	KUNIT_CASE(mtk_ram_console_reader_source_independence_test),
	KUNIT_CASE(mtk_ram_console_reader_every_bit_test),
	{}
};

static struct kunit_suite mtk_ram_console_reader_suite = {
	.name = "mtk-ram-console-reader",
	.test_cases = mtk_ram_console_reader_cases,
};

kunit_test_suite(mtk_ram_console_reader_suite);
#endif

MODULE_DESCRIPTION("MediaTek retained ram-console immutable copy owner");
MODULE_LICENSE("GPL");
