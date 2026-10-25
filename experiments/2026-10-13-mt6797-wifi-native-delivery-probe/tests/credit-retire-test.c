// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for the credit-retire proposal's header changes (0278, 0281):
 * the data descriptor without the MCU status report (no PID, no report; the
 * PID rule inverted without a report), the slot helpers that cover frames in
 * submission order as the page credits reach them, a sampled frame held for
 * its report, and a placeholder that keeps a sampled frame's place when its
 * report arrives before its credits.
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
	unsigned int pages, i;
	struct mt6797_data_slots s;
	struct mt6797_data_owner copy;
	void *f;
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

	/* slots: three credit frames (12, 12, 1 pages) and one reported frame; covered in ordinal order */
	memset(&s, 0, sizeof(s));
	assert(mt6797_data_put_credit(&s, 10, &a, 1000, 12, 1, 100));
	assert(mt6797_data_put_credit(&s, 11, &b, 1000, 12, 2, 200));
	assert(mt6797_data_put(&s, 12, &r, 1000));			/* status-report frame: zero pages */
	assert(mt6797_data_put_credit(&s, 13, &c, 1000, 1, 3, 300));
	assert(!mt6797_data_put_credit(&s, 14, &a, 1000, 0, 4, 400));	/* zero pages refused */
	assert(s.count == 4 && mt6797_data_credit_outstanding(&s) && !mt6797_data_room(&s, 1, 100));
	assert(mt6797_data_cover_oldest(&s, 11, &copy, &f) == MT6797_DATA_COVER_NONE && s.count == 4);
	assert(mt6797_data_cover_oldest(&s, 12, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &a && copy.pid == 10 && copy.pages == 12 && copy.submitted == 100);
	assert(mt6797_data_cover_oldest(&s, 12, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &b && copy.pid == 11);
	assert(mt6797_data_cover_oldest(&s, 100, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &c && copy.pid == 13 && copy.pages == 1);
	assert(mt6797_data_cover_oldest(&s, 100, &copy, &f) == MT6797_DATA_COVER_NONE);	/* the status-report frame is never covered by credits */
	assert(!mt6797_data_credit_outstanding(&s) && s.count == 1);
	assert(mt6797_data_take(&s, 12) == &r && s.count == 0 && mt6797_data_entry_free(&s));
	/* exact credit at the head; short by one is none */
	assert(mt6797_data_put_credit(&s, 20, &a, 1000, 3, 7, 700));
	assert(mt6797_data_cover_oldest(&s, 2, &copy, &f) == MT6797_DATA_COVER_NONE);
	assert(mt6797_data_cover_oldest(&s, 3, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &a && s.count == 0);

	/* a sampled frame (reported): covered in order, held for its report, out of the order once covered */
	memset(&s, 0, sizeof(s));
	assert(mt6797_data_put_credit(&s, 30, &a, 1000, 13, 1, 100));
	assert(mt6797_data_put_credit(&s, 31, &b, 1000, 13, 2, 200) && mt6797_data_mark_reported(&s, 31));
	assert(!mt6797_data_mark_reported(&s, 99));
	assert(mt6797_data_put_credit(&s, 32, &c, 1000, 13, 3, 300));
	assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &a);
	assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_HELD && copy.pid == 31 && f == NULL && s.count == 2);
	assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &c);
	assert(mt6797_data_cover_oldest(&s, 100, &copy, &f) == MT6797_DATA_COVER_NONE);
	assert(!mt6797_data_credit_outstanding(&s) && s.count == 1 && mt6797_data_find(&s, 31));
	assert(mt6797_data_take(&s, 31) == &b && s.count == 0 && mt6797_data_entry_free(&s));

	/* a report before coverage: a placeholder keeps the frame's place in the order */
	assert(mt6797_data_put_credit(&s, 40, &a, 1000, 13, 4, 400) && mt6797_data_mark_reported(&s, 40));
	assert(mt6797_data_put_credit(&s, 41, &b, 1000, 13, 5, 500));
	assert(mt6797_data_take(&s, 40) == &a && s.count == 1 && !mt6797_data_find(&s, 40));
	assert(mt6797_data_credit_outstanding(&s));
	assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_HELD && copy.ordinal == 4 && f == NULL);
	assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_RETIRE && f == &b);
	assert(!mt6797_data_credit_outstanding(&s) && s.count == 0 && mt6797_data_entry_free(&s));

	/* placeholders occupy entries: the room check and put see them */
	memset(&s, 0, sizeof(s));
	for (i = 0; i < MT6797_DATA_DEPTH; i++) {
		assert(mt6797_data_put_credit(&s, 50 + i, &a, 1000, 13, 10 + i, 1000 + i));
		assert(mt6797_data_mark_reported(&s, 50 + i));
	}
	for (i = 0; i < MT6797_DATA_DEPTH; i++)
		assert(mt6797_data_take(&s, 50 + i) == &a);
	assert(s.count == 0 && !mt6797_data_entry_free(&s) && !mt6797_data_room(&s, 13, 1000));
	assert(!mt6797_data_put_credit(&s, 70, &b, 1000, 13, 20, 2000));
	for (i = 0; i < MT6797_DATA_DEPTH; i++)
		assert(mt6797_data_cover_oldest(&s, 13, &copy, &f) == MT6797_DATA_COVER_HELD && copy.ordinal == 10 + i);
	assert(mt6797_data_entry_free(&s) && mt6797_data_room(&s, 13, 1000));
	printf("credit-retire-test: PASS (descriptor without the report; slots covered in order; samples held; placeholders)\n");
	return 0;
}
