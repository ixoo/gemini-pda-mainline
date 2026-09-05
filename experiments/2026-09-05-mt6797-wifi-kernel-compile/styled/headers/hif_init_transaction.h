/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_HIF_INIT_TRANSACTION_H
#define GEMINI_HIF_INIT_TRANSACTION_H
#include "hif_init_bounds.h"

static inline unsigned int mt6797_init_le16(const unsigned char *p)
{
	return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}

static inline unsigned int mt6797_init_le32(const unsigned char *p)
{
	return mt6797_init_le16(p) | (mt6797_init_le16(p + 2) << 16);
}

/* Exact logical bytes only, not the 32-byte staging span. Nonzero status is
 * well-formed firmware rejection (-EIO); diagnostics stay uninterpreted.
 */
static inline int mt6797_init_validate_result(const unsigned char *packet,
					      size_t bytes,
					      unsigned int expected_sequence,
					      unsigned int *status)
{
	if (!status)
		return -EINVAL;
	*status = 0;
	if (!packet || expected_sequence > 255U)
		return -EINVAL;
	if (bytes != 28 || mt6797_init_le16(packet) != 28 ||
	    mt6797_init_le16(packet + 2) != 0xe000 || packet[4] != 1 ||
	    packet[5] != expected_sequence)
		return -EPROTO;
	*status = packet[8];
	return *status ? -EIO : 0;
}

static inline int mt6797_init_validate_config(const unsigned char *p,
					      size_t bytes,
					      unsigned int sequence)
{
	unsigned int address, length, mode;

	if (!p || sequence > 255U)
		return -EINVAL;
	if (bytes != 20 || mt6797_init_le16(p) != 20 ||
	    mt6797_init_le16(p + 2) != 0x8000 || p[4] != 1 || p[5] != 0xa0 ||
	    p[6] || p[7] != sequence)
		return -EPROTO;
	address = mt6797_init_le32(p + 8);
	length = mt6797_init_le32(p + 12);
	mode = mt6797_init_le32(p + 16);
	/* Inclusive last address allows a range ending exactly at 2^32. */
	if (!length || length - 1U > 0xffffffffU - address ||
	    (mode & ~0x8000000fU) || !(mode & 0x80000000U) ||
	    ((mode & 6U) && !(mode & 1U)))
		return -EPROTO;
	return 0;
}

static inline int mt6797_init_validate_start(const unsigned char *p,
					     size_t bytes,
					     unsigned int sequence)
{
	if (!p || sequence > 255U)
		return -EINVAL;
	if (bytes != 16 || mt6797_init_le16(p) != 16 ||
	    mt6797_init_le16(p + 2) != 0x8000 || p[4] != 2 || p[5] != 0xa0 ||
	    p[6] || p[7] != sequence || mt6797_init_le32(p + 8) > 1U)
		return -EPROTO;
	/* The address is not a permission or validity check. */
	return 0;
}

enum mt6797_init_phase {
	MT6797_INIT_IDLE,
	MT6797_INIT_DISPATCH,
	MT6797_INIT_REPLY,
	MT6797_INIT_POISONED,
	MT6797_START_DISPATCH,
	MT6797_START_READY,
	MT6797_INIT_PAYLOAD
};

/* Zero-initialize once, set each pool only from proven fresh INIT admission.
 * Caller serializes all calls and owns a finite deadline/owner generation.
 * No reset/refund entry point. Do not reconstruct this after failure.
 */
struct mt6797_init_transaction {
	enum mt6797_init_phase phase;
	unsigned int free_pages, start_free_pages, expected_sequence;
	/* free_pages is CONFIG TC4; start_free_pages is START TC0. */
	unsigned char used_sequences[32];
};

static inline int mt6797_init_abort(struct mt6797_init_transaction *t)
{
	if (!t)
		return -EINVAL;
	t->phase = MT6797_INIT_POISONED;
	return -EIO;
}

