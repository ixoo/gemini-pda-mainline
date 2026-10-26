/* SPDX-License-Identifier: GPL-2.0-only */
/* The HT40 join commands (0323) on the actual hif.c: the channel privilege
 * request with ucRfSco 3 is the 20 MHz request with byte 4 set and nothing
 * else; only SCN, or SCB on channel 40, is accepted, and a refusal reaches no
 * bus; the BSS command's RLM ucRfSco (byte 71) follows the HT operation's
 * info 1 as sent. With CONFIG_MT6797_HT40_TX (0324) an ordinary data
 * descriptor carries FIX_BW_40 in byte 25 only after the HIF is told the
 * join is HT40, and is otherwise unchanged. With CONFIG_MT6797_HT_SGI_TX
 * (0327) it carries the guard interval bit (byte 27 bit 7) only after the
 * HIF is told short GI, and only for an HT mixed-mode fixed rate. The
 * state-3 station record carries the peer HT capability at the vendor
 * offsets, and with CONFIG_MT6797_HT_STA_RECORD_FULL also its rx highest
 * rate, transmit rate info, beamforming, A-MPDU parameters and ASEL
 * (34-39, 44-49), nothing else changed. Built by run-ht40-hif-test.py with
 * and without each option.
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
static inline __attribute__((unused)) void mutex_lock(struct mutex *m) { assert(!m->held); m->held = true; }
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
	/* The state-3 station record: legacy, then with a distinct-byte HT
	 * capability body. Outside the HT fields the two are identical.
	 */
	{
		static const u8 ap[6] = { 2, 0, 0, 0, 0, 1 };
		u8 ht_cap[26], legacy[124], *ht = sent + 8;

		for (unsigned int i = 0; i < sizeof(ht_cap); i++)
			ht_cap[i] = 0xa0 + i;
		fresh(&hif);
		assert(!mt6797_hif_join_station_qos(&hif, 21, ap, 3, 1, 0x3fc0, 0x540, true,
						   NULL, 1000000));
		memcpy(legacy, sent + 8, sizeof(legacy));
		assert(legacy[13] == 8 && legacy[74] == 0x4b);
		fresh(&hif);
		assert(!mt6797_hif_join_station_qos(&hif, 21, ap, 3, 1, 0x3fc0, 0x540, true,
						   ht_cap, 1000000));
		for (unsigned int i = 0; i < sizeof(legacy); i++) {
			bool full = (i >= 34 && i <= 39) || (i >= 44 && i <= 49);

			if (i == 13)
				assert(ht[i] == 0x18);
			else if (i == 21)
				assert(ht[i] == ht_cap[3]);
			else if (i == 22)
				assert(ht[i] == (ht_cap[7] & 1));
			else if (i >= 24 && i <= 33)
				assert(ht[i] == ht_cap[i - 21]);
			else if (i >= 40 && i <= 41)
				assert(ht[i] == ht_cap[i - 40]);
			else if (i >= 42 && i <= 43)
				assert(ht[i] == ht_cap[i - 23]);
#ifdef CONFIG_MT6797_HT_STA_RECORD_FULL
			else if (i >= 34 && i <= 39)
				assert(ht[i] == ht_cap[i - 21]);
			else if (i >= 44 && i <= 47)
				assert(ht[i] == ht_cap[i - 23]);
			else if (i == 48)
				assert(ht[i] == ht_cap[2]);
			else if (i == 49)
				assert(ht[i] == ht_cap[25]);
#endif
			else
				assert(ht[i] == legacy[i] && (!full || !ht[i]));
		}
	}
#ifdef CONFIG_MT6797_HT40_TX
	/* An ordinary data frame: the descriptor at 20 MHz, then at 40 MHz. */
	{
		u8 frame[60] = { 2, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 2, 0x08, 0x00 }, d20[64];

		fresh(&hif);
		hif.normal.tc1_limit = hif.normal.tc1_free = 12;
		assert(!mt6797_hif_send_data_report(&hif, frame, sizeof(frame), 1, 0, false,
						    500, 3, 1000000));
		memcpy(d20, sent, sizeof(d20));
		assert(d20[25] == 0 && d20[11] == 0x80);	/* fixed rate, no bandwidth */
		mt6797_hif_set_data_bw40(&hif, true);
		memset(sent, 0, sizeof(sent));
		calls = 0;
		hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
		hif.normal.tc1_free = hif.normal.tc1_limit;
		assert(!mt6797_hif_send_data_report(&hif, frame, sizeof(frame), 1, 0, false,
						    500, 3, 1000000));
		for (unsigned int i = 0; i < sizeof(d20); i++)
			assert(i == 25 ? sent[i] == 5 : sent[i] == d20[i]);
		/* told 20 MHz again: back to the 20 MHz descriptor */
		mt6797_hif_set_data_bw40(&hif, false);
		memset(sent, 0, sizeof(sent));
		calls = 0;
		hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
		hif.normal.tc1_free = hif.normal.tc1_limit;
		assert(!mt6797_hif_send_data_report(&hif, frame, sizeof(frame), 1, 0, false,
						    500, 3, 1000000));
		assert(!memcmp(sent, d20, sizeof(d20)));
#ifdef CONFIG_MT6797_HT_SGI_TX
		/* short GI on: byte 27 bit 7, and only for an HT mixed-mode code */
		mt6797_hif_set_data_sgi(&hif, true);
		memset(sent, 0, sizeof(sent));
		calls = 0;
		hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
		hif.normal.tc1_free = hif.normal.tc1_limit;
		assert(!mt6797_hif_send_data_report(&hif, frame, sizeof(frame), 1, 0, false,
						    500, 3, 1000000));
		for (unsigned int i = 0; i < sizeof(d20); i++)
			assert(i != 27 ? sent[i] == d20[i] :
			       ((MT6797_DATA_FIXED_RATE_CODE >> 6) & 7) == 2 ?
			       sent[i] == (d20[i] | 0x80) : sent[i] == d20[i]);
		mt6797_hif_set_data_sgi(&hif, false);
#endif
	}
#endif
	free(mapping);
#if defined(CONFIG_MT6797_HT_STA_RECORD_FULL)
	printf("ht40-hif-test: PASS (complete HT station record)\n");
#elif defined(CONFIG_MT6797_HT_SGI_TX)
	printf("ht40-hif-test: PASS (HT40, transmit at 40 MHz, short GI, rate code 0x%x)\n",
	       (unsigned int)MT6797_DATA_FIXED_RATE_CODE);
#elif defined(CONFIG_MT6797_HT40_TX)
	printf("ht40-hif-test: PASS (HT40, transmit at 40 MHz)\n");
#elif defined(CONFIG_MT6797_HT40)
	printf("ht40-hif-test: PASS (HT40)\n");
#else
	printf("ht40-hif-test: PASS (option off)\n");
#endif
	return 0;
}
