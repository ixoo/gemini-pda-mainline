// SPDX-License-Identifier: GPL-2.0-only

#include <linux/bitops.h>
#include <linux/kernel.h>
#include <linux/limits.h>
#include <linux/module.h>
#include <linux/overflow.h>
#include <linux/soc/mediatek/mtk-ram-console.h>
#include <linux/string.h>
#include <linux/unaligned.h>

#if IS_ENABLED(CONFIG_MTK_RAM_CONSOLE_PARSER_KUNIT_TEST)
#include <kunit/test.h>
#endif

#define MTK_RAM_CONSOLE_SIGNATURE	0x43474244
#define MTK_RAM_CONSOLE_HEADER_SIZE	64
#define MTK_RAM_CONSOLE_LK_SIZE		64
#define MTK_RAM_CONSOLE_RECORD_ALIGN	64

enum mtk_ram_console_header_word {
	MTK_RC_SIGNATURE,
	MTK_RC_OFF_PL,
	MTK_RC_OFF_LPL,
	MTK_RC_SZ_PL,
	MTK_RC_OFF_LK,
	MTK_RC_OFF_LLK,
	MTK_RC_SZ_LK,
	MTK_RC_PADDING_0,
	MTK_RC_PADDING_1,
	MTK_RC_DUMP_STEP,
	MTK_RC_SZ_BUFFER,
	MTK_RC_OFF_LINUX,
	MTK_RC_OFF_CONSOLE,
	MTK_RC_LOG_START,
	MTK_RC_LOG_SIZE,
	MTK_RC_SZ_CONSOLE,
};

static u32 mtk_ram_console_word(const u8 *buffer,
				enum mtk_ram_console_header_word word)
{
	return get_unaligned_le32(buffer + word * sizeof(u32));
}

static int mtk_ram_console_aligned_end(u32 offset, u32 size, u32 *end)
{
	u32 aligned;

	if (check_add_overflow(size, MTK_RAM_CONSOLE_RECORD_ALIGN - 1,
			       &aligned))
		return -EOVERFLOW;
	aligned &= ~(MTK_RAM_CONSOLE_RECORD_ALIGN - 1);
	if (check_add_overflow(offset, aligned, end))
		return -EOVERFLOW;

	return 0;
}

int mtk_ram_console_parse(const void *buffer, size_t buffer_size,
			  struct mtk_ram_console_snapshot *snapshot)
{
	const u8 *bytes = buffer;
	u32 off_console;
	u32 off_linux;
	u32 off_llk;
	u32 off_lk;
	u32 off_lpl;
	u32 off_pl;
	u32 sz_lk;
	u32 sz_pl;
	u32 end;
	int ret;

	if (!snapshot)
		return -EINVAL;
	*snapshot = (struct mtk_ram_console_snapshot){};
	if (!buffer)
		return -EINVAL;
	if (buffer_size < MTK_RAM_CONSOLE_HEADER_SIZE)
		return -EMSGSIZE;
	if (buffer_size > U32_MAX)
		return -EOVERFLOW;
	if (mtk_ram_console_word(bytes, MTK_RC_SIGNATURE) !=
	    MTK_RAM_CONSOLE_SIGNATURE)
		return -EBADMSG;
	if (mtk_ram_console_word(bytes, MTK_RC_SZ_BUFFER) != buffer_size)
		return -EBADMSG;

	off_pl = mtk_ram_console_word(bytes, MTK_RC_OFF_PL);
	off_lpl = mtk_ram_console_word(bytes, MTK_RC_OFF_LPL);
	sz_pl = mtk_ram_console_word(bytes, MTK_RC_SZ_PL);
	off_lk = mtk_ram_console_word(bytes, MTK_RC_OFF_LK);
	off_llk = mtk_ram_console_word(bytes, MTK_RC_OFF_LLK);
	sz_lk = mtk_ram_console_word(bytes, MTK_RC_SZ_LK);
	off_linux = mtk_ram_console_word(bytes, MTK_RC_OFF_LINUX);
	off_console = mtk_ram_console_word(bytes, MTK_RC_OFF_CONSOLE);

	if (off_pl != MTK_RAM_CONSOLE_HEADER_SIZE || sz_pl < sizeof(u32))
		return -EBADMSG;
	ret = mtk_ram_console_aligned_end(off_pl, sz_pl, &end);
	if (ret)
		return ret;
	if (end != off_lpl || end > buffer_size)
		return -EBADMSG;
	ret = mtk_ram_console_aligned_end(off_lpl, sz_pl, &end);
	if (ret)
		return ret;
	if (end != off_lk || end > buffer_size)
		return -EBADMSG;

