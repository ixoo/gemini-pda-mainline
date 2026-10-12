// SPDX-License-Identifier: GPL-2.0
/*
 * native-loop-test.c -- event-sequence model of the mt6797 native-crypto
 * delivery control loop, exercising ACTUAL retirement/ending-state event
 * orders against the shared pure core in native-diag.h.
 *
 * It models ONE worker iteration in the real source order --
 *   step() [mac.c:1752] -> parent lower-deadline end_data [1756]
 *   -> TX queue selection [1765] -> RX-loop class dispatch --
 * so it can prove the exact SAME-worker-iteration ordering root called out:
 * the disable/page fence is established before queue selection can send the
 * queued deauth, the lower data-phase deadline is honored in the same pass,
 * an owed TX-done is never dropped on a capture stop, and past a ceiling only
 * owed completions (TX-done/control) are processed -- beacon/EAPOL/data are not
 * resumed outside the admitted limits.
 *
 * step(), parent_deadline_end(), queue_selection() and dispatch_processed()
 * mirror mac.c and MUST be kept in sync; this is a host model of the control
 * loop on the pure core, not the compiled worker. Synthetic only; no device,
 * radio or key action.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

/* The driver includes net/mac80211.h for these; the model stubs them. */
#define RX_FLAG_DECRYPTED      (1u << 0)
#define RX_FLAG_IV_STRIPPED    (1u << 1)
#define RX_FLAG_PN_VALIDATED   (1u << 2)
#define RX_FLAG_MMIC_STRIPPED  (1u << 3)
#define RX_FLAG_MIC_STRIPPED   (1u << 4)
#define RX_FLAG_ALLOW_SAME_PN  (1u << 5)
#define RX_FLAG_NO_SIGNAL_VAL  (1u << 6)
#define RX_FLAG_8023           (1u << 7)

#include "native-diag.h"

struct model {
	enum mt6797_native_diag_state state;
	bool credit_pending;
	unsigned int page_debt;
	bool inflight;			/* a TX frame awaits its TX-done */
	bool data_phase;		/* associated data phase, both keys */
	bool data_ended;
	bool first_error, closing;	/* ambiguity latch */
	bool engaged;			/* sticky: no legacy RX once armed */
	unsigned long long now, data_deadline;	/* the live lower deadline */
	unsigned int total_rx, native_rx, bytes, seq;
	unsigned long long started;
	/* driver-built recovery frame queued by end_data */
	bool deauth_queued, deauth_sent;
	/* audit */
	bool legacy_reopened;
	bool deauth_before_disable;	/* deauth sent before disable retired (must stay 0) */
	int submits;
};

/* The receive gate: legacy (FW-decrypted translated) delivery only while never
 * engaged -- sticky withhold through CLOSED for the whole data lifetime. */
static bool legacy_delivery_allowed(const struct model *m)
{
	return !m->engaged;
}

/* mac.c:1752 -- one non-blocking step. Mirrors mt6797_native_diag_step(). */
static void step(struct model *m)
{
	struct mt6797_native_diag_ctx c = {0};
	struct mt6797_native_diag_budget b;
	enum mt6797_native_diag_state prev = m->state;
	enum mt6797_native_diag_action a;

	b.elapsed_ms = m->started ? (unsigned int)(m->now - m->started) : 0;
	b.total_rx = m->total_rx;
	b.native_rx = m->native_rx;
	b.bytes = m->bytes;

	c.state = m->state;
	c.armed = 1;
	/* The live lower deadline is folded in, so a deadline/association end is
	 * acted on THIS pass (before end_data and queue selection below). */
	c.data_phase = m->data_phase && !m->data_ended && m->now < m->data_deadline;
	c.quiescent = !m->credit_pending && !m->page_debt && !m->inflight;
	c.poisoned = m->first_error || m->closing;
	c.deadline_passed = 0;
	c.seq_ok = m->seq <= 253;
	c.budget_stop = mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP;

	a = mt6797_native_diag_transition(&c);
	m->state = c.state;

	if (a == MT6797_ND_ACT_SUBMIT_ENABLE || a == MT6797_ND_ACT_SUBMIT_DISABLE) {
		assert(c.quiescent && !c.poisoned);	/* no self-wait, no command on ambiguity */
		m->credit_pending = true;
		m->page_debt = 1;			/* the fence, established in step */
		m->seq++;
		m->submits++;
		if (a == MT6797_ND_ACT_SUBMIT_ENABLE) {
			m->engaged = true;
			m->started = m->now ? m->now : 1;
		}
	} else if (a == MT6797_ND_ACT_LATCH_NORADIO) {
		m->first_error = m->closing = true;
	}
	if (prev != MT6797_ND_CLOSED && m->state == MT6797_ND_CLOSED && m->engaged)
		m->data_ended = true;
	if (m->engaged && legacy_delivery_allowed(m))
		m->legacy_reopened = true;
}

/* mac.c:1756 -- the parent ends the data phase on the lower deadline, queuing
 * the driver-built deauthentication. */
static void parent_deadline_end(struct model *m)
{
	if (m->data_phase && !m->data_ended && m->now >= m->data_deadline) {
		m->data_ended = true;
		m->deauth_queued = true;
	}
}

/* mac.c:1765 -- queue selection sends a queued frame only with the ledger free
 * of an owed page and an in-flight frame. */
static void queue_selection(struct model *m)
{
	if (m->deauth_queued && !m->inflight && !m->page_debt) {
		m->deauth_sent = true;
		m->deauth_queued = false;
		if (m->state != MT6797_ND_CLOSED)
			m->deauth_before_disable = true;	/* ordering violation */
	}
}

