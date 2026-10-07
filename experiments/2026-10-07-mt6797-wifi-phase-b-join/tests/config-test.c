/* SPDX-License-Identifier: GPL-2.0-only */
/* Host fixture for the production config operation; no mac80211 model. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fixed-channels.h>
typedef uint32_t u32;
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_STATION_JOIN 1
#define CONFIG_MT6797_PASSIVE_SCAN 1
#define NL80211_BAND_2GHZ 0
#define NL80211_BAND_5GHZ 1
#define NL80211_CHAN_WIDTH_20_NOHT 0
#define NL80211_CHAN_WIDTH_20 1
#define IEEE80211_CONF_MONITOR (1 << 0)
#define IEEE80211_CONF_PS (1 << 1)
#define IEEE80211_CHAN_DISABLED (1 << 0)
#define IEEE80211_CHAN_NO_IR (1 << 1)
#define IEEE80211_CHAN_RADAR (1 << 3)
#define IEEE80211_CHAN_NO_20MHZ (1 << 10)
struct ieee80211_channel { unsigned band, center_freq, hw_value, flags; };
struct cfg80211_chan_def { struct ieee80211_channel *chan; unsigned width, center_freq1, center_freq2; };
struct ieee80211_hw { void *priv; void *wiphy; struct { unsigned flags; struct cfg80211_chan_def chandef; } conf; };
struct mt6797_mac {
 int mutex; bool scan_ready, closing, join_channel_valid, join_channel_refusal_logged;
 int first_error; struct ieee80211_channel channels[MT6797_CHANNELS];
};
static unsigned refusal_logs; static int logged_config;
static void record(const char *fmt, ...)
{ va_list ap; va_start(ap, fmt);
  if (strstr(fmt, "channel refused")) { for (int i = 0; i < 5; i++) (void)va_arg(ap, unsigned);
    (void)va_arg(ap, unsigned); logged_config = va_arg(ap, int); refusal_logs++; }
  va_end(ap); }
#define dev_info(dev, ...) record(__VA_ARGS__)
#define wiphy_dev(w) (w)
static int locked;
#define mutex_lock(m) do { assert(!locked); locked = 1; (void)(m); } while (0)
#define mutex_unlock(m) do { assert(locked); locked = 0; (void)(m); } while (0)
#include "config-function.h"

static struct mt6797_mac ready(struct ieee80211_hw *hw)
{
 struct mt6797_mac m = {.scan_ready = true};
 int slot = mt6797_channel_slot(40);
 assert(slot >= (int)MT6797_2G_CHANNELS && slot < (int)MT6797_CHANNELS);
 m.channels[slot] = (struct ieee80211_channel){.band = NL80211_BAND_5GHZ, .center_freq = 5200, .hw_value = 40};
 memset(hw, 0, sizeof(*hw));
 hw->conf.chandef = (struct cfg80211_chan_def){.width = NL80211_CHAN_WIDTH_20_NOHT, .center_freq1 = 5200};
 return m;
}

int main(void)
{
 struct ieee80211_hw hw; struct mt6797_mac m = ready(&hw); hw.priv = &m;
 int slot = mt6797_channel_slot(40);
 hw.conf.chandef.chan = &m.channels[slot];
 /* mac80211's whole-wiphy call: radio index -1 is accepted and binds channel 40. */
 assert(mt6797_mac_config(&hw, -1, 0) == 0 && m.join_channel_valid && !refusal_logs && !locked);
 /* A radio-specific request is refused, and the binding names the refusal once. */
 assert(mt6797_mac_config(&hw, 0, 0) == -EOPNOTSUPP && !m.join_channel_valid);
 assert(refusal_logs == 1 && logged_config == -EOPNOTSUPP);
 assert(mt6797_mac_config(&hw, 1, 0) == -EOPNOTSUPP && refusal_logs == 1);
 /* Back to -1: valid again; the NO-IR flag or a different width breaks the binding without an error. */
 assert(mt6797_mac_config(&hw, -1, 0) == 0 && m.join_channel_valid);
 m.channels[slot].flags = IEEE80211_CHAN_NO_IR;
 assert(mt6797_mac_config(&hw, -1, 0) == 0 && !m.join_channel_valid && refusal_logs == 1);
 m.channels[slot].flags = 0; hw.conf.chandef.width = NL80211_CHAN_WIDTH_20;
 assert(mt6797_mac_config(&hw, -1, 0) == 0 && !m.join_channel_valid);
 hw.conf.chandef.width = NL80211_CHAN_WIDTH_20_NOHT;
 /* Power save or monitor flags, or a non-ready MAC, refuse. */
 hw.conf.flags = IEEE80211_CONF_PS; assert(mt6797_mac_config(&hw, -1, 0) == -EOPNOTSUPP); hw.conf.flags = 0;
 m.scan_ready = false; assert(mt6797_mac_config(&hw, -1, 0) == -EOPNOTSUPP); m.scan_ready = true;
 /* A 2.4 GHz operating channel is not a join channel and logs nothing. */
 int slot1 = mt6797_channel_slot(1); assert(slot1 >= 0 && slot1 < (int)MT6797_2G_CHANNELS);
 m.channels[slot1] = (struct ieee80211_channel){.band = NL80211_BAND_2GHZ, .center_freq = 2412, .hw_value = 1};
 hw.conf.chandef.chan = &m.channels[slot1]; hw.conf.chandef.center_freq1 = 2412;
 assert(mt6797_mac_config(&hw, -1, 0) == 0 && !m.join_channel_valid && refusal_logs == 1);
 /* No operating channel at all. */
 hw.conf.chandef.chan = NULL; assert(mt6797_mac_config(&hw, -1, 0) == 0 && !m.join_channel_valid);
 puts("config=pass");
 return 0;
}
