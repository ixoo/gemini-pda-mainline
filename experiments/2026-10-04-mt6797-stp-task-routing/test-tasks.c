/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stp-full-task.h"

struct queue {
	struct stp_full_link *link;
	struct stp_full_link before;
	unsigned int packets, length;
	unsigned char payload[STP_FULL_MAX_PAYLOAD];
	int refuse;
};

static int deliver(void *context, const unsigned char *payload, unsigned int length)
{
	struct queue *queue = context;

	/* The callback must run before either kind of credit is published. */
	assert(!memcmp(queue->link, &queue->before, sizeof(queue->before)));
	if (queue->refuse)
		return queue->refuse;
	queue->packets++;
	queue->length = length;
	memcpy(queue->payload, payload, length);
	return 0;
}

int main(void)
{
	static const unsigned char payload[] = { 4, 14, 4, 1, 3, 12, 0 };
	struct stp_full_link link, before;
	struct stp_full_frame result, sentinel;
	struct queue queue[3] = { 0 };
	struct stp_full_client clients[] = {
		{ STP_FULL_TASK_BT, deliver, &queue[0] },
		{ STP_FULL_TASK_WMT, deliver, &queue[1] },
		{ STP_FULL_TASK_GPS, deliver, &queue[2] },
	};
	struct stp_full_client bad[7];
	unsigned char wire[STP_FULL_MAX_FRAME], ack[4], large[STP_FULL_MAX_PAYLOAD];
	unsigned int i, task, total;
	int bytes;

	memset(&sentinel, 0xa5, sizeof(sentinel));
	stp_full_link_init(&link);
	for (i = 0; i < 3; i++)
		queue[i].link = &link;
	/* Queue-full refusal cannot acknowledge piggyback TX or advance RX. */
	for (i = 0; i < 3; i++)
		assert(stp_full_link_sent(&link, i, 7) == 0);
	bytes = stp_full_encode(wire, sizeof(wire), payload, sizeof(payload), 0, 0, 0);
	before = link;
	queue[0].before = before;
	queue[0].refuse = 1;
	memcpy(&result, &sentinel, sizeof(result));
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	assert(!memcmp(&result, &sentinel, sizeof(result)) && !queue[0].packets);
	/* Separate ACK traffic can advance TX before the same data is retried.
	 * Its now-stale piggyback ACK must not prevent delivery or restore credit.
	 */
	assert(stp_full_ack(ack, sizeof(ack), 2) == 4);
	assert(stp_full_task_receive(&link, ack, 4, 0, 0, &result) == 0);
	queue[0].before = link;
	queue[0].refuse = 0;
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == 1);
	assert(queue[0].packets == 1 && link.peer_ack == 2 && !link.tx_pending);
	assert(link.rx_next == 1 && link.rx_pending == 1 && link.ack_owed);
	assert(!memcmp(queue[0].payload, payload, sizeof(payload)));
	assert(stp_full_link_ack_sent(&link, 0) == 0);
	/* A duplicate after unbind still requests its ACK, never a callback. */
	assert(stp_full_task_receive(&link, wire, bytes, 0, 0, &result) == 2);
	assert(queue[0].packets == 1 && stp_full_link_ack_sent(&link, 0) == 0);
	/* Unknown task, malformed registry, corruption and callback failures all
	 * preserve both credit windows and the caller's result.
	 */
	bytes = stp_full_encode(wire, sizeof(wire), payload, sizeof(payload), 1, 1, 2);
	before = link;
	memcpy(&result, &sentinel, sizeof(result));
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	bytes = stp_full_encode(wire, sizeof(wire), payload, sizeof(payload), 0, 1, 2);
	memcpy(bad, clients, sizeof(clients));
	bad[1].task = 0;
	assert(stp_full_task_receive(&link, wire, bytes, bad, 3, &result) == -1);
	bad[1] = clients[1];
	bad[2].receive = 0;
	assert(stp_full_task_receive(&link, wire, bytes, bad, 3, &result) == -1);
	bad[2] = clients[2];
	bad[2].task = 6;
	assert(stp_full_task_receive(&link, wire, bytes, bad, 3, &result) == -1);
	assert(stp_full_task_receive(&link, wire, bytes, bad, 7, &result) == -1);
	assert(stp_full_task_receive(&link, wire, bytes, 0, 3, &result) == -1);
	queue[0].before = link;
	queue[0].refuse = -1;
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == -1);
	queue[0].refuse = 0;
	wire[bytes - 1] ^= 1;
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == -1);
	assert(!memcmp(&link, &before, sizeof(link)));
	assert(!memcmp(&result, &sentinel, sizeof(result)));
	assert(queue[0].packets == 1 && !queue[1].packets && !queue[2].packets);
	/* Route asynchronous BT/GPS data without an active WMT command. Task
	 * bindings alternate while one global sequence crosses wrap repeatedly.
	 */
	for (i = 0; i < 48; i++) {
		task = i % 3;
		queue[task].before = link;
		bytes = stp_full_encode(wire, sizeof(wire), payload, sizeof(payload),
					clients[task].task, link.rx_next, link.peer_ack);
		assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == 1);
		assert(result.task == clients[task].task);
		assert(stp_full_link_ack_sent(&link, link.local_ack) == 0);
	}
	total = queue[0].packets + queue[1].packets + queue[2].packets;
	assert(total == 49 && queue[0].packets == 17 && queue[1].packets == 16 && queue[2].packets == 16);
	for (i = 0; i < sizeof(large); i++)
		large[i] = i;
	queue[0].before = link;
	bytes = stp_full_encode(wire, sizeof(wire), large, sizeof(large), 0, link.rx_next, link.peer_ack);
	assert(stp_full_task_receive(&link, wire, bytes, clients, 3, &result) == 1);
	assert(queue[0].length == sizeof(large) && !memcmp(queue[0].payload, large, sizeof(large)));
	puts("shared_task_routing=pass; callback before credit, queue retry and duplicate suppression; no device access");
	return 0;
}
