/* SPDX-License-Identifier: GPL-2.0-only */
/* Host fixture for the production scan-packet handler; no firmware or mac80211 model. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
#define BIT(n) (1U << (n))
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_SCAN_TUNING_SAMPLE 0
#define NSEC_PER_USEC 1000ULL
#define NL80211_BAND_2GHZ 0
#define NL80211_BAND_5GHZ 1
#define IEEE80211_CHAN_DISABLED (1 << 0)
#define IEEE80211_CHAN_RADAR (1 << 3)
#define IEEE80211_CHAN_NO_20MHZ (1 << 10)
#define GFP_KERNEL 0
#define dev_info(dev, ...) do { } while (0)
#define wiphy_dev(w) (w)
static __attribute__((unused)) u32 get_unaligned_le32(const void *p) { const u8 *b = p; return b[0] | b[1] << 8 | b[2] << 16 | (u32)b[3] << 24; }
#include <scan-wire.h>
struct ieee80211_channel { unsigned band, center_freq, hw_value, flags; };
struct ieee80211_rx_status { int band, freq, signal, flag; unsigned rate_idx, encoding; };
struct sk_buff { u8 *data; unsigned len; struct ieee80211_rx_status cb; struct sk_buff *next; };
struct sk_buff_head { struct sk_buff *head, *tail; unsigned count; };
#define IEEE80211_SKB_RXCB(s) (&(s)->cb)
static bool allocation_failure;
static struct sk_buff *dev_alloc_skb(unsigned n)
{ struct sk_buff *s; if (allocation_failure) return NULL; s = calloc(1, sizeof(*s)); s->data = calloc(1, n ? n : 1); return s; }
static void skb_put_data(struct sk_buff *s, const void *p, unsigned n) { memcpy(s->data, p, n); s->len = n; }
/* FIFO like the production queue: delivery order is the frame order. */
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *s)
{ s->next = NULL; if (q->tail) q->tail->next = s; else q->head = s; q->tail = s; q->count++; }
struct mt6797_hif { int unused; };
static int mt6797_hif_read32(struct mt6797_hif *h, unsigned reg, u64 deadline, u32 *v) { (void)h; (void)reg; (void)deadline; *v = BIT(8); return 0; }
struct ieee80211_hw { void *wiphy; };
struct mt6797_mac {
	struct ieee80211_hw *hw; struct mt6797_hif *hif;
	struct ieee80211_channel channels[MT6797_CHANNELS];
	unsigned scan_channels, scan_count; bool scan_frame_seen, scan_beacon;
	u8 scan_packet[2048];
};
#include "scan-packet-function.h"

/* One scan RX packet: 16-byte header, the 24-byte vector group (RCPI at +9),
 * then the 802.11 frame; see mt6797_scan_frame for the accepted layout.
 */
static size_t build(u8 *out, unsigned channel, unsigned rcpi, u16 fc, const u8 *body, size_t body_len)
{
	size_t offset = 16 + 24, total = offset + 24 + body_len;
	memset(out, 0, total);
	out[0] = total & 0xff; out[1] = total >> 8;          /* length */
	out[2] = 0x01; out[3] = 0xe8;                        /* type 0xe001 | (group 4 << 9) = 0xe801 */
	out[5] = (u8)channel; out[6] = 24;                   /* channel, header length */
	out[16 + 9] = (u8)rcpi;                              /* RCPI in the vector group */
	out[offset] = fc & 0xff; out[offset + 1] = fc >> 8;  /* frame control */
	memset(out + offset + 4, 0xff, 6);                   /* DA broadcast */
	memcpy(out + offset + 24, body, body_len);
	return total;
}

int main(void)
{
	struct ieee80211_hw hw = {0}; struct mt6797_hif hif = {0};
	struct mt6797_mac m = {.hw = &hw, .hif = &hif};
	struct sk_buff_head q = {0};
	u8 body[40] = {0};
	int slot = mt6797_channel_slot(40);
	bool done = false;
	size_t n;

	assert(slot >= (int)MT6797_2G_CHANNELS);
	m.channels[slot] = (struct ieee80211_channel){.band = NL80211_BAND_5GHZ, .center_freq = 5200, .hw_value = 40};
	m.scan_channels = BIT(slot);
	/* Beacon on the admitted channel: queued once with band, frequency and dBm signal. */
	n = build(m.scan_packet, 40, 100, 0x0080, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == 0 && q.count == 1 && m.scan_beacon && !done);
	assert(q.head->cb.band == NL80211_BAND_5GHZ && q.head->cb.freq == 5200 && q.head->cb.signal == 100 / 2 - 110);
	assert(q.head->cb.rate_idx == 0 && q.head->cb.flag == 0 && q.head->len == 24 + sizeof(body));
	assert(memcmp(q.head->data, m.scan_packet + 40, q.head->len) == 0);
	/* Probe response is accepted too and queued AFTER the beacon (FIFO); an action
	 * frame is not a scan result and is dropped silently. */
	n = build(m.scan_packet, 40, 90, 0x0050, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == 0 && q.count == 2);
	assert(q.head->cb.signal == 100 / 2 - 110 && q.head->next == q.tail && q.tail->cb.signal == 90 / 2 - 110);
	assert((q.head->data[0] & 0xff) == 0x80 && (q.tail->data[0] & 0xff) == 0x50 && q.tail->next == NULL);
	n = build(m.scan_packet, 40, 90, 0x00d0, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == 0 && q.count == 2);
	/* A channel outside the admitted set is a protocol error; a disabled channel is refused. */
	n = build(m.scan_packet, 36, 90, 0x0080, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == -EPROTO && q.count == 2);
	m.channels[slot].flags = IEEE80211_CHAN_DISABLED;
	n = build(m.scan_packet, 40, 90, 0x0080, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == -EACCES && q.count == 2);
	m.channels[slot].flags = 0;
	/* Allocation failure is reported, nothing is queued. */
	allocation_failure = true;
	n = build(m.scan_packet, 40, 90, 0x0080, body, sizeof(body));
	assert(mt6797_mac_scan_packet(&m, n, 1, &done, &q) == -ENOMEM && q.count == 2);
	while (q.head) { struct sk_buff *s = q.head; q.head = s->next; free(s->data); free(s); }
	puts("scan-report=pass");
	return 0;
}
