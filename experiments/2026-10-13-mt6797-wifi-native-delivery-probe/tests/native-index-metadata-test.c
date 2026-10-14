/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdlib.h>
#include <stdarg.h>
#define mt6797_data_rx_native_gate actual_data_gate
#define main beacon_layout_main
#include "native-beacon-test.c"
#undef main
#define own data_own
#define ap data_ap
#define main data_layout_main
#include "native-rx-test.c"
#undef main
#undef ap
#undef own
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
static u64 now = 1000000000ULL;
static u64 ktime_get_ns(void) { return now; }

struct ieee80211_rx_status { unsigned int flag, band, freq; int signal; };
struct sk_buff { u8 data[4096]; size_t len; struct ieee80211_rx_status status; };
struct sk_buff_head { struct sk_buff *skb; unsigned int count; };
struct wiphy_stub { u8 perm_addr[6]; };
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
	struct {
		unsigned int type[8], gate[MT6797_NATIVE_RX_GATES], window_blocked, beacons;
		unsigned int reported_idx1_translated, reported_idx1_untranslated;
	} native_diag_rx[4];
	unsigned int join_beacons_delivered, join_keyed_beacons;
};
struct mt6797_hif_rx_result { size_t logical_bytes; unsigned int packet_type; };
static unsigned int data_calls, samples, terminal_lines;
static char sample[2048], terminal[8][2048];
static bool fail_alloc;
#define wiphy_dev(w) (w)
#define IEEE80211_SKB_RXCB(s) (&(s)->status)
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args;
	(void)dev;
	assert(!strstr(format, "%s") && !strstr(format, "%p"));
	va_start(args, format);
	if (strstr(format, "native RX descriptor:")) {
		samples++;
		assert(vsnprintf(sample, sizeof(sample), format, args) > 0);
	} else if (strstr(format, "native RX classes:") || strstr(format, "native RX gates:")) {
		assert(terminal_lines < 8);
		assert(vsnprintf(terminal[terminal_lines++], sizeof(terminal[0]), format, args) > 0);
	}
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
#include "index-metadata-dispatch.h"

static int one(struct mt6797_mac *m, size_t n, unsigned int label)
{
	struct mt6797_hif_rx_result rx = {n, mt6797_join_le16(m->join_packet + 2)};
	struct sk_buff_head q = {0};
	u8 saved[512];
	unsigned int sum = 0, before = data_calls;
	unsigned int native_before = m->native_diag_native;
	int ret;

	memcpy(saved, m->join_packet, sizeof(saved));
	ret = dispatch(m, &rx, &q);
	assert(!memcmp(saved, m->join_packet, sizeof(saved)));
	for (unsigned int g = 0; g < MT6797_NATIVE_RX_GATES; g++)
		sum += m->native_diag_rx[1].gate[g];
	printf("case=%u ret=%d queued=%u native=%u beacons=%u calls=%u gates=%u blocked=%u",
	       label, ret, q.count, m->native_diag_native, m->join_beacons_delivered,
	       data_calls - before, sum, m->native_diag_rx[1].window_blocked);
	for (unsigned int p = 0; p < 4; p++) {
		for (unsigned int g = 0; g < MT6797_NATIVE_RX_GATES; g++)
			printf(" g%u_%u=%u", p, g, m->native_diag_rx[p].gate[g]);
		for (unsigned int t = 0; t < 8; t++)
			printf(" t%u_%u=%u", p, t, m->native_diag_rx[p].type[t]);
		printf(" blocked%u=%u beacon%u=%u", p, m->native_diag_rx[p].window_blocked,
		       p, m->native_diag_rx[p].beacons);
	}
	if (q.skb) {
		unsigned int checksum = 0;
		size_t offset, length;

		if (m->native_diag_native > native_before) {
			assert(actual_data_gate(saved, n, 40, own, ap, &offset, &length) ==
			       MT6797_NATIVE_RX_OK);
			assert(q.skb->len == length && !memcmp(q.skb->data, saved + offset, length));
			assert(!(q.skb->status.flag & mt6797_native_diag_crypto_bypass_mask()));
		}
		for (size_t i = 0; i < q.skb->len; i++) checksum = checksum * 33U + q.skb->data[i];
		printf(" bytes=%zu checksum=%u flags=%u band=%u freq=%u signal=%d",
		       q.skb->len, checksum, q.skb->status.flag, q.skb->status.band,
		       q.skb->status.freq, q.skb->status.signal);
	}
	putchar('\n');
	free(q.skb);
	return ret;
}