static inline int mt6797_init_begin(struct mt6797_init_transaction *t,
				    const unsigned char *command, size_t bytes,
				    unsigned int expected_sequence)
{
	int error;

	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_IDLE || t->free_pages > 104U)
		return mt6797_init_abort(t);
	error = mt6797_init_validate_config(command, bytes, expected_sequence);
	if (error)
		return error;
	if (t->used_sequences[expected_sequence / 8] &
	    (1U << (expected_sequence % 8)))
		return mt6797_init_abort(t);
	error = mt6797_init_debit(bytes, &t->free_pages);
	if (error)
		return error;
	t->used_sequences[expected_sequence / 8] |=
		(unsigned char)(1U << (expected_sequence % 8));
	t->expected_sequence = expected_sequence;
	t->phase = MT6797_INIT_DISPATCH;
	return 0;
}

/* Feed the finite PIO primitive's return outcome. Success means submitted,
 * not acknowledged. Any uncertain/failing outcome permanently poisons state.
 */
static inline int mt6797_init_submitted(struct mt6797_init_transaction *t,
					int pio_error)
{
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_DISPATCH || pio_error)
		return mt6797_init_abort(t);
	t->phase = MT6797_INIT_REPLY;
	return 0;
}

static inline int mt6797_start_begin(struct mt6797_init_transaction *t,
				     const unsigned char *command, size_t bytes,
				     unsigned int expected_sequence)
{
	int error;

	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_IDLE || t->start_free_pages > 104U)
		return mt6797_init_abort(t);
	error = mt6797_init_validate_start(command, bytes, expected_sequence);
	if (error)
		return error;
	if (t->used_sequences[expected_sequence / 8] &
	    (1U << (expected_sequence % 8)))
		return mt6797_init_abort(t);
	error = mt6797_init_debit(bytes, &t->start_free_pages);
	if (error)
		return error;
	t->used_sequences[expected_sequence / 8] |=
		(unsigned char)(1U << (expected_sequence % 8));
	t->expected_sequence = expected_sequence;
	t->phase = MT6797_START_DISPATCH;
	return 0;
}

static inline int mt6797_start_submitted(struct mt6797_init_transaction *t,
					 int pio_error)
{
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_START_DISPATCH || pio_error)
		return mt6797_init_abort(t);
	t->phase = MT6797_START_READY;
	return 0;
}

/* Caller supplies an attributable WCIR observation after successful START TX.
 * This is a level test, not proof that START caused a transition. Caller owns
 * deadline and session validity; abort on timeout/ownership loss/read failure.
 */
static inline int mt6797_start_observe_ready(struct mt6797_init_transaction *t,
					     unsigned int wcir)
{
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_START_READY)
		return mt6797_init_abort(t);
	if (!(wcir & (1U << 21)))
		return -EAGAIN;
	t->phase = MT6797_INIT_IDLE;
	return 0;
}

/* Validate port-0 length before dispatching the RX primitive. */
static inline int mt6797_init_prepare_reply(struct mt6797_init_transaction *t,
					    unsigned int length,
					    size_t capacity,
					    struct mt6797_hif_command *span)
{
	int error;

	if (span)
		*span = (struct mt6797_hif_command){0};
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_REPLY)
		return mt6797_init_abort(t);
	error = mt6797_init_result_span(length, capacity, span);
	if (error && error != -EAGAIN)
		mt6797_init_abort(t);
	return error;
}

static inline int mt6797_init_accept_reply(struct mt6797_init_transaction *t,
					   const unsigned char *packet,
					   size_t logical_bytes,
					   unsigned int *firmware_status)
{
	int error;

	if (firmware_status)
		*firmware_status = 0;
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_INIT_REPLY)
		return mt6797_init_abort(t);
	error = mt6797_init_validate_result(packet, logical_bytes,
					    t->expected_sequence, firmware_status);
	if (error) {
		mt6797_init_abort(t);
		return error;
	}
	t->phase = MT6797_INIT_IDLE;
	return 0;
}

#endif
