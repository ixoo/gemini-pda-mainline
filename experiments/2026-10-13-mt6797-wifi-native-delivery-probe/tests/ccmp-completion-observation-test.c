// SPDX-License-Identifier: GPL-2.0-only
/* Compiles the actual observation helpers; no transport or device exists. */
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t u32;
typedef unsigned long long u64;
typedef uint8_t u8;
static u64 now_ns;
static unsigned int lines;
static char output[3][1024];

static u64 ktime_get_ns(void) { return ++now_ns; }
static void record(const char *format, ...) __attribute__((format(printf, 1, 2)));
static void record(const char *format, ...)
{
	va_list args;
	assert(lines < 3);
	va_start(args, format);
	assert(vsnprintf(output[lines++], sizeof(output[0]), format, args) > 0);
	va_end(args);
}
#define dev_info(device, ...) record(__VA_ARGS__)

struct mt6797_hif_rx_result {
	bool pre_valid;
	u32 pre_wrplr;
	unsigned int packet_type;
};
struct mt6797_hif_tx_status { u32 whcr, whisr; };
#include "observation-struct.h"
struct mt6797_mac {
	struct mt6797_ccmp_observation ccmp_observation;
	void *join_inflight;
	u8 join_pid;
	u64 join_frame_deadline;
};
#include "observation-functions.h"

int main(void)
{
	struct mt6797_mac mac = {0};
	struct mt6797_ccmp_observation before, *o = &mac.ccmp_observation;
	struct mt6797_hif_tx_status guard = { .whcr = 0x1234, .whisr = 5 };
	struct mt6797_hif_rx_result rx = {
		.pre_valid = true, .pre_wrplr = 24U << 16, .packet_type = 0xe000,
	};

	/* Default-off admission: no state, clock or output changes. */
	before = *o;
	mt6797_ccmp_observe_guard(o, &guard);
	mt6797_ccmp_observe_rx(o, 0, -11, &rx);
	mt6797_ccmp_observe_terminal(&mac);
	assert(!memcmp(o, &before, sizeof(*o)) && !now_ns && !lines);
	o->active = true;
	mt6797_ccmp_observe_guard(o, &guard);
	assert(o->guard_valid && o->whcr == 0x1234 && o->whisr == 5);
	assert(o->guard_return_ns == 1);
	/* Empty selected half with advertised opposite work is retained honestly. */
	mt6797_ccmp_observe_rx(o, 0, -11, &rx);
	assert(o->port[0].attempts == 1 && o->port[0].opposite == 1);
	assert(!o->port[0].packets && !o->port[0].type7);
	assert(o->port[0].pre_valid && o->port[0].status == -11);
	/* Both ports, accepted control and data; metadata never accepts a packet. */
	mt6797_ccmp_observe_rx(o, 1, 0, &rx);
	assert(o->port[1].packets == 1 && o->port[1].type7 == 1);
	assert(!o->port[1].opposite);
	rx.pre_wrplr = 76;
	rx.packet_type = 0x4000;
	mt6797_ccmp_observe_rx(o, 0, 0, &rx);
	assert(o->port[0].packets == 1 && !o->port[0].type7);
	/* A length refusal counts an attempt, never a published packet/type. */
	mt6797_ccmp_observe_rx(o, 0, -71, &rx);
	assert(o->port[0].attempts == 3 && o->port[0].packets == 1);
	/* Invalid pre metadata clears the previous value, avoiding stale evidence. */
	rx.pre_valid = false;
	rx.pre_wrplr = 0xffffffff;
	mt6797_ccmp_observe_rx(o, 1, -110, &rx);
	assert(!o->port[1].pre_valid && !o->port[1].pre_wrplr);
	assert(o->port[1].packets == 1 && o->port[1].type7 == 1);
	before = *o;
	mt6797_ccmp_observe_rx(o, 2, 0, &rx);
	assert(!memcmp(o, &before, sizeof(*o)));
	mac.join_inflight = &mac;
	mac.join_pid = o->submit_pid = 6;
	o->submit_return_ns = 100;
	mac.join_frame_deadline = 750000100;
	mt6797_ccmp_observe_terminal(&mac);
	assert(lines == 3 && o->reported);
	assert(strstr(output[0], "inflight=1 pid=6 submit_pid=6 submit_return_ns=100"));
	assert(strstr(output[0], "frame_deadline_ns=750000100"));
	assert(strstr(output[0], "guard_return_ns=1 whcr=0x00001234 whisr=0x00000005"));
	assert(strstr(output[1], "port=0 attempts=3 packets=1 type7=0 opposite=1 status=-71"));
	assert(strstr(output[2], "port=1 attempts=2 packets=1 type7=1 opposite=0 status=-110"));
	/* Terminal state is frozen, including acquisition times and output count. */
	before = *o;
	mt6797_ccmp_observe_guard(o, &guard);
	mt6797_ccmp_observe_rx(o, 0, 0, &rx);
	mt6797_ccmp_observe_terminal(&mac);
	assert(!memcmp(o, &before, sizeof(*o)) && lines == 3);
	/* Healthy terminal with no guard sample: absent stays invalid/zero. */
	memset(&mac, 0, sizeof(mac));
	lines = 0;
	o->active = true;
	mt6797_ccmp_observe_terminal(&mac);
	assert(lines == 3 && strstr(output[0], "inflight=0 pid=0"));
	assert(strstr(output[0], "guard_valid=0 guard_return_ns=0"));
	assert(strstr(output[1], "attempts=0 packets=0 type7=0 opposite=0"));
	puts("CCMP completion observation: pass");
	return 0;
}
