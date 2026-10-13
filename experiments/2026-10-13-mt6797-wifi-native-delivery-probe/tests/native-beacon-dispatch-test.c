/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdlib.h>
#include <stdarg.h>
#define mt6797_data_rx_native_gate actual_data_gate
#define main layout_main
#include "native-beacon-test.c"
#undef main
#undef mt6797_data_rx_native_gate

#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#define NL80211_BAND_5GHZ 1U
#define MT6797_JOIN_BMC_WLAN_INDEX 2U
#define IS_ENABLED(x) 1
#include "native-diag.h"
typedef unsigned char u8;
typedef unsigned long long u64;
#define NSEC_PER_MSEC 1000000ULL
static u64 ktime_get_ns(void) { return 1000000000ULL; }

struct ieee80211_rx_status { unsigned int flag, band, freq; int signal; };
struct sk_buff { unsigned char data[4096]; size_t len; struct ieee80211_rx_status status; };
struct sk_buff_head { struct sk_buff *skb; unsigned int count; };
struct wiphy_stub { unsigned char perm_addr[6]; };
struct hw_stub { struct wiphy_stub *wiphy; };
struct mt6797_mac {
	struct hw_stub *hw;
	u8 join_packet[512], join_ap[6];
	bool native_diag_engaged, native_diag_sample_done, join_data_ended;
	bool join_assoc_received, join_cleanup_done, join_deauth_done;
	unsigned int join_assoc_status, join_key_group;
	unsigned int native_diag_state, native_diag_total, native_diag_native, native_diag_bytes;
	unsigned int native_diag_retire_reads, native_diag_retire_bytes;
	u64 native_diag_started;
	bool native_diag_rxd_sampled, native_diag_rx_reported;
	struct { unsigned int type[8], gate[MT6797_NATIVE_RX_GATES], window_blocked, beacons; } native_diag_rx[4];
	unsigned int join_beacons_delivered, join_keyed_beacons;
};
struct mt6797_hif_rx_result { size_t logical_bytes; unsigned int packet_type; };
static unsigned int data_calls, samples;
static unsigned int report_lines;
static char report[8][1024];
static bool fail_alloc;
#define wiphy_dev(w) (w)
#define IEEE80211_SKB_RXCB(s) (&(s)->status)
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args;
	(void)dev;
	if (strstr(format, "native RX descriptor:")) samples++;
	if (!strstr(format, "native RX classes:") && !strstr(format, "native RX gates:"))
		return;
	assert(report_lines < 8);
	va_start(args, format);
	assert(vsnprintf(report[report_lines++], sizeof(report[0]), format, args) > 0);
	va_end(args);
}
static struct sk_buff *dev_alloc_skb(size_t n)
{
	assert(n <= 4096);
	return fail_alloc ? NULL : calloc(1, sizeof(struct sk_buff));
}
static void skb_put_data(struct sk_buff *s, const void *p, size_t n)
{
	assert(n <= sizeof(s->data)); memcpy(s->data, p, n); s->len = n;
}
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *s)
{
	assert(!q->skb); q->skb = s; q->count++;
}
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a, b, 6); }
static enum mt6797_native_rx_gate
mt6797_data_rx_native_gate(const u8 *p, size_t n, unsigned char channel,
			  const u8 *own_addr, const u8 *ap_addr, size_t *off, size_t *len)
{
	data_calls++;
	return actual_data_gate(p, n, channel, own_addr, ap_addr, off, len);
}
#include "beacon-dispatch.h"

static int one(struct mt6797_mac *m, size_t n, size_t off, bool delivered)
{
	struct mt6797_hif_rx_result rx = {n, mt6797_join_le16(m->join_packet + 2)};
	struct sk_buff_head q = {0};
	unsigned char saved[512];
	unsigned int before = m->join_beacons_delivered;
	unsigned int native_before = m->native_diag_rx[1].beacons;
	int ret;

	memcpy(saved, m->join_packet, sizeof(saved));
	ret = dispatch(m, &rx, &q);
	assert(q.count == (unsigned int)delivered);
	assert(m->join_beacons_delivered == before + delivered);
	assert(m->native_diag_rx[1].beacons == native_before +
	       (delivered && (rx.packet_type >> 13) == 2));
	assert(!memcmp(saved, m->join_packet, sizeof(saved)));
	if (delivered) {
		assert(q.skb->len == n - off);
		assert(!memcmp(q.skb->data, saved + off, n - off));
		assert(q.skb->status.flag == 0 && q.skb->status.band == NL80211_BAND_5GHZ);
		assert(q.skb->status.freq == 5200 && q.skb->status.signal == -55);
	}
	free(q.skb);
	return ret;
}

