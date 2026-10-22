/* SPDX-License-Identifier: GPL-2.0-only */
#define main existing_decoder_regression
#include "eapol-rx-test.c"
#undef main
#undef MT6797_EAPOL_RX_H
#define mt6797_eapol_rx legacy_eapol_rx
#include "eapol-before.h"
#undef mt6797_eapol_rx

static void equivalent(unsigned char *p, size_t n)
{
 struct mt6797_eapol_rx now, before;
 struct legacy_eapol_rx old;
 memset(&now,0xa5,sizeof(now));memcpy(&before,&now,sizeof(now));memset(&old,0xa5,sizeof(old));
 bool a=mt6797_eapol_rx(p,n,40,own,ap,&now);
 bool b=legacy_eapol_rx(p,n,40,own,ap,&old);
 assert(a==b);
 if(!a)assert(!memcmp(&now,&before,sizeof(now)));
 else {
  assert(now.prefix_bytes==old.prefix_bytes&&now.offset==old.offset&&now.bytes==old.bytes);
  assert(now.signal_valid==old.signal_valid&&now.signal_dbm==old.signal_dbm&&now.bss_index==old.bss_index);
  assert(!memcmp(now.prefix,old.prefix,sizeof(now.prefix)));
 }
}
int main(void)
{
 assert(!existing_decoder_regression());
 unsigned char *p=malloc(4096);assert(p);
 size_t n=fixture(p,8,true,false,56);
 struct mt6797_eapol_rx out;
 assert(mt6797_eapol_rx_gate(p,n,40,own,ap,&out)==MT6797_EAPOL_OK);
 assert(mt6797_eapol_candidate(p,n)&&mt6797_eapol_rxd_bytes(p,n)==32);
 struct {size_t at;unsigned char value;enum mt6797_eapol_gate gate;} cases[]={
  {7,8,MT6797_EAPOL_BSS},{8,2,MT6797_EAPOL_FORMAT},
  {9,4,MT6797_EAPOL_SECURITY},{10,1,MT6797_EAPOL_PREFIX},
  {4,3,MT6797_EAPOL_WLAN_MATCH},{5,41,MT6797_EAPOL_CHANNEL},
  {7,0x3d,MT6797_EAPOL_MSDU_FORMAT}
 };
 for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  unsigned char keep=p[cases[i].at];p[cases[i].at]=cases[i].value;
  assert(mt6797_eapol_rx_gate(p,n,40,own,ap,&out)==cases[i].gate);
  assert(mt6797_eapol_candidate(p,n));equivalent(p,n);p[cases[i].at]=keep;
 }
 for(size_t i=0;i<n;i++)for(unsigned int bit=0;bit<8;bit++){
  p[i]^=1U<<bit;equivalent(p,n);p[i]^=1U<<bit;
 }
 for(size_t cut=0;cut<n;cut++){
  unsigned char *shortp=malloc(cut?cut:1);assert(shortp);memcpy(shortp,p,cut);
  if(cut>=2)put16(shortp,cut);
  equivalent(shortp,cut);assert(mt6797_eapol_rxd_bytes(shortp,cut)<=cut);
  (void)mt6797_eapol_candidate(shortp,cut);free(shortp);
 }
 n=fixture(p,0,false,false,0);
 assert(mt6797_eapol_rxd_bytes(p,n)==16&&mt6797_eapol_candidate(p,n));
 assert(mt6797_eapol_rx_gate(p,n,40,own,ap,&out)==MT6797_EAPOL_OK);
 p[payload_at+1]=0;assert(!mt6797_eapol_rx(p,n,40,own,ap,&out));
 assert(mt6797_eapol_rx_gate(p,n,40,own,ap,&out)==MT6797_EAPOL_EAPOL_TYPE);
 free(p);puts("EAPOL admission reasons, body/no-copy gates, descriptor geometry and before/after mutation equivalence: PASS");return 0;
}
