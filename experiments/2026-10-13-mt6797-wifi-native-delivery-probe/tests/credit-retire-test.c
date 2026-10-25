// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for the credit-retire proposal's header changes: the data
 * descriptor without the MCU status report (no PID, no report; the PID rule
 * inverted without a report) and the slot helpers that retire frames in
 * submission order as the page credits cover them.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "test-compat.h"
#include "join-tx.h"
#include "join-depth.h"

int main(void)
{
	unsigned char frame[64] = {0}, d[MT6797_JOIN_TX_DESC_BYTES];
	unsigned int pages;
	struct mt6797_data_slots s;
	struct mt6797_data_owner copy;
	int a = 1, b = 2, c = 3, r = 4;

	frame[0] = 0x02; frame[12] = 0x08; frame[13] = 0x00;
	/* reported: PID and the report together; unreported: neither; mixed forms refused */
	assert(mt6797_join_tx_data_descriptor(frame, sizeof(frame), 1, 5, 500, 3, d, &pages));
	assert(d[20] == 5 && d[21] == 2);
	assert(mt6797_join_tx_data_descriptor_report(frame, sizeof(frame), 1, 0, false, 500, 3, d, &pages));
	assert(d[20] == 0 && d[21] == 0 && pages == 1);
	assert(d[26] == ((MT6797_DATA_FIXED_RATE_CODE << 2) & 255));
	assert(!mt6797_join_tx_data_descriptor_report(frame, sizeof(frame), 1, 5, false, 500, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor_report(frame, sizeof(frame), 1, 0, true, 500, 3, d, &pages));

	/* slots: three credit frames (12, 12, 1 pages) and one reported frame */
	memset(&s, 0, sizeof(s));
	assert(mt6797_data_put_credit(&s, 10, &a, 1000, 12, 1, 100));
	assert(mt6797_data_put_credit(&s, 11, &b, 1000, 12, 2, 200));
	assert(mt6797_data_put(&s, 12, &r, 1000));			/* reported: zero pages */
	assert(mt6797_data_put_credit(&s, 13, &c, 1000, 1, 3, 300));
	assert(!mt6797_data_put_credit(&s, 14, &a, 1000, 0, 4, 400));	/* zero pages refused */
	assert(s.count == 4 && mt6797_data_credit_outstanding(&s));
	/* credits short of the oldest frame retire nothing; the order is by ordinal, not slot */
	assert(mt6797_data_take_oldest(&s, 11, &copy) == NULL && s.count == 4);
	assert(mt6797_data_take_oldest(&s, 12, &copy) == &a && copy.pid == 10 && copy.pages == 12 && copy.submitted == 100);
	assert(mt6797_data_take_oldest(&s, 12, &copy) == &b && copy.pid == 11);
	/* the reported frame is never retired by credits */
	assert(mt6797_data_take_oldest(&s, 100, &copy) == &c && copy.pid == 13 && copy.pages == 1);
	assert(mt6797_data_take_oldest(&s, 100, &copy) == NULL);
	assert(!mt6797_data_credit_outstanding(&s) && s.count == 1);
	assert(mt6797_data_take(&s, 12) == &r && s.count == 0);
	/* a later submission with a lower ordinal value never happens; equal pages at the exact credit */
	assert(mt6797_data_put_credit(&s, 20, &a, 1000, 3, 7, 700));
	assert(mt6797_data_take_oldest(&s, 2, &copy) == NULL);
	assert(mt6797_data_take_oldest(&s, 3, &copy) == &a);
	printf("credit-retire-test: PASS (descriptor without the report; slots retire in order as credits cover them)\n");
	return 0;
}
