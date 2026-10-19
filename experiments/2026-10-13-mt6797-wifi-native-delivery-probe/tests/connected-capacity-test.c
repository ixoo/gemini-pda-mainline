/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stddef.h>
#include <limits.h>
#include <stdio.h>
#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#include "native-diag.h"
#include "actual-packet-cap.inc"
int main(void)
{
 struct mt6797_native_diag_budget b = {.elapsed_ms=UINT_MAX};
 unsigned int *v[3]={&b.total_rx,&b.native_rx,&b.bytes};
 unsigned int limits[3]={32768,8192,16U*1024*1024};
 unsigned int i;
 assert(MT6797_CCMP_DIAG_RX_MAX==32768 && MT6797_CCMP_DIAG_CHECKED_MAX==8192);
 assert(MT6797_CCMP_DIAG_BYTES_MAX==16U*1024*1024 && MT6797_JOIN_MAX_PACKETS==65536);
 assert(MT6797_NATIVE_DIAG_RX_MAX==512 && MT6797_NATIVE_DIAG_NATIVE_MAX==64);
 assert(MT6797_NATIVE_DIAG_BYTES_MAX==1024U*1024 && MT6797_NATIVE_DIAG_WALL_MS==60000);
 assert(mt6797_ccmp_diag_budget_step(&b)==MT6797_NATIVE_DIAG_CONTINUE);
 for(i=0;i<3;i++) {
  *v[i]=limits[i]-1;assert(mt6797_ccmp_diag_budget_step(&b)==MT6797_NATIVE_DIAG_CONTINUE);
  *v[i]=limits[i];assert(mt6797_ccmp_diag_budget_step(&b)==MT6797_NATIVE_DIAG_STOP);
  *v[i]=limits[i]+1;assert(mt6797_ccmp_diag_budget_step(&b)==MT6797_NATIVE_DIAG_STOP);
  *v[i]=0;
 }
 assert(mt6797_ccmp_diag_budget_step(NULL)==MT6797_NATIVE_DIAG_STOP);
 assert(mt6797_native_diag_retire_step(63,256U*1024-1,749)==MT6797_NATIVE_DIAG_CONTINUE);
 assert(mt6797_native_diag_retire_step(64,0,0)==MT6797_NATIVE_DIAG_STOP);
 assert(mt6797_native_diag_retire_step(0,256U*1024,0)==MT6797_NATIVE_DIAG_STOP);
 assert(mt6797_native_diag_retire_step(0,0,750)==MT6797_NATIVE_DIAG_STOP);
 puts("connected capacity selected limits and unchanged native/drain limits PASS");
 return 0;
}
