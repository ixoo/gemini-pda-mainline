/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define NSEC_PER_SEC 1000000000ULL
#define GFP_KERNEL 0
#define MT6797_HIF_RX_MAX_PACKET 2352U
#define MT6797_BOOT_EVENT_MAX 8U
#define MT6797_BOOT_DEBUG_EVENT 0x27U
#define MT6797_BOOT_SLEEPY_EVENT 0x07U
#define MT6797_HIF_WHLPCR 4U
#define MT6797_HIF_DRIVER_OWN (1U << 8)
struct device { int unused; };
static void dev_info(struct device *dev, const char *format, ...)
 __attribute__((format(printf, 2, 3)));
static void dev_info(struct device *dev, const char *format, ...) {(void)dev;(void)format;}
struct mt6797_consys { void *fw_hif; };
struct mt6797_hif_rx_result {
 u32 pre_wrplr, post_wrplr;
 size_t staging_bytes, logical_bytes;
 unsigned int packet_type;
 bool pre_valid, rx_setup, rx_complete, post_valid;
};
static struct {
 unsigned int count, received, own_reads, fail_read;
 u32 ownership;
 int transport_error;
 struct {size_t len; unsigned int type; u8 id, state; u32 post;} packets[8];
} fake;
static u64 ktime_get_ns(void) {return 1000;}
static void *kmalloc(size_t bytes, int flags) {(void)flags; return malloc(bytes);}
static void kfree_sensitive(void *data) {free(data);}
static int mt6797_hif_receive_packet(void *hif, unsigned int port, u64 deadline,
 u8 *buffer, size_t capacity, struct mt6797_hif_rx_result *rx)
{
 assert(hif == &fake && port == 0 && deadline == 1000001000ULL);
 assert(capacity == 2352);
 *rx=(struct mt6797_hif_rx_result){0};
 unsigned int n=fake.received++;
 if(fake.transport_error) return fake.transport_error;
 rx->pre_valid=true;
 if(n==fake.count) return -EAGAIN;
 assert(n<fake.count);
 memset(buffer,0,capacity);
 rx->logical_bytes=fake.packets[n].len; rx->packet_type=fake.packets[n].type;
 rx->rx_setup=rx->rx_complete=rx->post_valid=true;
 rx->post_wrplr=fake.packets[n].post;
 if(rx->logical_bytes>=8) buffer[4]=fake.packets[n].id;
 if(rx->logical_bytes>=12) buffer[8]=fake.packets[n].state;
 return 0;
}
static int mt6797_hif_read32(void *hif, unsigned int reg, u64 deadline, u32 *value)
{
 assert(hif==&fake && reg==4 && deadline==1000001000ULL);
 fake.own_reads++;
 if(fake.own_reads==fake.fail_read) return -EIO;
 *value=fake.ownership;
 return 0;
}
#include "boot-drain-under-test.inc"
static int run(void) {struct device dev={0}; struct mt6797_consys owner={&fake}; return mt6797_consys_drain_boot_events(&dev,&owner);}
static void reset(unsigned int count)
{
 memset(&fake,0,sizeof(fake));fake.count=count;fake.ownership=0x100;
 for(unsigned int i=0;i<count;i++) {
  fake.packets[i].len=12;fake.packets[i].type=0xe000;fake.packets[i].id=7;
  fake.packets[i].state=1;fake.packets[i].post=i+1<count?12:0;
 }
}
int main(void)
{
 for(unsigned int state=0;state<256;state++) {
  reset(1);fake.packets[0].state=state;assert(run()==(state<=1?0:-EPROTO));
  assert(fake.received==1 && fake.own_reads==(state<=1?1U:0U));
 }
 for(unsigned int length=0;length<=16;length++) {
  reset(1);fake.packets[0].len=length;assert(run()==(length==12?0:-EPROTO));
  assert(fake.own_reads==(length==12?1U:0U));
 }
 for(unsigned int event=0;event<256;event++) {
  reset(1);fake.packets[0].id=event;assert(run()==((event==7||event==0x27)?0:-EPROTO));
  assert(fake.own_reads==(event==7?1U:0U));
 }
 reset(1);fake.packets[0].type=0xe001;assert(run()==-EPROTO && !fake.own_reads);
 reset(3);fake.packets[0].id=fake.packets[1].id=0x27;
 assert(!run() && fake.received==3 && fake.own_reads==1);
 reset(1);fake.ownership=0;assert(run()==-EACCES && fake.received==1 && fake.own_reads==1);
 reset(2);fake.fail_read=1;assert(run()==-EIO && fake.received==1 && fake.own_reads==1);
 reset(2);fake.fail_read=2;assert(run()==-EIO && fake.received==2 && fake.own_reads==2);
 reset(1);fake.transport_error=-ETIMEDOUT;assert(run()==-ETIMEDOUT && fake.received==1 && !fake.own_reads);
 reset(1);fake.packets[0].post=0x000c0000;assert(run()==-EBUSY && fake.received==1);
 reset(8);assert(!run() && fake.received==8 && fake.own_reads==8);
 reset(8);fake.packets[7].post=12;assert(run()==-E2BIG && fake.received==8 && fake.own_reads==8);
 reset(1);fake.packets[0].id=0x27;fake.packets[0].post=12;
 assert(!run() && fake.received==2 && !fake.own_reads);
 puts("actual boot-drain control flow: states, lengths, IDs, ownership, faults and finite packet budget pass");
 return 0;
}