int main(void)
{
	struct wiphy_stub wiphy = {0};
	struct hw_stub hw = {&wiphy};
	struct mt6797_mac m;
	size_t n, off;

	memcpy(wiphy.perm_addr, own, 6);
#define RESET() do { \
	memset(&m, 0, sizeof(m)); m.hw = &hw; memcpy(m.join_ap, ap, 6); \
	m.native_diag_engaged = true; m.native_diag_state = MT6797_ND_ACTIVE; \
	m.native_diag_started = ktime_get_ns(); m.join_assoc_received = true; \
	data_calls = samples = 0; fail_alloc = false; \
	report_lines = 0; \
	n = build_beacon(m.join_packet, 7, false, &off); \
} while (0)
	for (unsigned int g = 4; g < 16; g++) {
		if (!(g & 4)) continue;
		for (unsigned int pad = 0; pad < 2; pad++) {
			RESET(); n = build_beacon(m.join_packet, g, pad, &off);
			assert(one(&m, n, off, true) == 0);
			assert(m.native_diag_total == 1 && m.native_diag_bytes == n);
			assert(m.native_diag_rx[1].type[2] == 1 && !m.native_diag_native);
			assert(m.native_diag_rx[1].beacons == 1);
			assert(!data_calls && !samples && !m.native_diag_rxd_sampled);
		}
	}
	/* Parent has no native management dispatch: paired runner expects this
	 * child positive to fail on the exact ND4 parent, without a kernel boot. */
	for (unsigned int state = 0; state <= MT6797_ND_CLOSED; state++) {
		if (state == MT6797_ND_ACTIVE) continue;
		RESET(); m.native_diag_state = state;
		assert(one(&m, n, off, false) == 0 && !data_calls && !samples);
	}
	RESET(); m.native_diag_engaged = false; assert(one(&m, n, off, false) == 0);
	RESET(); m.join_data_ended = true;
	assert(one(&m, n, off, false) == 0 && !data_calls && !samples);
	assert(m.native_diag_retire_reads == 1 && m.native_diag_rx[2].type[2] == 1);
	RESET(); m.native_diag_sample_done = true;
	assert(one(&m, n, off, false) == 0 && !data_calls);
	RESET(); m.native_diag_total = MT6797_NATIVE_DIAG_RX_MAX - 1;
	assert(one(&m, n, off, false) == 0 && !data_calls);
	RESET(); m.native_diag_bytes = MT6797_NATIVE_DIAG_BYTES_MAX - n;
	assert(one(&m, n, off, false) == 0 && !data_calls);
	RESET(); m.native_diag_native = MT6797_NATIVE_DIAG_NATIVE_MAX;
	assert(one(&m, n, off, false) == 0 && !data_calls);
	RESET(); m.native_diag_started -= (u64)MT6797_NATIVE_DIAG_WALL_MS * NSEC_PER_MSEC;
	assert(one(&m, n, off, false) == 0 && !data_calls);
	/* Failure to establish joined/current AP preserves ordinary withholding. */
	RESET(); m.join_assoc_received = false;
	assert(one(&m, n, off, false) == 0 && data_calls == 1);
	RESET(); m.join_assoc_status = 1; assert(one(&m, n, off, false) == 0);
	RESET(); m.join_cleanup_done = true; assert(one(&m, n, off, false) == 0);
	RESET(); m.join_deauth_done = true; assert(one(&m, n, off, false) == 0);
	RESET(); m.join_packet[off + 10] ^= 4; assert(one(&m, n, off, false) == 0);
	/* Normal helper allocation failure follows the actual goto failed path. */
	RESET(); fail_alloc = true;
	assert(one(&m, n, off, false) == -ENOMEM && !data_calls && !samples);
	/* The original class7 clean and keyed selectors remain ahead of the new
	 * path and use the same verbatim helper (including before ACTIVE). */
	RESET(); m.native_diag_state = MT6797_ND_ENABLE_PENDING;
	m.join_packet[2] = 1; m.join_packet[3] = 0xee;
	m.join_packet[10] = 0; m.join_packet[11] = 0;
	assert(one(&m, n, off, true) == 0 && !data_calls && !samples);
	RESET(); m.native_diag_state = MT6797_ND_CLOSED; m.join_key_group = 1;
	m.join_packet[2] = 1; m.join_packet[3] = 0xee;
	m.join_packet[4] = 8; m.join_packet[7] = 4;
	m.join_packet[8] = 2; m.join_packet[9] = 0x40;
	assert(one(&m, n, off, true) == 0 && m.join_keyed_beacons == 1);
	assert(!m.native_diag_rx[1].beacons);
	RESET(); assert(one(&m, n, off, true) == 0);
	mt6797_native_diag_rx_report(&m);
	mt6797_native_diag_rx_report(&m);
	assert(report_lines == 8 && strstr(report[2], "phase=1"));
	assert(strstr(report[2], "beacons=1"));
	assert(!strstr(report[0], "beacons=1") && !strstr(report[4], "beacons=1") &&
	       !strstr(report[6], "beacons=1"));
	/* An ordinary protected CCMP-shaped frame still takes the original data
	 * path, not management: one data call/eligibility/native queue/sample, no
	 * beacon debit or crypto bypass/strip flags, original bytes unchanged. */
	RESET();
	m.join_packet[off] = 0x08; m.join_packet[off + 1] = 0x42;
	memcpy(m.join_packet + off + 4, own, 6);
	m.join_packet[off + 26] = 0; m.join_packet[off + 27] = 0x20;
	{
		struct mt6797_hif_rx_result rx = {n, mt6797_join_le16(m.join_packet + 2)};
		struct sk_buff_head q = {0};

		assert(dispatch(&m, &rx, &q) == 0 && q.count == 1);
		assert(data_calls == 1 && samples == 1 && m.native_diag_native == 1);
		assert(!m.join_beacons_delivered && !m.native_diag_rx[1].beacons);
		assert(m.native_diag_rx[1].gate[MT6797_NATIVE_RX_OK] == 1);
		assert(!(q.skb->status.flag & mt6797_native_diag_crypto_bypass_mask()));
		assert(q.skb->len == n - off && !memcmp(q.skb->data, m.join_packet + off, n - off));
		free(q.skb);
	}
	puts("native beacon actual dispatch: PASS verbatim/flags0, phases/ceilings/accounting/failures, class7 unchanged");
	return 0;
}
