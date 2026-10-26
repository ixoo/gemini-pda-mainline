/* SPDX-License-Identifier: GPL-2.0-only */
/* Host fixture for receive batching (proposal 0268): the WHCR enable and
 * read-back, the 112-byte enhanced status block, one aggregated read per
 * non-empty queue split by the reported lengths, frames served in order
 * across passes, -EAGAIN when the cache is empty, one block read per pass,
 * and the refusals (count over sixteen, header mismatch). PIO only; no
 * hardware. With CONFIG_MT6797_HIF_RX_PEEK (0322) the WHISR register reads
 * as the hardware's read-only done bits (transmit done while a release
 * count is waiting, receive done while a queue reports frames) beside the
 * clear-on-read others, and the pass reads WHISR before the block.
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
static u32 whcr = 0x00000000;		/* the firmware default: count 0 (unlimited), bit 16 clear */
static u8 block[112];
static u8 queue_stream[2][40960];
static unsigned int queue_offset[2];
static unsigned int setup_words, block_reads, whisr_reads, wrplr_reads;
/* The two consumers' shared hardware: WHISR and the sixteen TX queue
 * release counts, each clear-on-read whichever form reads it (the 112-byte
 * block or the WHISR/WTQCR registers).
 */
static u32 hw_whisr;
static unsigned int hw_tq[16];
static u8 image[112];
static bool inject_release_on_whisr_read;
static void put16(u8 *p, unsigned int v) { p[0] = v; p[1] = v >> 8; }
static void release(unsigned int q, unsigned int n) { hw_tq[q] += n; hw_whisr |= BIT(0); }

/* The read-only done bits (0322's model): transmit done while a release
 * count waits, receive done while a queue reports frames. Without the peek
 * the model keeps them in hw_whisr, clear-on-read, as before.
 */
