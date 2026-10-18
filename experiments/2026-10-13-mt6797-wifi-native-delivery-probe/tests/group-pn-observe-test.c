/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <sanitizer/asan_interface.h>
#define main translated_baseline_main
#include "../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"
#undef main
#include "ccmp-rx.h"
#define BIT(n) (1U << (n))
#define MT6797_JOIN_BMC_WLAN_INDEX 2
struct wiphy { unsigned char perm_addr[6]; };
struct hw { struct wiphy *wiphy; };
struct mt6797_mac {
	struct hw *hw;
	unsigned char *join_packet;
	unsigned char join_ap[6], join_group_key_id;
	struct mt6797_ccmp_rx_context ccmp_rx;
	void *ccmp_gtk, *untouched_ptk, *untouched_queue;
	unsigned int join_key_group;
	unsigned int ccmp_group_reported, ccmp_group_shape, ccmp_group_eligible;
	unsigned int ccmp_group_pn_present, ccmp_group_pn_absent, ccmp_group_masks;
	bool native_diag_engaged, native_diag_rx_reported;
	struct {
		unsigned int type[8], gate[17], window_blocked, beacons;
		unsigned int reported_idx1_translated, reported_idx1_untranslated;
	} native_diag_rx[4];
};
static bool ccmp_stable_epoch = true;
static unsigned int group_reports, all_reports, reported_values[6];
static void fake_log(const char *format, ...)
{
	va_list args;

	all_reports++;
	if (strstr(format, "one-shot WLAN group PN observation:")) {
		group_reports++;
		va_start(args, format);
		for (unsigned int i = 0; i < 6; i++)
			reported_values[i] = va_arg(args, unsigned int);
		va_end(args);
	}
}
#define wiphy_dev(w) (w)
#define dev_info(device, ...) do { (void)(device); fake_log(__VA_ARGS__); } while (0)
#include "group-observe.inc"
#include "group-report.inc"

static struct wiphy phy;
static struct hw hw = { &phy };
static unsigned int trials;
static struct mt6797_mac initial(unsigned char *p)
{
	struct mt6797_mac m = {0};

	memcpy(phy.perm_addr, own, 6);
	m.hw = &hw;
	m.join_packet = p;
	memcpy(m.join_ap, ap, 6);
	memset(m.ccmp_rx.pn, 0xa5, 6);
	m.ccmp_gtk = (void *)(uintptr_t)0x100;
	m.untouched_ptk = (void *)(uintptr_t)0x200;
	m.untouched_queue = (void *)(uintptr_t)0x300;
	m.join_key_group = 1;
	m.join_group_key_id = 1;
	return m;
}

static size_t frame(unsigned char *p, unsigned int groups, bool pad, unsigned int key)
{
	unsigned char base[256];
	size_t n = build(base, true, false, 20), at = 16;
	unsigned int type = (2U << 13) | (groups << 9);

	memset(p, 0, 256);
	memcpy(p, base, 16);
	p[2] = type; p[3] = type >> 8;
	p[4] |= key << 6;
	if (groups & 8) { memcpy(p + at, base + 16, 16); at += 16; }
	if (groups & 1) { memset(p + at, 0xda, 16); at += 16; }
	if (groups & 2) at += 8;
	if (groups & 4) { p[at + 9] = 100; at += 24; }
	if (pad) { p[6] |= 0x40; at += 2; }
	memcpy(p + at, base + 32, n - 32);
	n = at + n - 32;
	p[0] = n; p[1] = n >> 8;
	return n;
}

/* Exact allocations and full-state comparison: only observation counters may
 * change; input, keys, PN, queue cookies and terminal state remain identical.
 */
static struct mt6797_mac observe(unsigned char *p, size_t n, bool poison_pn)
{
	unsigned char *exact = malloc(n ? n : 1);
	struct mt6797_mac m, expected;

	assert(exact);
	memcpy(exact, p, n);
	m = initial(exact); expected = m;
	if (poison_pn) __asan_poison_memory_region(exact + 32, 16);
	mt6797_ccmp_group_observe(&m, n);
	if (poison_pn) __asan_unpoison_memory_region(exact + 32, 16);
	assert(!memcmp(exact, p, n));
	expected.ccmp_group_reported = m.ccmp_group_reported;
	expected.ccmp_group_shape = m.ccmp_group_shape;
	expected.ccmp_group_eligible = m.ccmp_group_eligible;
	expected.ccmp_group_pn_present = m.ccmp_group_pn_present;
	expected.ccmp_group_pn_absent = m.ccmp_group_pn_absent;
	expected.ccmp_group_masks = m.ccmp_group_masks;
	assert(!memcmp(&m, &expected, sizeof(m)));
	assert(m.ccmp_group_eligible == m.ccmp_group_pn_present + m.ccmp_group_pn_absent);
	assert(m.ccmp_group_reported >= m.ccmp_group_shape);
	assert(m.ccmp_group_shape >= m.ccmp_group_eligible);
	trials++;
	free(exact);
	m.join_packet = NULL;
	return m;
}

