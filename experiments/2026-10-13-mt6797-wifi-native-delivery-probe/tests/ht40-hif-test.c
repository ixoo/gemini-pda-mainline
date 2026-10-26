/* SPDX-License-Identifier: GPL-2.0-only */
/* The HT40 join commands (0323) on the actual hif.c: the channel privilege
 * request with ucRfSco 3 is the 20 MHz request with byte 4 set and nothing
 * else; only SCN, or SCB on channel 40, is accepted, and a refusal reaches no
 * bus; the BSS command's RLM ucRfSco (byte 71) follows the HT operation's
 * info 1 as sent. Built by run-ht40-hif-test.py with and without the option.
 * The bus is a capture: the setup word and the data words of each command.
 */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "test-compat.h"
typedef uint16_t u16;
typedef uint64_t dma_addr_t;
typedef uint64_t phys_addr_t;
typedef uint32_t gfp_t;
struct device { int dma_mask_bits; };
struct clk { int enabled; };
#define BIT(n) (1U << (n))
#define GENMASK(h, l) (((~0U) << (l)) & (~0U >> (31 - (h))))
#define lower_32_bits(n) ((u32)((n) & 0xffffffffULL))
#define upper_32_bits(n) ((u32)(((n) >> 16) >> 16))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define dma_wmb() do { } while (0)
#define dma_rmb() do { } while (0)
#define cpu_relax() do { } while (0)
#define DMA_BIT_MASK(n) ((1ULL << (n)) - 1)
static int clk_prepare_enable(struct clk *c) { c->enabled++; return 0; }
static void clk_disable_unprepare(struct clk *c) { c->enabled--; }
static int dma_set_mask_and_coherent(struct device *d, u64 mask) { (void)d; (void)mask; return 0; }
static void *dma_alloc_coherent(struct device *d, size_t n, dma_addr_t *phys, gfp_t f)
{ (void)d; (void)f; *phys = 0; return calloc(1, n); }
static void dma_free_coherent(struct device *d, size_t n, void *v, dma_addr_t p)
{ (void)d; (void)n; (void)p; free(v); }
int mt6797_test_dma_read(void *address, unsigned int *value) { (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_dma_write(unsigned int value, void *address) { (void)value; (void)address; assert(false); return -EIO; }
#include "hif.c"

static u8 *mapping;
static u8 sent[512];
static unsigned int calls;
u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long a, unsigned long b) { (void)a; (void)b; assert(false); }
int mt6797_test_read(void *address, unsigned int *value) { (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
	if (calls) {
		assert(address == mapping + 0x1000 && (calls - 1) * 4 + 4 <= sizeof(sent));
		memcpy(sent + (calls - 1) * 4, &value, 4);
	} else {
		assert(address == mapping);
	}
	calls++;
	return 0;
}

static struct mt6797_init_transaction transaction;
static unsigned char history[32];

static void fresh(struct mt6797_hif *hif)
{
	memset(hif, 0, sizeof(*hif));
	memset(history, 0, sizeof(history));
	transaction.phase = MT6797_INIT_IDLE;
	hif->transaction = &transaction;
	hif->firmware_ready = true;
	hif->capability_complete = true;
	hif->base = mapping;
	mutex_init(&hif->mutex);
	hif->io = (struct mt6797_hif_pio_io){ .context = hif, .write = mt6797_hif_write,
					     .read = mt6797_hif_read };
	assert(!mt6797_normal_admit(&hif->normal, 4, 4, history));
	hif->normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	memset(sent, 0, sizeof(sent));
	calls = 0;
}

int main(void)
{
	struct mt6797_hif hif;
	u8 channel20[16], channel40[16];

	mapping = calloc(1, 0x1004);
	assert(mapping);
	/* The 20 MHz request as it stands: SCN, band 5 GHz. */
	fresh(&hif);
	assert(!mt6797_hif_join_channel(&hif, 19, 7, 40, 9000, false, 1000000));
	memcpy(channel20, sent + 8, 16);
	assert(channel20[3] == 40 && channel20[4] == 0 && channel20[5] == 2);
#ifdef CONFIG_MT6797_HT40
	/* SCB: byte 4 alone differs. */
	fresh(&hif);
	assert(!mt6797_hif_join_channel_sco(&hif, 19, 7, 40, 3, 9000, 1000000));
	memcpy(channel40, sent + 8, 16);
	for (unsigned int i = 0; i < 16; i++)
		assert(i == 4 ? channel40[i] == 3 : channel40[i] == channel20[i]);
	/* SCN through the same entry point is the 20 MHz request exactly. */
	fresh(&hif);
	assert(!mt6797_hif_join_channel_sco(&hif, 19, 7, 40, 0, 9000, 1000000));
	assert(!memcmp(sent + 8, channel20, 16));
	/* SCA, the reserved value, or SCB off channel 40: refused before any bus. */
	fresh(&hif);
	assert(mt6797_hif_join_channel_sco(&hif, 19, 7, 40, 1, 9000, 1000000) == -EINVAL);
	assert(mt6797_hif_join_channel_sco(&hif, 19, 7, 40, 2, 9000, 1000000) == -EINVAL);
	assert(mt6797_hif_join_channel_sco(&hif, 19, 7, 36, 3, 9000, 1000000) == -EINVAL);
	assert(!calls && hif.normal.tc4_free == 4);
#else
	(void)channel40;
#endif
	/* The BSS command: RLM ucRfSco (71) from the HT operation as sent. */
	{
		static const u8 ap[6] = { 2, 0, 0, 0, 0, 1 };
		u8 ht_op[22] = { 40, 0x07, 0x06, 0 };

		fresh(&hif);
		assert(!mt6797_hif_join_bss_qos(&hif, 20, ap, (const u8 *)"lab", 3, 0x3fc0, 0x540,
						false, true, true, ht_op, 1000000));
		assert(sent[8 + 80] == 0x07);
#ifdef CONFIG_MT6797_HT40
		assert(sent[8 + 71] == 3);
		/* the caller's masked info 1 (no HT40) leaves SCN */
		ht_op[1] = 0;
		fresh(&hif);
		assert(!mt6797_hif_join_bss_qos(&hif, 20, ap, (const u8 *)"lab", 3, 0x3fc0, 0x540,
						false, true, true, ht_op, 1000000));
		assert(sent[8 + 71] == 0 && sent[8 + 80] == 0);
#else
		assert(sent[8 + 71] == 0);
#endif
	}
	free(mapping);
#ifdef CONFIG_MT6797_HT40
	printf("ht40-hif-test: PASS (HT40)\n");
#else
	printf("ht40-hif-test: PASS (option off)\n");
#endif
	return 0;
}
