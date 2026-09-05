/* SPDX-License-Identifier: GPL-2.0-only */
/* Original bounded normal-command helpers; see NORMAL_COMMAND.md. */
#ifndef GEMINI_NORMAL_COMMAND_H
#define GEMINI_NORMAL_COMMAND_H
#include "hif_command.h"

#define MT6797_NORMAL_CAP_BYTES 124U
#define MT6797_NORMAL_NVRAM_BYTES 520U

enum mt6797_normal_kind { MT6797_NORMAL_CAPABILITY, MT6797_NORMAL_NVRAM };
enum mt6797_normal_phase {
	MT6797_NORMAL_COLD, MT6797_NORMAL_IDLE, MT6797_NORMAL_CAP_TX,
	MT6797_NORMAL_CAP_WAIT, MT6797_NORMAL_CAP_RECEIVED,
	MT6797_NORMAL_NVRAM_TX, MT6797_NORMAL_NVRAM_SUBMITTED,
	MT6797_NORMAL_FAILED,
};

struct mt6797_normal_transaction {
	enum mt6797_normal_phase phase;
	unsigned int tc4_limit, tc4_free, expected_sequence;
	/* Shared adapter-session history, including INIT. Never cleared here. */
	unsigned char *used_sequences;
};

/* No MAC, date string or raw event is copied into this result. */
struct mt6797_normal_capability {
	unsigned int product, firmware_own, firmware_peer;
	unsigned int hw_5g_disabled, eeprom_used, rf_cal_fail, bb_cal_fail;
};

static inline unsigned int mt6797_normal_le16(const unsigned char *p)
{
	return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}

static inline int mt6797_normal_abort(struct mt6797_normal_transaction *t)
{
	if (!t)
		return -EINVAL;
	t->phase = MT6797_NORMAL_FAILED;
	return -EIO;
}

/* Only the actual post-START resource owner may supply these normal-TC4 facts.
 * No default quota, hardware reset, INIT-credit reuse or refill is provided.
 * history must cover 32 bytes and outlive this serialized bounded transaction.
 */
static inline int
mt6797_normal_admit(struct mt6797_normal_transaction *t, unsigned int limit,
	unsigned int available, unsigned char *history)
{
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_NORMAL_COLD)
		return mt6797_normal_abort(t);
	if (!history || !limit || limit > 0xffffU || available > limit)
		return -EINVAL;
	t->tc4_limit = limit;
	t->tc4_free = available;
	t->used_sequences = history;
	t->phase = MT6797_NORMAL_IDLE;
	return 0;
}

/* Distinct immutable payload, output and state storage. No output bytes are
 * changed on refusal. CAP's unused request tail and all HIF padding are zero.
 * Returned command describes WTDR1 PIO; no I/O occurs in this helper.
 */
static inline int
mt6797_normal_prepare(struct mt6797_normal_transaction *t,
	enum mt6797_normal_kind kind, unsigned int sequence,
	const unsigned char *payload, size_t payload_bytes,
	unsigned char *output, size_t capacity, struct mt6797_hif_command *command)
{
	struct mt6797_hif_command encoded;
	size_t bytes, i;
	unsigned int pages;
	int error;

	if (command)
		*command = (struct mt6797_hif_command){0};
	if (!t || !output || !command)
		return -EINVAL;
	if (!t->used_sequences || !t->tc4_limit || t->tc4_limit > 0xffffU ||
	    t->tc4_free > t->tc4_limit)
		return mt6797_normal_abort(t);
	if (kind == MT6797_NORMAL_CAPABILITY) {
		if (t->phase != MT6797_NORMAL_IDLE)
			return mt6797_normal_abort(t);
		if (payload || payload_bytes)
			return -EINVAL;
		bytes = MT6797_NORMAL_CAP_BYTES;
	} else if (kind == MT6797_NORMAL_NVRAM) {
		if (t->phase != MT6797_NORMAL_CAP_RECEIVED)
			return mt6797_normal_abort(t);
		if (!payload || payload_bytes != 512)
			return -EINVAL;
		bytes = MT6797_NORMAL_NVRAM_BYTES;
	} else {
		return -EINVAL;
	}
	if (sequence > 255)
		return -EINVAL;
	if (t->used_sequences[sequence / 8] & (1U << (sequence % 8)))
		return mt6797_normal_abort(t);
	error = mt6797_hif_encode_command(0x34, MT6797_HIF_WRITE,
		MT6797_HIF_PIO_ONLY, bytes, capacity, &encoded);
	if (error)
		return error;
	/* Source normal GENERAL/NETWORK IOCTL uses ceil(logical length/128),
	 * with no additional TX descriptor and no charge for HIF block padding.
	 */
	pages = (unsigned int)((bytes + 127) / 128);
	if (t->tc4_free < pages)
		return -ENOSPC;
	for (i = 0; i < encoded.transfer_bytes; i++)
		output[i] = 0;
	output[0] = (unsigned char)bytes;
	output[1] = (unsigned char)(bytes >> 8);
	output[3] = 0x80;
	output[4] = kind == MT6797_NORMAL_CAPABILITY ? 0x80 : 0x48;
	output[5] = 0xa0;
	output[6] = kind == MT6797_NORMAL_NVRAM ? 1 : 0;
	output[7] = (unsigned char)sequence;
	for (i = 0; i < payload_bytes; i++)
		output[8 + i] = payload[i];
	t->tc4_free -= pages;
	t->used_sequences[sequence / 8] |= (unsigned char)(1U << (sequence % 8));
	t->expected_sequence = sequence;
	t->phase = kind == MT6797_NORMAL_CAPABILITY ? MT6797_NORMAL_CAP_TX :
		MT6797_NORMAL_NVRAM_TX;
	*command = encoded;
	return 0;
}

