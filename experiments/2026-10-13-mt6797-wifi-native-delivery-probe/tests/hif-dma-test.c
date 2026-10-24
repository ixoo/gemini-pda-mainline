/* SPDX-License-Identifier: GPL-2.0-only */
/* Host fixture for the AP-DMA data-port transfer (proposal 0260): the vendor
 * register sequence against a modelled channel, the bounce-buffer copy in
 * both directions, the address-extension bits, the completion poll and its
 * timeout, and the attach/free pairing. No hardware.
 */
#define MT6797_HIF_HOST_TEST
#include <string.h>
#include <stdio.h>
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
static int dma_set_mask_and_coherent(struct device *d, u64 mask) { d->dma_mask_bits = mask == DMA_BIT_MASK(32) ? 32 : 0; return 0; }
static unsigned char *coherent;
static dma_addr_t coherent_phys = 0x8a000000ULL;
static void *dma_alloc_coherent(struct device *d, size_t n, dma_addr_t *phys, gfp_t f)
{ (void)d; (void)f; coherent = calloc(1, n); *phys = coherent_phys; return coherent; }
static void dma_free_coherent(struct device *d, size_t n, void *v, dma_addr_t p)
{ (void)d; (void)n; assert(v == coherent && p == coherent_phys); free(v); coherent = NULL; }
int mt6797_test_dma_read(void *address, unsigned int *value);
int mt6797_test_dma_write(unsigned int value, void *address);
#include "hif.c"

/* Modelled HIF window (setup word at 0) and AP-DMA channel registers. */
static u8 *window;
static u32 regs[0x80 / 4];
static unsigned setup_words, dma_writes;
static u32 last_setup;
static unsigned char fifo_content[2048];   /* what a port read would return */
static unsigned char fifo_captured[2048];  /* what a port write delivered */
static bool engine_completes = true;
static unsigned transfers;

