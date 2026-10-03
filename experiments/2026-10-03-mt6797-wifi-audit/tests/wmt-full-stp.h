/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_FULL_STP_H
#define GEMINI_WMT_FULL_STP_H

/* Selected WMT command limit: five-byte patch header plus 1000-byte body. */
#define WMT_FULL_MAX_PAYLOAD 1005U
#define WMT_FULL_MAX_FRAME (WMT_FULL_MAX_PAYLOAD + 6U)

struct wmt_full_frame {
	unsigned int sequence;
	unsigned int acknowledgement;
	unsigned int length;
	const unsigned char *payload;
};

/* CRC-16 polynomial 0x8005, reflected, initial value zero; payload only. */
static inline unsigned int wmt_full_crc(const unsigned char *data,
					 unsigned int length)
{
	unsigned int crc = 0;
	unsigned int i, bit;

	for (i = 0; i < length; i++) {
		crc ^= data[i];
		for (bit = 0; bit < 8; bit++)
			crc = (crc >> 1) ^ ((crc & 1) ? 0xa001U : 0);
	}
	return crc;
}

/* Caller supplies disjoint buffers and owns FIFO progress and transport state.
 * Returns frame bytes or -1 before modifying output on invalid arguments.
 */
static inline int wmt_full_encode(unsigned char *out, unsigned int capacity,
				  const unsigned char *payload, unsigned int length,
				  unsigned int sequence, unsigned int acknowledgement)
{
	unsigned int crc, i;

	if (!out || !payload || !length || length > WMT_FULL_MAX_PAYLOAD ||
	    sequence > 7 || acknowledgement > 7 || capacity < length + 6)
		return -1;
	crc = wmt_full_crc(payload, length);
	out[0] = 0x80 | (sequence << 3) | acknowledgement;
	out[1] = 0x40 | (length >> 8);
	out[2] = length & 0xff;
	out[3] = (out[0] + out[1] + out[2]) & 0xff;
	for (i = 0; i < length; i++)
		out[i + 4] = payload[i];
	out[length + 4] = crc & 0xff;
	out[length + 5] = crc >> 8;
	return length + 6;
}

static inline int wmt_full_ack(unsigned char *out, unsigned int capacity,
				unsigned int acknowledgement)
{
	if (!out || capacity < 4 || acknowledgement > 7)
		return -1;
	out[0] = 0x80 | acknowledgement;
	out[1] = 0;
	out[2] = 0;
	out[3] = out[0];
	return 4;
}

/* One complete frame; no scan/resynchronization or state advancement.
 * Returns 0 for ACK, 1 for WMT data, -1 without modifying result on failure.
 * Result aliases input: caller retains it and validates sequence/ack and WMT
 * event contents before accepting an exchange or advancing an epoch.
 */
static inline int wmt_full_decode(const unsigned char *frame, unsigned int bytes,
				  struct wmt_full_frame *result)
{
	unsigned int length, crc;

	if (!frame || !result || bytes < 4 || (frame[0] & 0xc0) != 0x80 ||
	    (frame[1] & 0x80) ||
	    ((frame[0] + frame[1] + frame[2]) & 0xff) != frame[3])
		return -1;
	length = ((frame[1] & 0x0f) << 8) | frame[2];
	if (!length) {
		if (frame[1] || bytes != 4)
			return -1;
	} else {
		if ((frame[1] & 0x70) != 0x40 || length > WMT_FULL_MAX_PAYLOAD ||
		    bytes != length + 6)
			return -1;
		crc = frame[length + 4] | (frame[length + 5] << 8);
		if (crc != wmt_full_crc(frame + 4, length))
			return -1;
	}
	result->sequence = (frame[0] >> 3) & 7;
	result->acknowledgement = frame[0] & 7;
	result->length = length;
	result->payload = length ? frame + 4 : 0;
	return length ? 1 : 0;
}

#endif
