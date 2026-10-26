/* SPDX-License-Identifier: GPL-2.0-only */
/* The actual EAPOL-Key receive admission and its refusal name (0305): the
 * first EAPOL-Key on the station tag before the station activation. Built by
 * run-early-m1-test.py, once on the parent (-DPARENT: the refusal of boots AA
 * and AA3 reproduced) and once on the change. No HIF.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

enum { MT6797_EAPOL_OK, MT6797_EAPOL_SHAPE };
static const char *mt6797_eapol_gate_name(int gate) { return gate ? "shape" : "ok"; }
struct mt6797_mac {
	bool join_assoc_received, join_deauth_done, join_cleanup_done;
	bool join_bss_configured, join_sta_active;
	unsigned int join_assoc_status, join_eapol_seen;
};
struct mt6797_eapol { unsigned int bss_index; };
#include "early-m1-functions.inc"

static struct mt6797_mac m;

/* After a status-0 association response, before the BSS credit and the
 * station activation: boot AA3 at 14.2267 s.
 */
static void associated(void)
{
	memset(&m, 0, sizeof(m));
	m.join_assoc_received = true;
}

static void refused(unsigned int tag, int g, const char *name)
{
	struct mt6797_eapol e = { tag };

	assert(!admitted(&m, g, e));
	assert(!strcmp(refusal(&m, g), name));
}

int main(void)
{
	struct mt6797_eapol one = { 1 };

	associated();
#ifdef PARENT
	refused(1, MT6797_EAPOL_OK, "bss-interval");
	m.join_sta_active = true;
	assert(admitted(&m, MT6797_EAPOL_OK, one));
	printf("parent: message 1 on tag 1 before the activation refused at bss-interval, as in boots AA and AA3\n");
#else
	/* tag 1 from the accepted association on, activated or not */
	assert(admitted(&m, MT6797_EAPOL_OK, one));
	m.join_bss_configured = true;
	assert(admitted(&m, MT6797_EAPOL_OK, one));
	m.join_sta_active = true;
	assert(admitted(&m, MT6797_EAPOL_OK, one));
	/* the delivery cap holds */
	m.join_eapol_seen = 2;
	refused(1, MT6797_EAPOL_OK, "delivery-cap");
	/* no association, a refused association, deauthentication, cleanup */
	memset(&m, 0, sizeof(m));
	refused(1, MT6797_EAPOL_OK, "association");
	associated(); m.join_assoc_status = 17;
	refused(1, MT6797_EAPOL_OK, "association");
	associated(); m.join_deauth_done = true;
	refused(1, MT6797_EAPOL_OK, "deauth-ended");
	associated(); m.join_cleanup_done = true;
	refused(1, MT6797_EAPOL_OK, "cleanup-done");
	/* tag 15 keeps its interval; other tags and shapes stay refused */
	associated();
	assert(admitted(&m, MT6797_EAPOL_OK, (struct mt6797_eapol){ 15 }));
	m.join_bss_configured = true;
	refused(15, MT6797_EAPOL_OK, "bss-interval");
	refused(0, MT6797_EAPOL_OK, "bss-interval");
	refused(7, MT6797_EAPOL_OK, "bss-interval");
	refused(1, MT6797_EAPOL_SHAPE, "shape");
	printf("early M1: PASS; tag 1 admitted from the accepted association on, the cap, the association, deauthentication and cleanup conditions, tag 15's interval and every other tag unchanged\n");
#endif
	return 0;
}
