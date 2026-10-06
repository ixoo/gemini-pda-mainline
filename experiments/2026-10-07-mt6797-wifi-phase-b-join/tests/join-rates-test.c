/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <join-commands.h>
int main(void)
{
 unsigned desired, basic;
 for(unsigned support=0; support<256; support++) {
  for(unsigned mandatory=0; mandatory<256; mandatory++) {
   desired=0xfeed; basic=0xbeef;
   bool valid=support && mandatory && (support&1) && !(mandatory&~support);
   assert(mt6797_join_legacy_rates(support,mandatory,&desired,&basic)==valid);
   if(valid) { assert(desired==(support<<6)); assert(basic==(mandatory<<6)); }
   else { assert(desired==0xfeed && basic==0xbeef); }
  }
 }
 for(unsigned bit=8;bit<32;bit++) {
  desired=0xfeed; basic=0xbeef;
  assert(!mt6797_join_legacy_rates(1U|(1U<<bit),1,&desired,&basic));
  assert(!mt6797_join_legacy_rates(1,1U|(1U<<bit),&desired,&basic));
  assert(desired==0xfeed && basic==0xbeef);
 }
 assert(!mt6797_join_legacy_rates(255,1,NULL,&basic));
 assert(!mt6797_join_legacy_rates(255,1,&desired,NULL));
 return 0;
}