int main(void)
{
	unsigned char p[256], original[256];
	struct mt6797_mac m;
	size_t n, offset;

	assert(translated_baseline_main() == 0);
	for (unsigned int groups = 0; groups < 16; groups++) {
		for (unsigned int pad = 0; pad < 2; pad++) {
			n = frame(p, groups, pad, 1);
			m = observe(p, n, (groups & 9) == 9);
			assert(m.ccmp_group_reported == 1);
			assert(m.ccmp_group_shape == !!(groups & 8));
			assert(m.ccmp_group_eligible == !!(groups & 8));
			assert(m.ccmp_group_pn_present == ((groups & 9) == 9));
			assert(m.ccmp_group_pn_absent == ((groups & 9) == 8));
			assert(m.ccmp_group_masks == ((groups & 8) ? BIT(groups) : 0));
			/* Every exact truncation, no changed declared length. */
			for (size_t cut = 0; cut < n; cut++) {
				m = observe(p, cut, false);
				assert(!m.ccmp_group_shape && !m.ccmp_group_eligible);
			}
		}
	}
	/* Key ID 0 is a valid GTK ID; its WLAN index still distinguishes PTK. */
	for (unsigned int key = 0; key < 4; key++) {
		n = frame(p, 9, false, key);
		m = initial(p); m.join_group_key_id = key;
		mt6797_ccmp_group_observe(&m, n);
		assert(m.ccmp_group_eligible == 1 && m.ccmp_group_pn_present == 1);
	}
	n = frame(p, 9, false, 1); memcpy(original, p, n);
	/* Every status bit, wrong table/BSS/cipher/channel/translation/peer. */
	for (unsigned int bit = 0; bit < 16; bit++) {
		memcpy(p, original, n); p[10 + bit / 8] ^= 1U << (bit % 8);
		m = observe(p, n, false); assert(!m.ccmp_group_shape);
	}
	for (unsigned int byte = 5; byte <= 9; byte++) {
		memcpy(p, original, n); p[byte] ^= 1;
		m = observe(p, n, false);
		if (byte == 9) assert(m.ccmp_group_shape && !m.ccmp_group_eligible);
		else assert(!m.ccmp_group_shape);
	}
	memcpy(p, original, n); p[18] ^= 2;
	m = observe(p, n, true); assert(!m.ccmp_group_shape);
	memcpy(p, original, n); p[4] = 0x02;
	m = observe(p, n, true); assert(!m.ccmp_group_reported);
	memcpy(p, original, n); p[4] = 0x84;
	m = observe(p, n, true); assert(m.ccmp_group_shape && !m.ccmp_group_eligible);
	memcpy(p, original, n); p[4] = 0x44;
	m = observe(p, n, true); assert(m.ccmp_group_eligible); /* multicast */
	offset = 48;
	for (unsigned int kind = 0; kind < 3; kind++) {
		memcpy(p, original, n);
		if (kind == 0) { p[offset + 12] = 0x88; p[offset + 13] = 0x8e; }
		if (kind == 1) { p[offset + 12] = 0; p[offset + 13] = 20; }
		if (kind == 2) { n = offset + 14; p[0] = n; p[1] = n >> 8; }
		m = observe(p, n, true); assert(m.ccmp_group_shape && !m.ccmp_group_eligible);
	}
	n = frame(p, 9, false, 1);
	m = initial(p); m.ccmp_gtk = NULL;
	mt6797_ccmp_group_observe(&m, n); assert(!m.ccmp_group_reported);
	m = initial(p); m.join_key_group = 2;
	mt6797_ccmp_group_observe(&m, n); assert(!m.ccmp_group_reported);
	/* Same 512-acquisition ceiling bounds counters; no packet is delivered. */
	m = initial(p);
	for (unsigned int i = 0; i < 512; i++) mt6797_ccmp_group_observe(&m, n);
	assert(m.ccmp_group_reported == 512 && m.ccmp_group_pn_present == 512);
	m.native_diag_engaged = false;
	mt6797_native_diag_rx_report(&m); assert(!all_reports);
	m.native_diag_engaged = true;
	mt6797_native_diag_rx_report(&m);
	assert(group_reports == 1 && all_reports == 9);
	assert(reported_values[0] == 512 && reported_values[3] == 512);
	mt6797_native_diag_rx_report(&m); assert(group_reports == 1 && all_reports == 9);
	m.native_diag_rx_reported = false; ccmp_stable_epoch = false;
	mt6797_native_diag_rx_report(&m); assert(group_reports == 1);
	printf("PASS %u exact-allocation observation trials, PN-poison, unchanged state and single report\n", trials);
	return 0;
}
