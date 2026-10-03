/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_STP_OPTIONS_H
#define GEMINI_WMT_STP_OPTIONS_H

/* Fixed mandatory-mode set request. The selected mandatory TX path does not
 * increment its debug sequence; full-mode enable separately reseeds state.
 * No register, mode, clock, IRQ or transport operations are performed here.
 */
static const unsigned char wmt_stp_set_options[15] = {
	0x80, 0x40, 0x09, 0x00, 0x01, 0x04, 0x05, 0x00,
	0x03, 0xdf, 0x0e, 0x68, 0x01, 0x00, 0x00
};

/* Payloads for the existing full-STP codec/owner after the checked set event,
 * admitted full-mode boundary, sequence initialization and switch delay.
 */
static const unsigned char wmt_stp_full_query[5] = {
	0x01, 0x04, 0x01, 0x00, 0x04
};

static const unsigned char wmt_stp_full_options[10] = {
	0x02, 0x04, 0x06, 0x00, 0x00, 0x04, 0xdf, 0x0e, 0x68, 0x01
};

struct wmt_stp_set_reply {
	unsigned int received;
	int failed;
};

/* One consumed byte: 1 complete, 0 incomplete, -1 failed. Caller enforces
 * finite byte/time/IRQ budgets and retires on refusal or extra input.
 */
static inline int wmt_stp_set_reply_byte(struct wmt_stp_set_reply *reply,
					 unsigned char byte)
{
	static const unsigned char suffix[11] = {
		0x40, 0x06, 0x00, 0x02, 0x04, 0x02, 0x00, 0x00,
		0x03, 0x00, 0x00
	};

	if (!reply || reply->failed)
		return -1;
	if (reply->received >= 12) {
		reply->failed = 1;
		return -1;
	}
	if (reply->received ? byte != suffix[reply->received - 1] :
	    !(byte & 0x80)) {
		reply->failed = 1;
		return -1;
	}
	reply->received++;
	return reply->received == 12;
}

#endif