int main(void)
{
	struct wiphy_stub wiphy = {0};
	struct hw_stub hw = {&wiphy};
	struct mt6797_mac m;
	size_t n, off;
	unsigned int label = 0;

	beacon_layout_main();
	data_layout_main();
	memcpy(wiphy.perm_addr, own, 6);
#define RESET() do { \
	memset(&m, 0, sizeof(m)); m.hw = &hw; memcpy(m.join_ap, ap, 6); \
	m.native_diag_engaged = true; m.native_diag_state = MT6797_ND_ACTIVE; \
	m.native_diag_started = now; m.join_assoc_received = true; \
	data_calls = samples = terminal_lines = 0; sample[0] = 0; fail_alloc = false; \
	n = build_g(m.join_packet, 7, false, false, &off); m.join_packet[8] = 1; \
} while (0)
	/* Untranslated reported1 and wrong-index translated calls cannot consume
	 * the new sample. The next qualifying call must still be observable. */
	RESET(); assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(!samples && !m.native_diag_rxd_sampled);
	assert(m.native_diag_rx[1].reported_idx1_untranslated == 1);
#endif
	m.join_packet[6] |= 0x80; m.join_packet[8] = 2;
	assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(!samples && m.native_diag_rx[1].reported_idx1_translated == 0);
#endif
	m.join_packet[8] = 1;
	assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(samples == 1 && m.native_diag_rxd_sampled);
	assert(strstr(sample, "group4_valid=0 fc=0x0000 ta_ap_equal=0"));
	assert(m.native_diag_rx[1].reported_idx1_translated == 1);
#endif
	assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(samples == 1 && m.native_diag_rx[1].reported_idx1_translated == 2);
#endif
	/* Group4 present at16: FC/TA report comes from metadata, NOT the Ethernet
	 * destination at the derived body offset, regardless of pad/other groups. */
	for (unsigned int g = 0; g < 16; g++)
		for (unsigned int pad = 0; pad < 2; pad++) {
			RESET(); n = build_g(m.join_packet, g, pad, false, &off);
			m.join_packet[6] |= 0x80; m.join_packet[8] = 1;
			m.join_packet[9] = 0x4b;
			m.join_packet[off] = 0x08; m.join_packet[off + 1] = 0x40;
			if (g & 8) {
				m.join_packet[16] = 0x88; m.join_packet[17] = 0x42;
				memcpy(m.join_packet + 18, ap, 6);
			}
			assert(one(&m, n, label++) == 0 && data_calls == 1);
#ifdef METADATA_CHILD
			assert(samples == 1 && strstr(sample, "reported_index=1 security_mode=4"));
			if (g & 8)
				assert(strstr(sample, "group4_valid=1 fc=0x4288 ta_ap_equal=1"));
			else
				assert(strstr(sample, "group4_valid=0 fc=0x0000 ta_ap_equal=0"));
			assert(!strstr(sample, "fc=0x4008"));
#endif
		}
	/* Security is exactly the upper nibble; TA mismatch does not change FC
	 * availability or become a packet-authentication result. */
	for (unsigned int sec = 0; sec < 16; sec++) {
		char expected[64];
		RESET(); n = build_g(m.join_packet, 8, false, false, &off);
		m.join_packet[6] |= 0x80; m.join_packet[8] = 1;
		m.join_packet[9] = (sec << 4) | 15;
		m.join_packet[16] = 0; m.join_packet[17] = 0;
		memcpy(m.join_packet + 18, ap, 6); m.join_packet[23] ^= 1;
		assert(one(&m, n, label++) == 0);
		snprintf(expected, sizeof(expected), "security_mode=%u group4_valid=1", sec);
#ifdef METADATA_CHILD
		assert(samples == 1 && strstr(sample, expected));
		assert(strstr(sample, "fc=0x0000 ta_ap_equal=0"));
#endif
	}
	/* Full RXD absent => no index counter/sample. Full RXD but short group4
	 * selects one ABSENT group4 sample; later bytes are never read as fields. */
	for (unsigned int bytes = 4; bytes <= 32; bytes++) {
		RESET(); n = bytes; m.join_packet[0] = n; m.join_packet[1] = 0;
		m.join_packet[3] = 0x50; m.join_packet[2] = 0;
		m.join_packet[6] |= 0x80;
		memset(m.join_packet + 16, 0xaa, sizeof(m.join_packet) - 16);
		assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
		if (bytes < 16) {
			assert(!samples && !m.native_diag_rx[1].reported_idx1_translated);
		} else {
			assert(samples == 1 && m.native_diag_rx[1].reported_idx1_translated == 1);
			if (bytes < 32)
				assert(strstr(sample, "group4_valid=0 fc=0x0000 ta_ap_equal=0"));
			else
				assert(strstr(sample, "group4_valid=1 fc=0xaaaa ta_ap_equal=0"));
		}
#endif
	}
	/* Translation/index reports with earlier length/channel failure still
	 * describe an actual call, but MUST NOT select a TRANSLATED-gate sample. */
	RESET(); m.join_packet[6] |= 0x80; m.join_packet[0]--;
	assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(!samples && m.native_diag_rx[1].reported_idx1_translated == 1);
