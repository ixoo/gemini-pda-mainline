/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdarg.h>
#define mt6797_data_rx_native_gate actual_native_gate
#define main baseline_main
#include "native-rx-test.c"
#undef main
#undef mt6797_data_rx_native_gate

#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#include "native-diag.h"
typedef unsigned char u8;

static unsigned int calls, lines;
static enum mt6797_native_rx_gate
mt6797_data_rx_native_gate(const unsigned char *p, size_t n, unsigned char c,
			  const unsigned char *o, const unsigned char *a,
			  size_t *off, size_t *len)
{
	calls++;
	return actual_native_gate(p, n, c, o, a, off, len);
}

struct wiphy_stub { unsigned char perm_addr[6]; };
struct hw_stub { struct wiphy_stub *wiphy; };
struct mt6797_mac {
	struct hw_stub *hw;
	unsigned int native_diag_state;
	bool native_diag_engaged, native_diag_sample_done, join_data_ended;
	unsigned char join_packet[512], join_ap[6];
#include "metadata-fields.h"
};
struct mt6797_hif_rx_result { unsigned int packet_type; size_t logical_bytes; };
#define wiphy_dev(w) (w)
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args;
	(void)dev;
	assert(!strstr(format, "%s") && !strstr(format, "%p"));
	lines++;
	va_start(args, format);
	vprintf(format, args);
	va_end(args);
}
#include "metadata-hooks.h"

int main(void)
{
	struct wiphy_stub wiphy = {0};
	struct hw_stub hw = { .wiphy = &wiphy };
	struct mt6797_mac m = { .hw = &hw };
	struct mt6797_hif_rx_result rx;
	size_t off;
	int phase;

	memcpy(wiphy.perm_addr, own, 6);
	memcpy(m.join_ap, ap, 6);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_IDLE, false) == -1);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_DISABLE_PENDING, false) == -1);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_ENABLE_PENDING, false) == 0);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_ACTIVE, false) == 1);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_ENABLE_PENDING, true) == 2);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_ACTIVE, true) == 2);
	assert(mt6797_native_diag_rx_phase(MT6797_ND_CLOSED, true) == 3);
	mt6797_native_diag_rx_report(&m);
	assert(!lines && !m.native_diag_rx_reported);
	m.native_diag_engaged = true;
	/* A pending 442B packet counted by the window is NOT decoded or relabeled. */
	m.native_diag_state = MT6797_ND_ENABLE_PENDING;
	rx.packet_type = 7U << 13; rx.logical_bytes = 442;
	phase = observed_class(&m, &rx);
	assert(phase == 0);
	m.native_diag_state = MT6797_ND_ACTIVE;
	assert(m.native_diag_rx[0].type[7] == 1 && !m.native_diag_rx[1].type[7]);
	/* Simulate remaining-dispatch arrival at the hook while pending: blocked. */
	observed_gate(&m, &rx, phase, false);
	assert(!calls && m.native_diag_rx[0].window_blocked == 1);
	/* ACTIVE frames reaching the hook: first rejection only, then eligibility. */
	rx.logical_bytes = build_g(m.join_packet, 5, 0, 0, &off);
	rx.packet_type = 2U << 13;
	m.join_packet[6] |= 0x80;
	m.join_packet[off + 1] &= ~0x40;
	phase = observed_class(&m, &rx);
	assert(!observed_gate(&m, &rx, phase, true));
	assert(calls == 1 && m.native_diag_rx[1].gate[MT6797_NATIVE_RX_TRANSLATED] == 1);
	assert(!m.native_diag_rx[1].gate[MT6797_NATIVE_RX_UNPROTECTED]);
	rx.logical_bytes = build_g(m.join_packet, 5, 0, 0, &off);
	phase = observed_class(&m, &rx);
	assert(observed_gate(&m, &rx, phase, true));
	assert(calls == 2 && m.native_diag_rx[1].gate[MT6797_NATIVE_RX_OK] == 1);
	/* ACTIVE packet at a reached ceiling stays withheld; decoder not called. */
	phase = observed_class(&m, &rx);
	assert(!observed_gate(&m, &rx, phase, false));
	assert(calls == 2 && m.native_diag_rx[1].window_blocked == 1);
	/* Drain is counted BEFORE its exact-TX-done/continue dispatch, no decoder. */
	m.join_data_ended = true;
	rx.packet_type = 7U << 13;
	phase = observed_class(&m, &rx);
	assert(phase == 2 && calls == 2 && m.native_diag_rx[2].type[7] == 1);
	/* CLOSED inherited receive is separate and never admits native decoding. */
	m.native_diag_state = MT6797_ND_CLOSED;
	phase = observed_class(&m, &rx);
	assert(phase == 3 && !observed_gate(&m, &rx, phase, false));
	assert(calls == 2 && m.native_diag_rx[3].window_blocked == 1);
	mt6797_native_diag_rx_report(&m);
	mt6797_native_diag_rx_report(&m);
	assert(lines == 9 && m.native_diag_rx_reported && m.native_diag_rxd_sampled);
	assert(!(mt6797_native_diag_ordinary_flags(0) &
		 mt6797_native_diag_crypto_bypass_mask()));
	/* A first admitted short frame reports ABSENT descriptor fields, not stale
	 * buffer data; blocked frames never emit or consume the sample. */
	{
		struct mt6797_mac short_mac = { .hw = &hw,
			.native_diag_engaged = true, .native_diag_state = MT6797_ND_ACTIVE };
		unsigned int before = lines;

		memset(short_mac.join_packet, 0xff, sizeof(short_mac.join_packet));
		rx.logical_bytes = 4; rx.packet_type = 2U << 13;
		phase = observed_class(&short_mac, &rx);
		assert(!observed_gate(&short_mac, &rx, phase, false));
		assert(lines == before && !short_mac.native_diag_rxd_sampled);
		assert(!observed_gate(&short_mac, &rx, phase, true));
		assert(lines == before + 1 && short_mac.native_diag_rxd_sampled);
		assert(short_mac.native_diag_rx[1].gate[MT6797_NATIVE_RX_INPUT] == 1);
		/* Every actual call contributes exactly one first-gate count. Class
		 * counts also include packets consumed before reaching this hook. */
		{
			unsigned int total_calls = 0;

			for (unsigned int p = 0; p < 4; p++) {
				unsigned int types = 0, gates = 0;

				for (unsigned int t = 0; t < 8; t++)
					types += m.native_diag_rx[p].type[t];
				for (unsigned int g = 0; g < MT6797_NATIVE_RX_GATES; g++)
					gates += m.native_diag_rx[p].gate[g];
				assert(gates + m.native_diag_rx[p].window_blocked <= types);
				total_calls += gates;
			}
			total_calls += short_mac.native_diag_rx[1].gate[MT6797_NATIVE_RX_INPUT];
			assert(total_calls == calls);
		}
	}
	puts("native metadata phases: pending/active/drain/closed, no blocked decode, eight terminal lines plus one guarded sample");
	return 0;
}
