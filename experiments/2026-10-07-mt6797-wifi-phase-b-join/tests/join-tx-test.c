/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <string.h>
#include "join-tx.h"
int main(void)
{
 unsigned char f[2304] = {0xb0}, d[28], before[28];
 const unsigned char expected[28] = {58,0,26,0x88,1,0xcc,0,4,11,0,15,0x80,
                                    0,0x18,0x23,0x81,0,0,0,0,7,2,0,0,0,0,0x2c,1};
 unsigned int pages = 99;
 f[22] = 0x30; f[23] = 0x12;
 assert(mt6797_join_tx_descriptor(f,30,1,7,500,3,d,&pages));
 assert(!memcmp(d,expected,28) && pages == 1);
 assert(mt6797_join_tx_descriptor(f,100,1,7,1,1,d,&pages));
 assert(d[10] == 1 && pages == 1);
 assert(mt6797_join_tx_descriptor(f,101,1,7,10000,30,d,&pages));
 assert(d[10] == 255 && pages == 2);
 memcpy(before,d,28);
 assert(!mt6797_join_tx_descriptor(f,30,1,7,0,3,d,&pages));
 assert(!mt6797_join_tx_descriptor(f,30,1,7,500,31,d,&pages));
 assert(!mt6797_join_tx_descriptor(f,29,1,7,500,3,d,&pages));
 assert(!mt6797_join_tx_descriptor(f,2305,1,7,500,3,d,&pages));
 f[22] |= 1;
 assert(!mt6797_join_tx_descriptor(f,30,1,7,500,3,d,&pages));
 f[22] &= 0xf0; f[1] = 0x40;
 assert(!mt6797_join_tx_descriptor(f,30,1,7,500,3,d,&pages));
 f[1] = 0; f[0] = 8;
 assert(!mt6797_join_tx_descriptor(f,30,1,7,500,3,d,&pages));
 assert(!memcmp(before,d,28) && pages == 2);
 f[0] = 0;
 assert(mt6797_join_tx_descriptor(f,28,1,7,500,3,d,&pages));
 assert(d[8] == 0);
 f[0] = 0xc0;
 assert(mt6797_join_tx_descriptor(f,26,1,7,500,3,d,&pages));
 assert(d[8] == 12);
 return 0;
}
