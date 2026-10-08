/* SPDX-License-Identifier: GPL-2.0-only */
/* mac80211's rate matching, exactly as compiled, over the driver's registered rates. */
#include <assert.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define DIV_ROUND_UP(n, d) (((n) + (d) - 1) / (d))
#define BSS_MEMBERSHIP_SELECTOR_MIN 120
static void set_bit(unsigned bit, unsigned long *map) { map[bit / 64] |= 1UL << (bit % 64); }
struct ieee80211_rate { u16 bitrate, hw_value; };
struct ieee80211_supported_band { struct ieee80211_rate *bitrates; int n_bitrates; };
#include "driver-bitrates.h"
#include "rates-function.h"

int main(void)
{
	struct ieee80211_rate rates[16];
	struct ieee80211_supported_band band_5g;
	unsigned n = sizeof(driver_bitrates) / sizeof(driver_bitrates[0]);
	/* The owner AP's "Supported rates: 6.0* 9.0 12.0* 18.0 24.0* 36.0 48.0 54.0"
	 * as the beacon encodes them (500 kbit/s units, basic flag in bit 7).
	 */
	const u8 ap_rates[] = { 0x8c, 0x12, 0x98, 0x24, 0xb0, 0x48, 0x60, 0x6c };
	u32 supp = 0, basic = 0; bool over11 = false; int min_rate = INT_MAX, min_index = -1;

	assert(n == 12);
	for (unsigned i = 0; i < n; i++) { rates[i].bitrate = (u16)driver_bitrates[i]; rates[i].hw_value = (u16)i; }
	/* The driver registers the 5 GHz band as the eight OFDM rates after the four CCK rates. */
	band_5g.bitrates = rates + 4; band_5g.n_bitrates = (int)n - 4;
	ieee80211_get_rates(&band_5g, ap_rates, sizeof(ap_rates), NULL, 0, &supp, &basic, NULL, &over11, &min_rate, &min_index);
	assert(supp == 0xff && basic == (BIT(0) | BIT(2) | BIT(4)) && min_index == 0 && min_rate == 60 && over11);
	/* The record mac80211 reads is empty when a driver informs cfg80211 directly:
	 * this is the exact "No legacy rates in association response" condition. */
	supp = basic = 0; min_rate = INT_MAX; min_index = -1;
	ieee80211_get_rates(&band_5g, NULL, 0, NULL, 0, &supp, &basic, NULL, &over11, &min_rate, &min_index);
	assert(min_index < 0 && !supp && !basic);
	/* A membership selector among the basic rates is not a rate and is reported separately. */
	{ const u8 with_selector[] = { 0x8c, 0xff, 0x98 }; unsigned long selectors[2] = {0}; supp = basic = 0; min_index = -1; min_rate = INT_MAX;
	  ieee80211_get_rates(&band_5g, with_selector, sizeof(with_selector), NULL, 0, &supp, &basic, selectors, &over11, &min_rate, &min_index);
	  assert(supp == (BIT(0) | BIT(2)) && basic == (BIT(0) | BIT(2)) && (selectors[1] & (1UL << (127 - 64)))); }
	puts("rates=pass");
	return 0;
}
