/* SPDX-License-Identifier: GPL-2.0-only */
/* Compile the exact MAC receive-routing block; no packet decoding or firmware is modeled. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define MT6797_ND_CLOSED 4
struct mt6797_hif_rx_result { unsigned int selected_port; bool selected_port_valid; };
struct mt6797_mac {
	void *hif;
	unsigned char join_packet[8];
	bool native_diag_engaged;
	unsigned int native_diag_state, ccmp_observation;
};
bool ccmp_stable_epoch;
unsigned int requested[2], selected_calls, observed[2], selected_port;
int mt6797_hif_receive_selected(void *hif, unsigned long long deadline,
		unsigned char *buffer, size_t capacity, struct mt6797_hif_rx_result *r)
{
	(void)hif; (void)deadline; (void)buffer; (void)capacity;
	selected_calls++;
	*r = (struct mt6797_hif_rx_result){selected_port, true};
	return 0;
}
int mt6797_hif_receive_runtime_packet(void *hif, unsigned int port,
		unsigned long long deadline, unsigned char *buffer,
		size_t capacity, struct mt6797_hif_rx_result *r)
{
	(void)hif; (void)deadline; (void)buffer; (void)capacity;
	assert(port < 2);
	requested[port]++;
	*r = (struct mt6797_hif_rx_result){0};
	return 0;
}
void mt6797_ccmp_observe_rx(unsigned int *o, unsigned int port, int ret,
			  const struct mt6797_hif_rx_result *r)
{
	(void)o; (void)r;
	assert(port < 2 && !ret);
	observed[port]++;
}
static void run(bool enabled, bool engaged, unsigned int state, unsigned int chosen)
{
	struct mt6797_mac m = { .native_diag_engaged = engaged, .native_diag_state = state };
	struct mt6797_mac *mac = &m;
	struct mt6797_hif_rx_result rx;
	unsigned long long deadline = 1000;
	unsigned int branch = 0;
	int ret = 0;
	bool active = false;

	ccmp_stable_epoch = enabled;
	selected_port = chosen;
	memset(requested, 0, sizeof(requested));
	memset(observed, 0, sizeof(observed));
	selected_calls = 0;
	for (unsigned int n = 0; n < 8; n++) {
		for (unsigned int port = 0; port < 2; port++) {
			unsigned int rx_port = port;

#include "closed-selected-route.inc"
			(void)rx_port;
		}
	}
#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH
	active = enabled && engaged && state == MT6797_ND_CLOSED;
#endif
	assert(branch == 4 && !ret);
	if (active) {
		assert(selected_calls == 8 && !requested[0] && !requested[1]);
		assert(observed[chosen] == 8 && !observed[1 - chosen]);
	} else {
		assert(!selected_calls && requested[0] == 8 && requested[1] == 8);
#ifdef CONFIG_MT6797_CCMP_STABLE_EPOCH
		assert(observed[0] == 8 && observed[1] == 8);
#else
		assert(!observed[0] && !observed[1]);
#endif
	}
}
int main(void)
{
	for (unsigned int e = 0; e < 2; e++)
		for (unsigned int g = 0; g < 2; g++)
			for (unsigned int s = 0; s < 5; s++)
				for (unsigned int p = 0; p < 2; p++)
					run(e, g, s, p);
	puts("actual MAC routing: 80 flag/state/port cases PASS");
	return 0;
}