u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long a, unsigned long b) { (void)a; (void)b; assert(false); }
int mt6797_test_read(void *address, unsigned int *value) { (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
	assert(address == window);	/* only the setup word; data words never go through PIO here */
	last_setup = value; setup_words++;
	return 0;
}
static void engine_run(void)
{
	u32 con = regs[0x18 / 4], len = regs[0x24 / 4] & 0xfffff;
	u32 src = regs[0x1c / 4], dst = regs[0x20 / 4];

	assert(con & BIT(31));			/* bus increment */
	assert((con & GENMASK(17, 16)) == (3U << 16));	/* burst 4/4 */
	assert(!(con & BIT(1)));			/* no fixed addressing */
	if (con & BIT(0)) {			/* read: FIFO -> memory */
		assert(src == 0x180f1000U && dst == (u32)coherent_phys);
		memcpy(coherent, fifo_content, len);
	} else {				/* write: memory -> FIFO */
		assert(dst == 0x180f1000U && src == (u32)coherent_phys);
		memcpy(fifo_captured, coherent, len);
	}
	transfers++;
	if (engine_completes) {
		regs[0] |= BIT(0);		/* INT_FLAG */
		regs[0x08 / 4] &= ~BIT(0);	/* EN clears when done */
	}
}
int mt6797_test_dma_read(void *address, unsigned int *value)
{
	size_t off = (u8 *)address - (u8 *)regs;
	assert(off < sizeof(regs) && !(off & 3));
	*value = regs[off / 4];
	return 0;
}
int mt6797_test_dma_write(unsigned int value, void *address)
{
	size_t off = (u8 *)address - (u8 *)regs;
	assert(off < sizeof(regs) && !(off & 3));
	dma_writes++;
	regs[off / 4] = value;
	if (off == 0x08 && (value & BIT(0)))
		engine_run();
	return 0;
}

static struct mt6797_hif *make(bool addr2, struct device *dev, struct clk *clk)
{
	static struct mt6797_init_transaction transaction;
	struct mt6797_hif *hif;

	transaction.phase = MT6797_INIT_IDLE;
	window = calloc(1, 0x1004);
	hif = mt6797_hif_alloc(window, 0x1004, &transaction);
	assert(!IS_ERR(hif));
	hif->deadline_ns = 1000000;
	assert(!mt6797_hif_attach_dma(hif, regs, 0x180f1000ULL, dev, clk, addr2));
	assert(hif->dma == (void *)regs && hif->dma_buffer == coherent && clk->enabled == 1);
	assert(mt6797_hif_attach_dma(hif, regs, 0x180f1000ULL, dev, clk, addr2) == -EINVAL);
	return hif;
}

int main(void)
{
	struct device dev = {0};
	struct clk clk = {0};
	struct mt6797_hif_pio_result result;
	struct mt6797_hif_command cmd;
	unsigned char payload[1518], out[2560];
	struct mt6797_hif *hif;
	unsigned i;

	for (i = 0; i < sizeof(payload); i++)
		payload[i] = (unsigned char)(i * 7 + 3);

	/* 1. Read, 1518 bytes, extension bits on: block mode, bounce copy exact. */
	hif = make(true, &dev, &clk);
	memset(regs, 0, sizeof(regs)); setup_words = 0; dma_writes = 0; transfers = 0;
	memcpy(fifo_content, payload, sizeof(payload));
	assert(!mt6797_hif_encode_command(0x50, MT6797_HIF_READ, MT6797_HIF_DMA_ENABLED, 1518, 2560, &cmd));
	assert(cmd.transfer_bytes == 1536 && (cmd.word & BIT(27)));	/* three blocks */
	assert(!mt6797_hif_dma_transfer(hif, 0x50, MT6797_HIF_READ, out, 1518, sizeof(out), &result));
	assert(setup_words == 1 && last_setup == cmd.word);
	assert(result.setup_submitted && result.transfer_complete && result.data_bytes == 1536);
	assert(!memcmp(out, payload, 1518));
	assert(transfers == 1 && hif->dma_rx == 1 && hif->dma_tx == 0 && hif->dma_failures == 0);
	assert((regs[0x54 / 4] & BIT(0)) && (regs[0x58 / 4] & BIT(0)));	/* extension bits set */
	assert(!(regs[0] & BIT(0)));			/* flag acknowledged */
	assert(!(regs[0x04 / 4] & BIT(0)));		/* interrupt masked again */
	assert(!(regs[0x08 / 4] & BIT(0)));		/* EN seen clear */

	/* 2. Write, 342 bytes, byte mode: padding zeroed, FIFO receives the frame. */
	memset(fifo_captured, 0xee, sizeof(fifo_captured));
	assert(!mt6797_hif_encode_command(0x34, MT6797_HIF_WRITE, MT6797_HIF_DMA_ENABLED, 342, 2560, &cmd));
	assert(cmd.transfer_bytes == 344 && !(cmd.word & BIT(27)));
	assert(!mt6797_hif_dma_transfer(hif, 0x34, MT6797_HIF_WRITE, payload, 342, sizeof(payload), &result));
	assert(last_setup == cmd.word && result.data_bytes == 344);
	assert(!memcmp(fifo_captured, payload, 342) && fifo_captured[342] == 0 && fifo_captured[343] == 0);
	assert(hif->dma_tx == 1 && transfers == 2);

	/* 3. Timeout: the engine never completes; context poisoned like a PIO fault. */
	engine_completes = false;
	assert(mt6797_hif_dma_transfer(hif, 0x50, MT6797_HIF_READ, out, 200, sizeof(out), &result) == -ETIMEDOUT);
	assert(hif->dma_failures == 1 && !(regs[0x04 / 4] & BIT(0)));
	engine_completes = true;
	regs[0x08 / 4] = 0;

	/* 4. Capacity below the rounded transfer is refused before the copy. */
	assert(mt6797_hif_dma_transfer(hif, 0x50, MT6797_HIF_READ, out, 1518, 1520, &result) == -EMSGSIZE);

	/* 5. Free releases the buffer and the clock. */
	mt6797_hif_free(hif);
	assert(coherent == NULL && clk.enabled == 0);
	free(window);

	/* 6. Extension bits off: the ADDR2 registers stay untouched. */
	hif = make(false, &dev, &clk);
	memset(regs, 0, sizeof(regs));
	assert(!mt6797_hif_dma_transfer(hif, 0x54, MT6797_HIF_READ, out, 100, sizeof(out), &result));
	assert(!(regs[0x54 / 4] & BIT(0)) && !(regs[0x58 / 4] & BIT(0)) && regs[0x1c / 4] == 0x180f1000U);
	assert(result.data_bytes == 104);	/* eight-byte receive alignment */
	mt6797_hif_free(hif);
	free(window);
	printf("hif-dma-test: PASS (%u transfers)\n", transfers);
	return 0;
}