#endif
	RESET(); m.join_packet[6] |= 0x80; m.join_packet[5] = 36;
	assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
	assert(!samples);
#endif
	/* All inactive/off/drain/ceiling/blocked paths remain inert. */
	for (unsigned int state = 0; state <= MT6797_ND_CLOSED; state++) {
		if (state == MT6797_ND_ACTIVE) continue;
		RESET(); m.native_diag_state = state; m.join_packet[6] |= 0x80;
		assert(one(&m, n, label++) == 0 && !data_calls && !samples);
#ifdef METADATA_CHILD
		assert(!m.native_diag_rx[1].reported_idx1_translated);
#endif
	}
	for (unsigned int stop = 0; stop < 7; stop++) {
		RESET(); m.join_packet[6] |= 0x80;
		if (stop == 0) m.native_diag_engaged = false;
		if (stop == 1) m.join_data_ended = true;
		if (stop == 2) m.native_diag_sample_done = true;
		if (stop == 3) m.native_diag_total = MT6797_NATIVE_DIAG_RX_MAX - 1;
		if (stop == 4) m.native_diag_bytes = MT6797_NATIVE_DIAG_BYTES_MAX - n;
		if (stop == 5) m.native_diag_native = MT6797_NATIVE_DIAG_NATIVE_MAX;
		if (stop == 6) m.native_diag_started -= (u64)MT6797_NATIVE_DIAG_WALL_MS * NSEC_PER_MSEC;
		assert(one(&m, n, label++) == 0 && !data_calls && !samples);
#ifdef METADATA_CHILD
		assert(!m.native_diag_rx[1].reported_idx1_translated);
#endif
	}
	/* Native beacon and class7 paths never reach this ordinary metadata hook. */
	RESET(); n = build_beacon(m.join_packet, 7, false, &off); m.join_packet[8] = 1;
	assert(one(&m, n, label++) == 0 && !data_calls && !samples);
#ifdef METADATA_CHILD
	assert(!m.native_diag_rx[1].reported_idx1_untranslated);
#endif
	RESET(); n = build_beacon(m.join_packet, 7, false, &off); m.join_packet[8] = 1;
	fail_alloc = true;
	assert(one(&m, n, label++) == -ENOMEM && !data_calls && !samples);
#ifdef METADATA_CHILD
	assert(!m.native_diag_rx[1].reported_idx1_untranslated);
#endif
	RESET(); n = build_beacon(m.join_packet, 7, false, &off);
	m.join_packet[2] = 1; m.join_packet[3] = 0xee; m.join_packet[10] = m.join_packet[11] = 0;
	assert(one(&m, n, label++) == 0 && !data_calls && !samples);
	for (unsigned int cls = 0; cls < 8; cls++) {
		if (cls == 2) continue;
		RESET(); m.join_packet[3] = (m.join_packet[3] & 31) | (cls << 5);
		m.join_packet[6] |= 0x80;
		assert(one(&m, n, label++) == 0);
#ifdef METADATA_CHILD
		assert(!samples && !m.native_diag_rx[1].reported_idx1_translated &&
		       !m.native_diag_rx[1].reported_idx1_untranslated);
#endif
	}
	/* Subsequent allocation failure is still an actual untranslated call, not
	 * a selected translated sample; original decision/failure stays identical. */
	RESET(); fail_alloc = true; assert(one(&m, n, label++) == -ENOMEM);
#ifdef METADATA_CHILD
	assert(!samples && m.native_diag_rx[1].reported_idx1_untranslated == 1);
#endif
	/* Report still exactly8 once, with descriptive scalar counters only. */
	RESET(); m.join_packet[6] |= 0x80; assert(one(&m, n, label++) == 0);
	mt6797_native_diag_rx_report(&m); mt6797_native_diag_rx_report(&m);
	assert(terminal_lines == 8);
#ifdef METADATA_CHILD
	assert(strstr(terminal[2], "reported_idx1_translated=1 reported_idx1_untranslated=0"));
	assert(!strstr(terminal[0], "reported_idx1_translated=1"));
	assert(!strstr(terminal[4], "reported_idx1_translated=1"));
	assert(!strstr(terminal[6], "reported_idx1_translated=1"));
	assert(!strstr(sample, "02:00") && !strstr(sample, "payload") && !strstr(sample, "key="));
#endif
	fputs(sample, stderr);
	for (unsigned int p = 0; p < 8; p++) fputs(terminal[p], stderr);
	return 0;
}
