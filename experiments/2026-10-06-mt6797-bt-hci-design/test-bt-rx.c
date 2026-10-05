/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * The driver's IRQ-side receive callback, compiled from btmt6797.c, feeding
 * the real engine: a full ring refuses, which must stop the link.
 */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "mt6797-stp-engine.h"

/* Minimal stand-ins for the kernel pieces the callback touches. */
typedef unsigned char u8;
typedef struct { int unused; } spinlock_t;
static void spin_lock(spinlock_t *l) { (void)l; }
static void spin_unlock(spinlock_t *l) { (void)l; }
static unsigned int scheduled;
struct work_struct { int unused; };
static void schedule_work(struct work_struct *w) { (void)w; scheduled++; }
#define BTMT6797_RX_SLOTS 16U
#define BTMT6797_RX_MAX 2048U

struct btmt6797_rx_slot {
	unsigned int length;
	u8 data[BTMT6797_RX_MAX];
};

struct btmt6797 {
	spinlock_t rx_lock;
	struct btmt6797_rx_slot rx[BTMT6797_RX_SLOTS];
	unsigned int rx_head, rx_count;
	struct work_struct rx_work;
};

#include "btmt6797-rx.inc"

static int rx_adapter(void *context, const unsigned char *payload, unsigned int length)
{
	return btmt6797_rx(context, payload, length);
}

int main(void)
{
	static struct stp_engine e;
	static struct btmt6797 bt;
	static const unsigned char ev[] = { 0x04, 0x0e, 0x04, 0x01, 0x03, 0x0c, 0x00 };
	unsigned char wire[64];
	unsigned int i, n;
	int bytes, ret = 0;

	stp_engine_init(&e, 0);
	assert(stp_engine_bind(&e, STP_FULL_TASK_BT, rx_adapter, &bt) == 0);
	/* 16 frames fill the ring; the engine ACKs them as consumed by the client. */
	for (n = 0; n <= BTMT6797_RX_SLOTS; n++) {
		bytes = stp_full_encode(wire, sizeof(wire), ev, sizeof(ev), STP_FULL_TASK_BT,
					n & 7, 7);
		for (i = 0; i < (unsigned int)bytes && !ret; i++)
			ret = stp_engine_rx(&e, wire[i], n);
		if (ret)
			break;
		/* Keep the window open: pretend each ACK went out. */
		while (stp_engine_tx_pending(&e))
			assert(stp_engine_tx_done(&e, e.frame_length - e.frame_written, n) == 0);
	}
	assert(n == BTMT6797_RX_SLOTS && ret == STP_ENGINE_ENOSPC);
	assert(bt.rx_count == BTMT6797_RX_SLOTS && scheduled == BTMT6797_RX_SLOTS);
	assert(e.failed == STP_ENGINE_ENOSPC && e.rx_frames == BTMT6797_RX_SLOTS);
	/* Oversize and empty payloads are refused before touching the ring. */
	assert(btmt6797_rx(&bt, ev, 0) == -EINVAL);
	puts("bt rx: full ring refuses and stops the link; ACKed frames all kept");
	return 0;
}