/* Feedback from the actual ordered transport. Failure may have side effects. */
static inline int
mt6797_normal_submitted(struct mt6797_normal_transaction *t, int transport_error)
{
	if (!t)
		return -EINVAL;
	if (transport_error)
		return mt6797_normal_abort(t);
	if (t->phase == MT6797_NORMAL_CAP_TX)
		t->phase = MT6797_NORMAL_CAP_WAIT;
	else if (t->phase == MT6797_NORMAL_NVRAM_TX)
		t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	else
		return mt6797_normal_abort(t);
	return 0;
}

/* Caller supplies the logical port-1 length obtained via proper WRPLR access.
 * Extra four RX bytes are staging only. Zero means pending, never a reply.
 */
static inline int
mt6797_normal_reply_span(struct mt6797_normal_transaction *t,
	unsigned int reported_length, size_t capacity, struct mt6797_hif_command *span)
{
	int error;

	if (span)
		*span = (struct mt6797_hif_command){0};
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_NORMAL_CAP_WAIT || !span)
		return mt6797_normal_abort(t);
	if (!reported_length)
		return -EAGAIN;
	if (reported_length != MT6797_NORMAL_CAP_BYTES)
		return mt6797_normal_abort(t);
	error = mt6797_hif_encode_command(0x54, MT6797_HIF_READ,
		MT6797_HIF_PIO_ONLY, MT6797_NORMAL_CAP_BYTES + 4, capacity, span);
	if (error)
		mt6797_normal_abort(t);
	return error;
}

/* Exact logical event only; no response-status byte is defined for capability.
 * RF/BB failure flags are observations, not packet-validation failures or proof
 * of calibration. Reserved bytes/MAC/date remain unexported and uninterpreted.
 */
static inline int
mt6797_normal_accept_capability(struct mt6797_normal_transaction *t,
	const unsigned char *packet, size_t bytes, struct mt6797_normal_capability *result)
{
	if (result)
		*result = (struct mt6797_normal_capability){0};
	if (!t)
		return -EINVAL;
	if (t->phase != MT6797_NORMAL_CAP_WAIT || !packet || !result ||
	    bytes != MT6797_NORMAL_CAP_BYTES ||
	    mt6797_normal_le16(packet) != MT6797_NORMAL_CAP_BYTES ||
	    mt6797_normal_le16(packet + 2) != 0xe000 || packet[4] != 1 ||
	    t->expected_sequence > 255 || packet[5] != t->expected_sequence)
		return mt6797_normal_abort(t);
	result->product = mt6797_normal_le16(packet + 8);
	result->firmware_own = mt6797_normal_le16(packet + 10);
	result->firmware_peer = mt6797_normal_le16(packet + 12);
	result->hw_5g_disabled = packet[14];
	result->eeprom_used = packet[15];
	result->rf_cal_fail = packet[26];
	result->bb_cal_fail = packet[27];
	t->phase = MT6797_NORMAL_CAP_RECEIVED;
	return 0;
}
#endif