	if (sz_lk != MTK_RAM_CONSOLE_LK_SIZE)
		return -EBADMSG;
	ret = mtk_ram_console_aligned_end(off_lk, sz_lk, &end);
	if (ret)
		return ret;
	if (end != off_llk || end > buffer_size)
		return -EBADMSG;
	ret = mtk_ram_console_aligned_end(off_llk, sz_lk, &end);
	if (ret)
		return ret;
	if (end != off_linux || end > buffer_size)
		return -EBADMSG;
	if (off_console < off_linux || off_console > buffer_size)
		return -EBADMSG;

	snapshot->preloader_status = get_unaligned_le32(bytes + off_pl);
	snapshot->valid = true;
	return 0;
}
EXPORT_SYMBOL_GPL(mtk_ram_console_parse);

#if IS_ENABLED(CONFIG_MTK_RAM_CONSOLE_PARSER_KUNIT_TEST)
#define MTK_RAM_CONSOLE_TEST_SIZE	512
#define MTK_RAM_CONSOLE_TEST_OFF_PL	64
#define MTK_RAM_CONSOLE_TEST_OFF_LPL	128
#define MTK_RAM_CONSOLE_TEST_OFF_LK	192
#define MTK_RAM_CONSOLE_TEST_OFF_LLK	256
#define MTK_RAM_CONSOLE_TEST_OFF_LINUX	320
#define MTK_RAM_CONSOLE_TEST_OFF_CONSOLE	384

static void mtk_ram_console_test_word(u8 *buffer,
				      enum mtk_ram_console_header_word word,
				      u32 value)
{
	put_unaligned_le32(value, buffer + word * sizeof(u32));
}

static void mtk_ram_console_test_fixture(u8 *buffer, u32 status)
{
	memset(buffer, 0, MTK_RAM_CONSOLE_TEST_SIZE);
	mtk_ram_console_test_word(buffer, MTK_RC_SIGNATURE,
				  MTK_RAM_CONSOLE_SIGNATURE);
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_PL,
				  MTK_RAM_CONSOLE_TEST_OFF_PL);
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_LPL,
				  MTK_RAM_CONSOLE_TEST_OFF_LPL);
	mtk_ram_console_test_word(buffer, MTK_RC_SZ_PL, sizeof(u32));
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_LK,
				  MTK_RAM_CONSOLE_TEST_OFF_LK);
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_LLK,
				  MTK_RAM_CONSOLE_TEST_OFF_LLK);
	mtk_ram_console_test_word(buffer, MTK_RC_SZ_LK,
				  MTK_RAM_CONSOLE_LK_SIZE);
	mtk_ram_console_test_word(buffer, MTK_RC_SZ_BUFFER,
				  MTK_RAM_CONSOLE_TEST_SIZE);
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_LINUX,
				  MTK_RAM_CONSOLE_TEST_OFF_LINUX);
	mtk_ram_console_test_word(buffer, MTK_RC_OFF_CONSOLE,
				  MTK_RAM_CONSOLE_TEST_OFF_CONSOLE);
	put_unaligned_le32(status, buffer + MTK_RAM_CONSOLE_TEST_OFF_PL);
}

static void mtk_ram_console_invalid_arguments_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot = {
		.preloader_status = U32_MAX,
		.valid = true,
	};
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];

	mtk_ram_console_test_fixture(buffer, 0);
	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_parse(NULL, sizeof(buffer), &snapshot));
	KUNIT_EXPECT_EQ(test, 0U, snapshot.preloader_status);
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
	KUNIT_EXPECT_EQ(test, -EINVAL,
			mtk_ram_console_parse(buffer, sizeof(buffer), NULL));
}

static void mtk_ram_console_truncated_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot = {};
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];

	mtk_ram_console_test_fixture(buffer, 0);
	KUNIT_EXPECT_EQ(test, -EMSGSIZE,
			mtk_ram_console_parse(buffer,
					      MTK_RAM_CONSOLE_HEADER_SIZE - 1,
					      &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
}

static void mtk_ram_console_signature_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot = {};
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];

	mtk_ram_console_test_fixture(buffer, 0);
	mtk_ram_console_test_word(buffer, MTK_RC_SIGNATURE, 0);
	KUNIT_EXPECT_EQ(test, -EBADMSG,
			mtk_ram_console_parse(buffer, sizeof(buffer), &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
}

static void mtk_ram_console_buffer_size_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot = {};
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];

	mtk_ram_console_test_fixture(buffer, 0);
	mtk_ram_console_test_word(buffer, MTK_RC_SZ_BUFFER,
				  MTK_RAM_CONSOLE_TEST_SIZE - 1);
	KUNIT_EXPECT_EQ(test, -EBADMSG,
			mtk_ram_console_parse(buffer, sizeof(buffer), &snapshot));
	KUNIT_EXPECT_FALSE(test, snapshot.valid);
}