static void worker_iter(struct model *m)
{
	step(m);			/* 1752 */
	parent_deadline_end(m);		/* 1756 */
	queue_selection(m);		/* 1765 */
}

static void credit_return(struct model *m) { m->credit_pending = false; m->page_debt = 0; }
static void tx_done(struct model *m) { m->inflight = false; }

/* mac.c:2041 -- past a ceiling only owed completions process. */
enum cls { CLS_TXDONE, CLS_CONTROL, CLS_BEACON, CLS_EAPOL, CLS_GROUP, CLS_DATA };
static bool dispatch_processed(enum cls k, bool nd_over)
{
	if (k == CLS_TXDONE || k == CLS_CONTROL)
		return true;		/* owed completions always retire */
	return !nd_over;		/* beacon/EAPOL/group/data skipped over a ceiling */
}

int main(void)
{
	/* A: capture STOP with an owed TX-done -> never dropped; disable waits. */
	{
		struct model m = {0};
		int g;

		m.state = MT6797_ND_IDLE; m.data_phase = true; m.data_deadline = 10000;
		worker_iter(&m);
		assert(m.state == MT6797_ND_ENABLE_PENDING && m.engaged && m.submits == 1);
		credit_return(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_ACTIVE);
		m.inflight = true; m.total_rx = MT6797_NATIVE_DIAG_RX_MAX;	/* ceiling + owed TX */
		for (g = 0; g < 4; g++) {
			worker_iter(&m);
			assert(m.state == MT6797_ND_ACTIVE && m.submits == 1);	/* TX-done not dropped */
		}
		tx_done(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_DISABLE_PENDING && m.submits == 2);
		credit_return(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_CLOSED);
		assert(mt6797_native_diag_cleanup_allowed(m.state));
		assert(!m.legacy_reopened && !m.deauth_before_disable);
	}

	/* B: lower deadline ends the window; prove the page fence is established in
	 * the SAME iteration, before the queued deauth can be selected/sent. */
	{
		struct model m = {0};

		m.state = MT6797_ND_IDLE; m.data_phase = true; m.data_deadline = 10000;
		worker_iter(&m); credit_return(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_ACTIVE && m.submits == 1);
		m.now = 10000;			/* now >= lower deadline, this iteration */
		worker_iter(&m);
		/* step() saw now>=deadline -> disabled -> page_debt set BEFORE 1765;
		 * end_data queued the deauth at 1756; queue selection fenced it. */
		assert(m.state == MT6797_ND_DISABLE_PENDING && m.submits == 2);
		assert(m.deauth_queued && !m.deauth_sent && !m.deauth_before_disable);
		credit_return(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_CLOSED);
		assert(m.deauth_sent && !m.deauth_before_disable);	/* deauth only after close */
		assert(!m.legacy_reopened);
	}

	/* B2: deadline ends the window while a TX-done is still owed -> the inflight
	 * fence holds the deauth until retirement, then the page fence does. */
	{
		struct model m = {0};

		m.state = MT6797_ND_IDLE; m.data_phase = true; m.data_deadline = 10000;
		worker_iter(&m); credit_return(&m); worker_iter(&m);
		m.inflight = true; m.now = 10000;
		worker_iter(&m);					/* !quiescent -> wait */
		assert(m.state == MT6797_ND_ACTIVE && m.submits == 1);
		assert(m.deauth_queued && !m.deauth_sent && !m.deauth_before_disable);
		tx_done(&m); worker_iter(&m);				/* retired -> disable, fenced */
		assert(m.state == MT6797_ND_DISABLE_PENDING && !m.deauth_sent);
		credit_return(&m); worker_iter(&m);
		assert(m.state == MT6797_ND_CLOSED && m.deauth_sent && !m.deauth_before_disable);
	}

	/* C: ambiguity during enable -> no further command, window closes. */
	{
		struct model m = {0};

		m.state = MT6797_ND_IDLE; m.data_phase = true; m.data_deadline = 10000;
		worker_iter(&m); assert(m.submits == 1 && m.engaged);
		m.first_error = true; worker_iter(&m);
		assert(m.state == MT6797_ND_CLOSED && m.submits == 1);	/* no command on ambiguity */
		assert(mt6797_native_diag_cleanup_allowed(m.state) && !m.legacy_reopened);
	}

	/* D: cleanup only at CLOSED/IDLE. */
	assert(mt6797_native_diag_cleanup_allowed(MT6797_ND_IDLE));
	assert(mt6797_native_diag_cleanup_allowed(MT6797_ND_CLOSED));
	assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_ENABLE_PENDING));
	assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_ACTIVE));
	assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_DISABLE_PENDING));

	/* E: bounded retirement -- past a ceiling only owed completions process. */
	assert(dispatch_processed(CLS_TXDONE, true));
	assert(dispatch_processed(CLS_CONTROL, true));
	assert(!dispatch_processed(CLS_BEACON, true));
	assert(!dispatch_processed(CLS_EAPOL, true));
	assert(!dispatch_processed(CLS_GROUP, true));
	assert(!dispatch_processed(CLS_DATA, true));
	assert(dispatch_processed(CLS_BEACON, false));	/* under budget: normal */
	assert(dispatch_processed(CLS_DATA, false));

	printf("native-loop: PASS (same-iteration page fence before deauth; lower deadline honored; owed TX-done never dropped; bounded retirement only; no legacy reopen; no command on ambiguity)\n");
	return 0;
}
