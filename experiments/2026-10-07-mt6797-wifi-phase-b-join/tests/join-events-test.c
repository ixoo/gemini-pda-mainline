/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <assert.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
#include "join-events.h"
int main(void)
{
 u8 tx[24] = {24, 0, 0, 0xe0, 0x0f, 99, 0, 0, 7, 0, 0x34, 0x12, 1, 2};
 u8 ch[24] = {24, 0, 0, 0xe0, 0x10, 99, 0, 0, 0, 3, 0, 40, 0, 2,
              0, 0, 0, 0, 0, 0, 100};
 u8 sta[16] = {16, 0, 0, 0xe0, 0x0c, 19, 0, 0, 2, 3, 4, 5, 6, 7, 1, 0};
 struct mt6797_join_tx_result r = {0}, before;
 struct mt6797_join_channel e = {0, 3, 40, 0, 2, 0, 0, 0, 0, 100};
 u32 interval = 999;
 unsigned int i;
 tx[16] = 1;
 assert(mt6797_join_tx_done(tx, sizeof(tx), 7, 1, &r));
 assert(r.sequence == 0x1234 && r.count == 2);
 tx[16] = 0; tx[14] = 0xff;
 assert(mt6797_join_tx_done(tx, sizeof(tx), 7, 1, &r));
 assert(!r.count && !r.rate);
 before = r;
 for (i = 0; i < sizeof(tx); i++)
  assert(!mt6797_join_tx_done(tx, i, 7, 1, &r));
 assert(!mt6797_join_tx_done(tx, sizeof(tx), 8, 1, &r));
 assert(!mt6797_join_tx_done(tx, sizeof(tx), 7, 2, &r));
 assert(before.status == r.status && before.count == r.count &&
        before.flags == r.flags && before.sequence == r.sequence && before.rate == r.rate);
 assert(mt6797_join_channel_grant(ch, sizeof(ch), &e, &interval));
 assert(interval == 100);
 for (i = 8; i <= 17; i++) {
  ch[i] ^= 1;
  assert(!mt6797_join_channel_grant(ch, sizeof(ch), &e, &interval));
  ch[i] ^= 1;
 }
 ch[20] = 101;
 assert(!mt6797_join_channel_grant(ch, sizeof(ch), &e, &interval));
 ch[20] = 0;
 assert(!mt6797_join_channel_grant(ch, sizeof(ch), &e, &interval));
 assert(mt6797_join_sta_active(sta, sizeof(sta), 19, 1, 0, sta + 8, true));
 assert(!mt6797_join_sta_active(sta, sizeof(sta), 18, 1, 0, sta + 8, true));
 assert(!mt6797_join_sta_active(sta, sizeof(sta), 19, 1, 0, sta + 8, false));
 assert(!mt6797_join_sta_active(sta, sizeof(sta), 19, 2, 0, sta + 8, true));
 for (i = 0; i < 6; i++) {
  u8 mac[6]; memcpy(mac, sta + 8, 6); mac[i] ^= 1;
  assert(!mt6797_join_sta_active(sta, sizeof(sta), 19, 1, 0, mac, true));
 }
 tx[0] = 23;
 assert(!mt6797_join_tx_done(tx, sizeof(tx), 7, 1, &r));
 tx[0] = 24; tx[3] = 0;
 assert(!mt6797_join_tx_done(tx, sizeof(tx), 7, 1, &r));
 return 0;
}
