/* SPDX-License-Identifier: GPL-2.0-only */
/* Host fixture for receive batching (proposal 0268): the WHCR enable and
 * read-back, the 112-byte enhanced status block, one aggregated read per
 * non-empty queue split by the reported lengths, frames served in order
 * across passes, -EAGAIN when the cache is empty, one block read per pass,
 * and the refusals (count over sixteen, header mismatch). PIO only; no
 * hardware.
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
static int dma_set_mask_and_coherent(struct device *d, u64 mask) { (void)d; (void)mask; return 0; }
static void *dma_alloc_coherent(struct device *d, size_t n, dma_addr_t *phys, gfp_t f)
{ (void)d; (void)f; *phys = 0; return calloc(1, n); }
static void dma_free_coherent(struct device *d, size_t n, void *v, dma_addr_t p)
{ (void)d; (void)n; (void)p; free(v); }
int mt6797_test_dma_read(void *address, unsigned int *value) { (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_dma_write(unsigned int value, void *address) { (void)value; (void)address; assert(false); return -EIO; }
#include "hif.c"

/* Modelled HIF window: the setup word selects a register or port; data
 * words at 0x1000 come from that selection's stream.
 */
static u8 *window;
static unsigned int pending_port, pending_bytes, pending_offset;
static bool pending_write;
static u32 whcr = 0x00000a00;		/* some other length count before enable */
static u8 block[112];
static u8 queue_stream[2][40960];
static unsigned int queue_offset[2];
static unsigned int setup_words, block_reads, wrplr_reads;

u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long a, unsigned long b) { (void)a; (void)b; assert(false); }
int mt6797_test_write(unsigned int value, void *address)
{
	if (address == window) {
		pending_port = (value >> 9) & 0x1ffffU;
		pending_bytes = (value & BIT(27)) ? (value & 0x1ffU) * 512U : (value & 0x1ffU);
		pending_write = !!(value & BIT(31));
		pending_offset = 0;
		setup_words++;
		if (pending_port == 0x10)
			block_reads++;
		if (pending_port == 0x90)
			wrplr_reads++;
		return 0;
	}
	assert(address == window + 0x1000 && pending_write);
	if (pending_port == 0x0c)
		whcr = value;
	return 0;
}
int mt6797_test_read(void *address, unsigned int *value)
{
	assert(address == window + 0x1000 && !pending_write);
	if (pending_port == 0x0c) {
		*value = whcr;
	} else if (pending_port == 0x10) {
		assert(pending_offset + 4 <= sizeof(block));
		memcpy(value, block + pending_offset, 4);
	} else if (pending_port == 0x50 || pending_port == 0x54) {
		unsigned int q = pending_port == 0x54;

		assert(pending_offset < pending_bytes);
		memcpy(value, queue_stream[q] + queue_offset[q] + pending_offset, 4);
		if (pending_offset + 4 >= pending_bytes)
			queue_offset[q] += pending_bytes;
	} else {
		assert(false);	/* no WRPLR or other register reads in batch mode */
	}
	pending_offset += 4;
	return 0;
}

static void put16(u8 *p, unsigned int v) { p[0] = v; p[1] = v >> 8; }
static unsigned int frame(u8 *stream, unsigned int offset, unsigned int length, unsigned int seed)
{
	unsigned int i;

	put16(stream + offset, length);
	put16(stream + offset + 2, 0x4000 | seed);	/* a data-type word */
	for (i = 4; i < length; i++)
		stream[offset + i] = (u8)(seed + i);
	return offset + ALIGN(length + 4U, 4);
}
/* The block reports n0/n1 frames; at most sixteen lengths each are carried. */
static void announce(unsigned int n0, const unsigned int *l0, unsigned int n1, const unsigned int *l1)
{
	unsigned int i;

	memset(block, 0, sizeof(block));
	put16(block + 36, n0); put16(block + 38, n1);
	for (i = 0; i < n0 && i < 16; i++) put16(block + 40 + 2 * i, l0[i]);
	for (i = 0; i < n1 && i < 16; i++) put16(block + 72 + 2 * i, l1[i]);
}

static struct mt6797_hif *make(void)
{
	static struct mt6797_init_transaction transaction;
	struct mt6797_hif *hif;

	transaction.phase = MT6797_INIT_IDLE;
	window = calloc(1, 0x1004);
	hif = mt6797_hif_alloc(window, 0x1004, &transaction);
	assert(!IS_ERR(hif));
	hif->deadline_ns = 1000000;
	hif->firmware_ready = true;
	hif->capability_complete = true;
	hif->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	hif->rx_batch_forced = true;
	return hif;
}

int main(void)
{
	struct mt6797_hif_rx_result rx;
	struct mt6797_hif_rx_batch_stats stats;
	struct mt6797_hif *hif = make();
	unsigned char out[2560];
	unsigned int l0[2] = {60, 1518}, l1[1] = {100}, l17[17], off, i;

	for (i = 0; i < 17; i++)
		l17[i] = 60;

	/* 1. Two frames on queue 0, one on queue 1: enable, block, two aggregates,
	 * frames served in block order whatever port the caller names.
	 */
	off = frame(queue_stream[0], 0, 60, 1); off = frame(queue_stream[0], off, 1518, 2);
	assert(off == ALIGN(64U, 4) + ALIGN(1522U, 4));
	frame(queue_stream[1], 0, 100, 3);
	announce(2, l0, 1, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
	assert((whcr & BIT(16)) && ((whcr >> 8) & 0x3fU) == 16U && hif->rx_batch_on);
	assert(rx.logical_bytes == 60 && rx.selected_port == 0 && rx.selected_port_valid && out[0] == 60);
	assert(rx.packet_type == (0x4000 | 1) && out[7] == (u8)(1 + 7));
	assert(!mt6797_hif_receive_runtime_packet(hif, 1, 1000000, out, sizeof(out), &rx));
	assert(rx.logical_bytes == 1518 && rx.selected_port == 0 && out[1517] == (u8)(2 + 1517));
	assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
	assert(rx.logical_bytes == 100 && rx.selected_port == 1);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.on && stats.reads == 1 && stats.aggregates == 2 && stats.frames == 3 && stats.max_frames == 3 && !stats.failures);
	assert(block_reads == 1 && wrplr_reads == 0 && !hif->first_error);

	/* 2. No new pass: the empty cache costs no bus work. A new pass with an
	 * empty block reads once and reports empty.
	 */
	assert(mt6797_hif_receive_runtime_packet(hif, 1, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	assert(block_reads == 1);
	announce(0, l0, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	assert(mt6797_hif_receive_runtime_packet(hif, 1, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(block_reads == 2 && stats.reads == 2 && stats.empty == 1 && stats.frames == 3);

	/* 3. A count over sixteen is refused and poisons the context. */
	announce(17, l17, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EPROTO);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.failures == 1 && hif->first_error == -EPROTO);

	/* 4. A header that disagrees with the reported length is refused. */
	mt6797_hif_free(hif);
	free(window);
	hif = make();
	memset(queue_stream, 0, sizeof(queue_stream)); memset(queue_offset, 0, sizeof(queue_offset));
	frame(queue_stream[0], 0, 60, 5); put16(queue_stream[0], 61);
	announce(1, l0, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EPROTO);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.failures == 1 && stats.aggregates == 1);
	mt6797_hif_free(hif);
	free(window);
	printf("receive batching fixtures: PASS\n");
	return 0;
}
