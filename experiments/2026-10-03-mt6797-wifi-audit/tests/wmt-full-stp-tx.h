/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_FULL_STP_TX_H
#define GEMINI_WMT_FULL_STP_TX_H
#include "wmt-full-stp.h"

#define WMT_FULL_TX_OBSERVATIONS 256U

/* Caller owns immutable encoded bytes throughout this span. Serial access;
 * no MMIO, retries, timers or IRQ masking are performed by this helper.
 */
struct wmt_full_tx {
	const unsigned char *frame;
	unsigned int length, written, offered, observations;
	int retired;
};

static inline int wmt_full_tx_init(struct wmt_full_tx *tx,
		const unsigned char *frame, unsigned int length)
{
	struct wmt_full_frame decoded;
	struct wmt_full_tx initial = { .frame = frame, .length = length };

	if (!tx || wmt_full_decode(frame, length, &decoded) < 0)
		return -1;
	*tx = initial;
	return 0;
}

static inline int wmt_full_tx_done(const struct wmt_full_tx *tx)
{
	return tx && !tx->retired && !tx->offered && tx->written == tx->length;
}

/* Fresh, normal-bank LSR observation for exactly one batch. Caller checks its
 * deadline under the ownership lock and supplies the corresponding expiry.
 * Returns offered bytes, zero for no room/completion, or terminal -1.
 */
static inline int wmt_full_tx_batch(struct wmt_full_tx *tx, unsigned int lsr,
		int expired, const unsigned char **bytes)
{
	unsigned int room, remaining;

	if (!tx || !bytes)
		return -1;
	if (tx->retired || tx->offered || expired)
		goto retire;
	if (wmt_full_tx_done(tx))
		return 0;
	if (tx->observations == WMT_FULL_TX_OBSERVATIONS)
		goto retire;
	tx->observations++;
	room = lsr & 0x40 ? 16 : lsr & 0x20 ? 8 : 0;
	if (!room)
		return 0;
	remaining = tx->length - tx->written;
	tx->offered = remaining < room ? remaining : room;
	*bytes = tx->frame + tx->written;
	return tx->offered;
retire:
	tx->retired = 1;
	return -1;
}

/* Report actual THR writes once. Partial or late completion preserves its byte
 * count but retires without claiming command submission or replaying a suffix.
 */
static inline int wmt_full_tx_commit(struct wmt_full_tx *tx,
		unsigned int actual, int expired)
{
	if (!tx)
		return -1;
	if (tx->retired || !tx->offered || actual > tx->offered) {
		tx->retired = 1;
		return -1;
	}
	tx->written += actual;
	if (actual != tx->offered || expired) {
		tx->retired = 1;
		return -1;
	}
	tx->offered = 0;
	return 0;
}
#endif