static void mtk_ram_console_preloader_layout_test(struct kunit *test)
{
	static const struct {
		enum mtk_ram_console_header_word word;
		u32 value;
	} corruptions[] = {
		{ MTK_RC_OFF_PL, MTK_RAM_CONSOLE_TEST_OFF_PL + 4 },
		{ MTK_RC_SZ_PL, 3 },
		{ MTK_RC_OFF_LPL, MTK_RAM_CONSOLE_TEST_OFF_LPL + 64 },
		{ MTK_RC_OFF_LK, MTK_RAM_CONSOLE_TEST_OFF_LK + 64 },
		{ MTK_RC_SZ_PL, U32_MAX },
	};
	struct mtk_ram_console_snapshot snapshot;
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];
	unsigned int index;

	for (index = 0; index < ARRAY_SIZE(corruptions); index++) {
		mtk_ram_console_test_fixture(buffer, 0);
		mtk_ram_console_test_word(buffer, corruptions[index].word,
					  corruptions[index].value);
		KUNIT_EXPECT_LT(test,
				mtk_ram_console_parse(buffer, sizeof(buffer),
						      &snapshot),
				0);
		KUNIT_EXPECT_FALSE(test, snapshot.valid);
	}
}

static void mtk_ram_console_lk_layout_test(struct kunit *test)
{
	static const struct {
		enum mtk_ram_console_header_word word;
		u32 value;
	} corruptions[] = {
		{ MTK_RC_SZ_LK, MTK_RAM_CONSOLE_LK_SIZE - 4 },
		{ MTK_RC_OFF_LLK, MTK_RAM_CONSOLE_TEST_OFF_LLK + 64 },
		{ MTK_RC_OFF_LINUX, MTK_RAM_CONSOLE_TEST_OFF_LINUX + 64 },
		{ MTK_RC_OFF_CONSOLE, MTK_RAM_CONSOLE_TEST_OFF_LINUX - 4 },
		{ MTK_RC_OFF_CONSOLE, MTK_RAM_CONSOLE_TEST_SIZE + 4 },
	};
	struct mtk_ram_console_snapshot snapshot;
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];
	unsigned int index;

	for (index = 0; index < ARRAY_SIZE(corruptions); index++) {
		mtk_ram_console_test_fixture(buffer, 0);
		mtk_ram_console_test_word(buffer, corruptions[index].word,
					  corruptions[index].value);
		KUNIT_EXPECT_EQ(test, -EBADMSG,
				mtk_ram_console_parse(buffer, sizeof(buffer),
						      &snapshot));
		KUNIT_EXPECT_FALSE(test, snapshot.valid);
	}
}

static void mtk_ram_console_exact_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot = {};
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];

	mtk_ram_console_test_fixture(buffer, 0xa5c33ca5);
	KUNIT_ASSERT_EQ(test, 0,
			mtk_ram_console_parse(buffer, sizeof(buffer), &snapshot));
	KUNIT_EXPECT_EQ(test, 0xa5c33ca5U, snapshot.preloader_status);
	KUNIT_EXPECT_TRUE(test, snapshot.valid);
}

static void mtk_ram_console_every_bit_test(struct kunit *test)
{
	struct mtk_ram_console_snapshot snapshot;
	u8 buffer[MTK_RAM_CONSOLE_TEST_SIZE];
	unsigned int bit;

	for (bit = 0; bit < 32; bit++) {
		mtk_ram_console_test_fixture(buffer, BIT(bit));
		KUNIT_ASSERT_EQ(test, 0,
				mtk_ram_console_parse(buffer, sizeof(buffer),
						      &snapshot));
		KUNIT_EXPECT_EQ(test, BIT(bit), snapshot.preloader_status);
		KUNIT_EXPECT_TRUE(test, snapshot.valid);
	}
}

static struct kunit_case mtk_ram_console_cases[] = {
	KUNIT_CASE(mtk_ram_console_invalid_arguments_test),
	KUNIT_CASE(mtk_ram_console_truncated_test),
	KUNIT_CASE(mtk_ram_console_signature_test),
	KUNIT_CASE(mtk_ram_console_buffer_size_test),
	KUNIT_CASE(mtk_ram_console_preloader_layout_test),
	KUNIT_CASE(mtk_ram_console_lk_layout_test),
	KUNIT_CASE(mtk_ram_console_exact_test),
	KUNIT_CASE(mtk_ram_console_every_bit_test),
	{}
};

static struct kunit_suite mtk_ram_console_suite = {
	.name = "mtk-ram-console-parser",
	.test_cases = mtk_ram_console_cases,
};

kunit_test_suite(mtk_ram_console_suite);
#endif

MODULE_DESCRIPTION("MediaTek retained ram-console wire-format parser");
MODULE_LICENSE("GPL");
