/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <string.h>
#include "join-rx.h"
int main(void)
{
 unsigned char p[128] = {0}, own[6]={2,0,0,0,0,1}, ap[6]={2,0,0,0,0,2};
 struct mt6797_join_rx_frame r;
 unsigned char *f=p+40;
 p[0]=70; p[2]=1; p[3]=0xe8; p[5]=40; p[6]=24; p[25]=101;
 f[0]=0xb0; memcpy(f+4,own,6); memcpy(f+10,ap,6); memcpy(f+16,ap,6);
 f[26]=2;
 assert(mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r));
 assert(r.offset==40 && r.bytes==30 && r.signal_dbm==-60 && r.rcpi==101);
 for(unsigned n=0;n<70;n++) assert(!mt6797_join_rx_frame(p,n,40,own,ap,1U<<11,&r));
 assert(!mt6797_join_rx_frame(p,70,36,own,ap,1U<<11,&r));
 assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<1,&r));
 for(unsigned address=4;address<=16;address+=6) for(unsigned i=0;i<6;i++) {
  f[address+i]^=1;
  assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r));
  f[address+i]^=1;
 }
 f[26]=1; assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r)); f[26]=2;
 p[25]=221; assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r)); p[25]=101;
 p[6]|=0x80; assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r)); p[6]=24;
 f[0]=0x10; f[26]=0;
 assert(mt6797_join_rx_frame(p,70,40,own,ap,1U<<1,&r));
 p[0]=73; f[30]=1; f[31]=1; f[32]=12;
 assert(mt6797_join_rx_frame(p,73,40,own,ap,1U<<1,&r));
 f[31]=2; assert(!mt6797_join_rx_frame(p,73,40,own,ap,1U<<1,&r));
 p[0]=71; assert(!mt6797_join_rx_frame(p,71,40,own,ap,1U<<1,&r));
 p[0]=66; f[0]=0xc0;
 assert(mt6797_join_rx_frame(p,66,40,own,ap,1U<<12,&r));
 f[0]=0xa0; assert(mt6797_join_rx_frame(p,66,40,own,ap,1U<<10,&r));
 f[1]=0x40; assert(!mt6797_join_rx_frame(p,66,40,own,ap,1U<<10,&r)); f[1]=0;
 /* All optional firmware groups in wire order, plus two header pad bytes. */
 memmove(p+82,f,26); p[0]=108; p[3]=0xfe; p[6]=24|0x40; p[65]=100;
 assert(mt6797_join_rx_frame(p,108,40,own,ap,1U<<10,&r));
 assert(r.offset==82 && r.bytes==26 && r.signal_dbm==-60);
 p[3]=0xe0; assert(!mt6797_join_rx_frame(p,108,40,own,ap,1U<<10,&r));
 p[3]=0xe8; p[6]=24; p[0]=70; memcpy(p+40,p+82,26);
 p[40]=0xb0; p[66]=2; p[11]=8;
 assert(!mt6797_join_rx_frame(p,70,40,own,ap,1U<<11,&r));
 /* Exercise every optional-group combination and both padding modes.
  * Only combinations with RX vector group 3 carry usable signal evidence. */
 for(unsigned groups=0;groups<16;groups++) for(unsigned pad=0;pad<2;pad++) {
  unsigned char q[128]={0}; unsigned offset=16, vector=0;
  if(groups&8) offset+=16;
  if(groups&1) offset+=16;
  if(groups&2) offset+=8;
  if(groups&4) {vector=offset; offset+=24;}
  offset+=2*pad;
  q[0]=offset+30; q[2]=1; q[3]=0xe0|(groups<<1);
  q[5]=40; q[6]=24|(pad?0x40:0);
  if(vector) q[vector+9]=220;
  q[offset]=0xb0; q[offset+26]=2;
  memcpy(q+offset+4,own,6); memcpy(q+offset+10,ap,6); memcpy(q+offset+16,ap,6);
  assert(mt6797_join_rx_frame(q,offset+30,40,own,ap,1U<<11,&r)==!!vector);
  if(vector) {
   assert(r.offset==offset && r.bytes==30 && r.signal_dbm==0);
   for(unsigned cut=16;cut<offset+30;cut++) {
    q[0]=cut;
    assert(!mt6797_join_rx_frame(q,cut,40,own,ap,1U<<11,&r));
   }
  }
 }
 return 0;
}
