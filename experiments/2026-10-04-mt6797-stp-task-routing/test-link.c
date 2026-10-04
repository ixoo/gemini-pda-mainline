/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stp-full-link.h"

static int receive(struct stp_full_link *link, unsigned int task,
	unsigned int seq, unsigned int ack, struct stp_full_frame *result)
{
	static unsigned char wire[32];
	static const unsigned char payload[] = { 4, 14, 4, 1, 3, 12, 0 };
	int length = stp_full_encode(wire, sizeof(wire), payload, sizeof(payload),
				     task, seq, ack);

	assert(length == 13);
	return stp_full_link_receive(link, wire, length, result);
}

int main(void)
{
	struct stp_full_link link, before;
	struct stp_full_frame result, sentinel;
	unsigned char ack[4], corrupt[4];
	unsigned int start, count, value, i, credit, expected_ack, sequence, delivered;
	int found;

	memset(&sentinel, 0xa5, sizeof(sentinel));
	/* Independent queue oracle: an ACK must name a transmitted queue entry,
	 * or repeat the previous cumulative ACK. Other ACKs are ignored without
	 * credit. Test every modulo-eight start.
	 */
	for (start = 0; start < 8; start++) {
		for (count = 0; count <= STP_FULL_WINDOW; count++) {
			for (value = 0; value < 8; value++) {
				stp_full_link_init(&link);
				link.tx_next = start;
				link.peer_ack = (start + 7) % 8;
				for (i = 0; i < count; i++)
					assert(stp_full_link_sent(&link, (start + i) % 8, 7) == 0);
				before = link;
				credit = 0;
				found = value == before.peer_ack;
				for (i = 0; i < count; i++) {
					if (value == (start + i) % 8) {
						found = 1;
						credit = i + 1;
					}
				}
				assert(stp_full_ack(ack, sizeof(ack), value) == 4);
				memcpy(&result, &sentinel, sizeof(result));
				assert(stp_full_link_receive(&link, ack, 4, &result) == 0);
				if (found) {
					assert(link.tx_pending == count - credit && link.peer_ack == value);
					assert(link.tx_next == before.tx_next && !link.ack_owed);
					before = link;
					assert(stp_full_link_receive(&link, ack, 4, &result) == 0);
				}
				assert(result.task == STP_FULL_TASK_NONE);
				assert(!memcmp(&link, &before, sizeof(link)));
			}
		}
	}
	stp_full_link_init(&link);
	before = link;
	assert(receive(&link, 0, 7, 7, &result) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	for (i = 0; i < 7; i++)
		assert(stp_full_link_sent(&link, i, 7) == 0);
	before = link;
	assert(stp_full_link_sent(&link, 7, 7) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	assert(receive(&link, STP_FULL_TASK_BT, 0, 2, &result) == 1);
	assert(result.task == STP_FULL_TASK_BT && link.tx_pending == 4);
	assert(receive(&link, STP_FULL_TASK_WMT, 1, 6, &result) == 1);
	assert(result.task == STP_FULL_TASK_WMT && !link.tx_pending && link.rx_pending == 2);
	/* An ACK snapshot for RX0 finishes after RX1. The newer credit stays owed. */
	assert(stp_full_link_sent(&link, 7, 0) == 0);
	assert(link.rx_pending == 1 && link.host_ack == 0 && link.ack_owed);
	assert(stp_full_link_ack_sent(&link, 1) == 0);
	assert(!link.rx_pending && !link.ack_owed);
	/* Retransmitted RX0 never redelivers or frees TX7 via its piggyback ACK. */
	assert(receive(&link, STP_FULL_TASK_BT, 0, 7, &result) == 2);
	assert(link.rx_next == 2 && link.tx_pending == 1 && link.peer_ack == 6 && link.ack_owed);
	assert(stp_full_link_ack_sent(&link, 1) == 0);
	assert(receive(&link, STP_FULL_TASK_BT, 2, 7, &result) == 1);
	assert(!link.tx_pending && link.rx_pending == 1);
	before = link;
	assert(stp_full_link_ack_sent(&link, 0) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	assert(stp_full_link_ack_sent(&link, 2) == 0);
	/* RX and outgoing ACK credit are separate, bounded windows. */
	stp_full_link_init(&link);
	for (i = 0; i < 7; i++)
		assert(receive(&link, i % 2 ? 4 : 0, i, 7, &result) == 1);
	before = link;
	memcpy(&result, &sentinel, sizeof(result));
	assert(receive(&link, 0, 7, 7, &result) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	assert(!memcmp(&result, &sentinel, sizeof(result)));
	assert(stp_full_link_ack_sent(&link, 3) == 0);
	assert(link.rx_pending == 3 && link.ack_owed);
	assert(receive(&link, 0, 7, 7, &result) == 1);
	assert(stp_full_link_ack_sent(&link, 6) == 0);
	assert(link.rx_pending == 1 && link.ack_owed);
	assert(stp_full_link_sent(&link, 0, 7) == 0);
	assert(!link.rx_pending && !link.ack_owed);
	/* Alternating task delivery survives repeated wrap; task boundaries never
	 * reseed sequence state. Duplicate traffic has no delivery credit.
	 */
	stp_full_link_init(&link);
	delivered = 0;
	for (i = 0; i < 64; i++) {
		sequence = link.tx_next;
		assert(stp_full_link_sent(&link, sequence, link.local_ack) == 0);
		expected_ack = sequence;
		assert(receive(&link, i % 2 ? 4 : 0, link.rx_next, expected_ack, &result) == 1);
		delivered++;
		assert(result.task == (i % 2 ? 4U : 0U) && !link.tx_pending);
		assert(stp_full_link_ack_sent(&link, link.local_ack) == 0);
		assert(receive(&link, result.task, link.local_ack, expected_ack, &result) == 2);
		assert(stp_full_link_ack_sent(&link, link.local_ack) == 0);
	}
	assert(delivered == 64 && !link.tx_next && !link.rx_next);
	/* Corrupt wire, invalid ACK completion and invalid TX cannot repair state. */
	before = link;
	assert(stp_full_ack(ack, sizeof(ack), link.peer_ack) == 4);
	memcpy(corrupt, ack, 4);
	corrupt[3] ^= 1;
	memcpy(&result, &sentinel, sizeof(result));
	assert(stp_full_link_receive(&link, corrupt, 4, &result) == -1);
	assert(stp_full_link_receive(&link, ack, 3, &result) == -1);
	assert(stp_full_link_receive(&link, ack, 4, 0) == -1);
	assert(!memcmp(&result, &sentinel, sizeof(result)));
	assert(stp_full_link_sent(&link, 8, 7) == -1);
	assert(stp_full_link_sent(&link, link.tx_next, 8) == -1);
	assert(stp_full_link_ack_sent(&link, 8) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	puts("shared_stp_link=pass; cumulative window, task sequence and WMT boundary; no device access");
	return 0;
}