static u32 whisr_level(void)
{
#ifdef CONFIG_MT6797_HIF_RX_PEEK
	unsigned int i, tq = 0;

	for (i = 0; i < 16; i++)
		tq |= hw_tq[i];
	return (tq ? BIT(0) : 0) | (block[36] | block[37] ? BIT(1) : 0) |
	       (block[38] | block[39] ? BIT(2) : 0);
#else
	return 0;
#endif
}

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
		if (pending_port == 0x10 && pending_bytes == 112)
			block_reads++;
		else if (pending_port == 0x10)
			whisr_reads++;
		if (pending_port == 0x90)
			wrplr_reads++;
		return 0;
	}
	assert(address == window + 0x1000 && pending_write);
	assert(pending_port != 0x0c);	/* WHCR is confirmed by reading, never written */
	return 0;
}
int mt6797_test_read(void *address, unsigned int *value)
{
	assert(address == window + 0x1000 && !pending_write);
	if (pending_port == 0x0c) {
		*value = whcr;
	} else if (pending_port == 0x10 && pending_bytes == 112) {
		unsigned int i;

		if (!pending_offset) {	/* the block read consumes the counts */
			memcpy(image, block, sizeof(image));
			put16(image, hw_whisr | whisr_level());
			put16(image + 2, (hw_whisr | whisr_level()) >> 16);
			for (i = 0; i < 16; i++)
				put16(image + 4 + 2 * i, hw_tq[i]);
			hw_whisr = 0;
			memset(hw_tq, 0, sizeof(hw_tq));
		}
		assert(pending_offset + 4 <= sizeof(image));
		memcpy(value, image + pending_offset, 4);
	} else if (pending_port == 0x10) {
		*value = hw_whisr;	/* the register read consumes it too */
		*value |= whisr_level();
		hw_whisr = 0;
		if (inject_release_on_whisr_read) {
			inject_release_on_whisr_read = false;
			release(15, 1); release(14, 1);
		}
	} else if (pending_port >= 0x130 && pending_port <= 0x14c) {
		unsigned int i = (pending_port - 0x130) / 4;

		*value = hw_tq[2 * i] | (hw_tq[2 * i + 1] << 16);
		hw_tq[2 * i] = hw_tq[2 * i + 1] = 0;
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

/* Start a case with empty queue streams at offset zero and an empty block. */
static void fresh(void)
{
	memset(queue_stream, 0, sizeof(queue_stream));
	memset(block, 0, sizeof(block));
	queue_offset[0] = queue_offset[1] = 0;
	hw_whisr = 0;
	memset(hw_tq, 0, sizeof(hw_tq));
}

/* The cold observation is the one status acquisition this model reaches; the
 * merge sits in the acquisition loop every form shares. White box: the
 * admission flags are reset so it can be taken more than once.
 */
static int observe(struct mt6797_hif *hif, struct mt6797_hif_tx_status *st)
{
	int ret;

	hif->normal.phase = MT6797_NORMAL_COLD;
	hif->capability_attempted = false;
	hif->tx_status_boot_attempted = false;
	ret = mt6797_hif_observe_tx_status(hif, 1000000, 1, st);
	hif->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	return ret;
}

static struct mt6797_hif *make(bool forced)
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
	hif->rx_batch_forced = forced;
	return hif;
}

int main(void)
{
	struct mt6797_hif_rx_result rx;
	struct mt6797_hif_rx_batch_stats stats;
	struct mt6797_hif *hif = make(true);
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
	assert(whcr == 0 && hif->rx_batch_on && hif->rx_batch_whcr_after == 0);
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
#ifdef CONFIG_MT6797_HIF_RX_PEEK
	/* The zero WHISR skips the block. */
	assert(block_reads == 1 && stats.reads == 1 && stats.peek_skips == 1 && stats.frames == 3);
#else
	assert(block_reads == 2 && stats.reads == 2 && stats.empty == 1 && stats.frames == 3);
#endif

	/* 3. A count over sixteen is served as sixteen (counted once in failures,
	 * never poison); the seventeenth frame drains on the next pass.
	 */
	fresh();
	off = 0;
	for (i = 0; i < 17; i++)
		off = frame(queue_stream[0], off, 60, 10 + i);
	announce(17, l17, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	for (i = 0; i < 16; i++) {
		assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
		assert(rx.logical_bytes == 60 && rx.packet_type == (0x4000 | (10 + i)));
	}
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.failures == 1 && stats.max_frames == 16 && stats.frames == 19 && !hif->first_error);
	announce(1, l17, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
	assert(rx.logical_bytes == 60 && rx.packet_type == (0x4000 | 26));
	assert(!hif->first_error);

	/* 4. A length outside the frame bounds leaves that queue unread this
	 * pass: no data-port transfer, counted, no poison.
	 */
	fresh();
	{
		unsigned int bad[1] = {2}, before;

		mt6797_hif_rx_batch_stats(hif, &stats);
		before = stats.aggregates;
		announce(1, bad, 0, l1);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(stats.failures == 2 && stats.aggregates == before && !hif->first_error);
	}

	/* 5. A header that disagrees with its reported length drops that
	 * aggregate (its frames are gone); the other queue's frames are still
	 * served in the same pass, and the context is not poisoned.
	 */
	fresh();
	{
		unsigned int lie[2] = {60, 100};

		off = frame(queue_stream[0], 0, 60, 30);
		frame(queue_stream[0], off, 80, 31);	/* the block said 100 */
		frame(queue_stream[1], 0, 100, 32);
		announce(2, lie, 1, l1);
		mt6797_hif_rx_batch_pass(hif);
		assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
		assert(rx.logical_bytes == 100 && rx.selected_port == 1 && rx.packet_type == (0x4000 | 32));
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(stats.failures == 3 && !hif->first_error);
	}

	/* 6. The TX release counts the block carries (WHISR and the sixteen
	 * queue counts, consumed by the read) are merged into the next TX
	 * status acquisition in the WTQCR word layout, then cleared. Fails
	 * without the merge: the counts would be gone with the block read.
	 */
	fresh();
	{
		struct mt6797_hif_tx_status st;
		unsigned int whisr_before = whisr_reads;

		announce(0, l0, 0, l1);
		release(1, 1);			/* TQ1: one AC1 page */
		release(14, 2);			/* TQ14: two FFA pages */
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(stats.credit_blocks == 1 && stats.block_whisr == 0x1 &&
		       stats.pending_wtqcr0 == 0x00010000 && stats.pending_wtqcr7 == 0x00000002);
		assert(!observe(hif, &st));
		/* The register WHISR was consumed by the block read and is not
		 * copied back: the acquisition's own word is zero and the done
		 * bit the counts imply is synthesised beside it.
		 */
#ifdef CONFIG_MT6797_HIF_RX_PEEK
		assert(whisr_reads == whisr_before + 2);	/* the pass's, then the acquisition's */
#else
		assert(whisr_reads == whisr_before + 1 && whisr_reads == 1);
#endif
		assert(st.whisr == 0 && st.synthesized == 0x1 &&
		       st.wtqcr[0] == 0x00010000 && st.wtqcr[7] == 0x00000002 && st.wtqcr[1] == 0);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(!stats.pending_wtqcr0 && !stats.pending_wtqcr7 && !hif->first_error);
	}

	/* 7. Counts arriving between two block reads accumulate, and are not
	 * doubled: the second read finds the registers empty. Fails without
	 * the merge (nothing reaches the acquisition).
	 */
	fresh();
	{
		struct mt6797_hif_tx_status st;

		release(15, 1); release(14, 1);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		release(15, 1); release(14, 1);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(stats.credit_blocks == 3 && stats.pending_wtqcr7 == 0x00020002);
		assert(!observe(hif, &st) && st.wtqcr[7] == 0x00020002 && st.synthesized == 0x1);
		assert(!observe(hif, &st) && st.wtqcr[7] == 0 && st.whisr == 0 && !st.synthesized);
	}

	/* 8. A block that carries no TX counts leaves credits= alone (control:
	 * does not depend on the merge).
	 */
	fresh();
	announce(0, l0, 0, l1);
	mt6797_hif_rx_batch_pass(hif);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.credit_blocks == 3 && !stats.pending_wtqcr7);

	/* 9. Counts that arrive while the credit path is mid-acquisition (after
	 * its WHISR read, before its WTQCR reads) land in the registers and are
	 * added to the block-carried counts in that one acquisition: no split
	 * update, nothing left pending. Fails without the merge (the
	 * block-carried half is lost).
	 */
	fresh();
	{
		struct mt6797_hif_tx_status st;

		release(15, 2); release(14, 2);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		inject_release_on_whisr_read = true;
		assert(!observe(hif, &st) && st.wtqcr[7] == 0x00030003);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(!stats.pending_wtqcr7 && !inject_release_on_whisr_read);
		assert(!observe(hif, &st) && st.wtqcr[7] == 0);
	}

	/* 9b. The block's edge bits are never copied; the abnormal edge (bit 6)
	 * the block carries is recorded with the word and fails the HIF, as
	 * the vendor resets the chip on it from whichever read carried it.
	 */
	fresh();
	hw_whisr = BIT(6) | BIT(1);
	mt6797_hif_rx_batch_pass(hif);
	assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EIO);
	mt6797_hif_rx_batch_stats(hif, &stats);
	assert(stats.block_abnormal == (BIT(6) | BIT(1)) && stats.error == -EIO && hif->first_error == -EIO);
	mt6797_hif_free(hif);
	free(window);

	/* 11. The join replay over the merged block state, at the ledger: the
	 * state-1 record (two pages) credited through the block, the
	 * authentication frame (one page) credited through the registers, the
	 * second EAPOL message (two pages) credited through the block and its
	 * completion carrying no counts; the guard's acquisition passes each
	 * time with the synthesised done bit where the block carried the
	 * counts, and trips only on a genuine abnormal in the register.
	 */
	fresh();
	hif = make(true);
	{
		static unsigned char history[32];
		struct mt6797_hif_tx_status st;
		struct mt6797_normal_release acc;
		struct mt6797_normal_transaction *t = &hif->normal;

		t->phase = MT6797_NORMAL_COLD;
		assert(!mt6797_normal_admit(t, 26, 26, history));
		t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
		hif->tx_status_accounting_baseline = true;
		hif->tx_status_normal_attempted = true;
		/* state-1 record: two pages written, released while the block is the reader */
		t->tc4_free -= 2;
		release(15, 2); release(14, 2);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		assert(!mt6797_hif_reconcile_runtime(hif, 1000000, &st, &acc));
		assert(acc.released_pages == 2 && t->tc4_free == 26 && st.synthesized == 0x1 && st.whisr == 0);
		/* authentication frame: one page, released between block reads, seen by the registers */
		t->tc4_free -= 1;
		release(15, 1); release(14, 1);
		assert(!mt6797_hif_reconcile_runtime(hif, 1000000, &st, &acc));
		assert(acc.released_pages == 1 && t->tc4_free == 26 && !st.synthesized && st.whisr == 0x1);
		/* second EAPOL message: two pages through the block, then a completion with no counts */
		t->tc4_free -= 2;
		release(15, 2); release(14, 2);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		assert(!mt6797_hif_reconcile_runtime(hif, 1000000, &st, &acc));
		assert(acc.released_pages == 2 && t->tc4_free == 26 && st.synthesized == 0x1);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		assert(!mt6797_hif_reconcile_runtime(hif, 1000000, &st, &acc));
		assert(!acc.released_pages && t->tc4_free == 26 && !st.synthesized && !st.whisr && !hif->first_error);
		/* a genuine abnormal in the register trips the guard's acquisition */
		hw_whisr = BIT(6);
		assert(mt6797_hif_reconcile_runtime(hif, 1000000, &st, &acc) == -EIO && hif->first_error == -EIO);
	}
	mt6797_hif_free(hif);
	free(window);

	/* 10. Mode off (the option disabled, nothing forced): the credit path
	 * polls the registers as before and consumes them; no block is read
	 * (control: the unchanged behaviour).
	 */
	fresh();
	hif = make(false);
	{
		struct mt6797_hif_tx_status st;
		unsigned int before = block_reads;

		release(15, 2); release(14, 2);
		assert(!observe(hif, &st) && st.wtqcr[7] == 0x00020002 && st.whisr == 0x1);
		assert(!observe(hif, &st) && st.wtqcr[7] == 0);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(block_reads == before && !stats.on && !stats.credit_blocks && !hif->first_error);
	}
	mt6797_hif_free(hif);
	free(window);
#ifdef CONFIG_MT6797_HIF_RX_PEEK
	/* 12. The WHISR peek (0322). */
	fresh();
	hif = make(true);
	{
		unsigned int blocks = block_reads, skips;

		/* nothing waiting: no block read, counted as skipped */
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(block_reads == blocks && stats.peeks == 1 && stats.peek_skips == 1);
		skips = stats.peek_skips;
		/* a frame waiting on queue 1: receive done is set, the block is read */
		frame(queue_stream[1], 0, 100, 40);
		announce(0, l0, 1, l1);
		mt6797_hif_rx_batch_pass(hif);
		assert(!mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx));
		assert(rx.logical_bytes == 100 && rx.selected_port == 1 && block_reads == blocks + 1);
		/* a release count alone: transmit done is set, the block is read
		 * and the count merged
		 */
		announce(0, l0, 0, l1);
		release(14, 1);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(block_reads == blocks + 2 && stats.pending_wtqcr7 == 0x1 && stats.peek_skips == skips);
		/* a clear-on-read bit alone still reads the block */
		hw_whisr = BIT(8);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EAGAIN);
		assert(block_reads == blocks + 3 && !hif->first_error);
		/* the firmware assert the peek consumes fails the HIF without a block read */
		hw_whisr = BIT(31);
		mt6797_hif_rx_batch_pass(hif);
		assert(mt6797_hif_receive_runtime_packet(hif, 0, 1000000, out, sizeof(out), &rx) == -EIO);
		mt6797_hif_rx_batch_stats(hif, &stats);
		assert(block_reads == blocks + 3 && stats.block_abnormal == BIT(31) && hif->first_error == -EIO);
	}
	mt6797_hif_free(hif);
	free(window);
#endif
	printf("hif-rx-batch-test: PASS (clamp, bad length, dropped aggregate, credit merge, interleavings, block abnormal, join replay, mode off)\n");
	return 0;
}
