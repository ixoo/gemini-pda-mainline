/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_DEFAULT_QUERY_H
#define GEMINI_WMT_DEFAULT_QUERY_H

/* Fixed mandatory-STP WMT query; no register or transport operations. */
static const unsigned char wmt_default_query[11] = {
	0x80, 0x40, 0x05, 0x00, 0x01, 0x04, 0x01, 0x00, 0x04, 0x00, 0x00
};

struct wmt_default_reply {
	unsigned int received;
	int failed;
};

/* Feed exactly one consumed byte. 1 means complete, 0 incomplete, -1 failed.
 * Caller owns deadline, read budget and single-use transport lifetime.
 */
static inline int wmt_default_reply_byte(struct wmt_default_reply *reply,
					 unsigned char byte)
{
	static const unsigned char suffix[15] = {
		0x40, 0x0a, 0x00, 0x02, 0x04, 0x06, 0x00, 0x00,
		0x04, 0x11, 0x00, 0x00, 0x00, 0x00, 0x00
	};

	if (!reply || reply->failed || reply->received >= 16)
		return -1;
	if (reply->received ? byte != suffix[reply->received - 1] :
	    !(byte & 0x80)) {
		reply->failed = 1;
		return -1;
	}
	reply->received++;
	return reply->received == 16;
}

#endif
