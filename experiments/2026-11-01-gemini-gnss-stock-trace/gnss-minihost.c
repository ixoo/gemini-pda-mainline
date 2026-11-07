// SPDX-License-Identifier: MIT
/*
 * Run the GNSS DSP over /dev/gnss0 and record what it sends: gnss-minihost.py
 * for the station, which has no Python. /dev/gnss0 has poll, so one thread does.
 * gnss-mt6797 boots the DSP from its firmware file when the device opens, so
 * this starts at the setup frames.
 *
 * Usage: gnss-minihost DEVICE PARAMS OUTPUT SECONDS
 * PARAMS is a private text file of "key value" lines; hex values may repeat.
 * Its image_offset, image_size and header, from when this booted the DSP
 * itself, are accepted and ignored.
 * Exit: 0 full window, 3 signalled, 4 open failed, 5 DSP silent, 6 write failed.
 */

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define EXIT_SIGNALLED 3
#define EXIT_OPEN 4
#define EXIT_SILENT 5
#define EXIT_WRITE 6
#define MAX_ITEMS 16
#define MAX_ITEM 256
#define GPS_EPOCH 315964800L
#define LEAP 18

struct item {
	uint8_t data[MAX_ITEM];
	size_t length;
};

static struct {
	long first_millis;
	struct item status4, setting, setting_first;
	struct item setup[MAX_ITEMS], lists[MAX_ITEMS];
	int setups, nlists;
} params;

static int device_fd;
static FILE *logfile;
static uint8_t pending[8192];
static size_t pending_length;
static unsigned long counts[256];
static volatile sig_atomic_t signalled;

static void on_signal(int number)
{
	(void)number;
	signalled = 1;
}

static double monotonic(void)
{
	struct timespec now;

	clock_gettime(CLOCK_MONOTONIC, &now);
	return now.tv_sec + now.tv_nsec / 1e9;
}

static void record(char kind, const uint8_t *data, size_t length)
{
	struct timespec now;
	size_t i;

	clock_gettime(CLOCK_REALTIME, &now);
	fprintf(logfile, "%lld.%03ld %c ", (long long)now.tv_sec, now.tv_nsec / 1000000, kind);
	for (i = 0; i < length; i++)
		fprintf(logfile, "%02x", data[i]);
	fputc('\n', logfile);
	fflush(logfile);
}

static size_t put_stuffed(uint8_t *out, const uint8_t *in, size_t length)
{
	size_t i, n = 0;

	for (i = 0; i < length; i++) {
		if (in[i] == 0xde) {
			out[n++] = 0xde;
			out[n++] = 0xe0;
		} else if (in[i] == 0xaa) {
			out[n++] = 0xde;
			out[n++] = 0xdf;
		} else {
			out[n++] = in[i];
		}
	}
	return n;
}

/* Appends one frame to out; the sequence nibble is always 0 on the host side. */
static size_t put_frame(uint8_t *out, unsigned int id, const uint8_t *payload, size_t length)
{
	uint8_t head[4], tail[2];
	unsigned int sum = 0;
	size_t i, n = 0;

	head[0] = (length + 4) & 0xff;
	head[1] = ((length + 4) >> 8) & 0x0f;
	head[2] = id & 0xff;
	head[3] = id >> 8;
	for (i = 0; i < 4; i++)
		sum += head[i];
	for (i = 0; i < length; i++)
		sum += payload[i];
	tail[0] = sum & 0xff;
	tail[1] = (sum >> 8) & 0xff;
	out[n++] = 0xaa;
	out[n++] = 0xf0;
	n += put_stuffed(out + n, head, 4);
	n += put_stuffed(out + n, payload, length);
	n += put_stuffed(out + n, tail, 2);
	out[n++] = 0xaa;
	out[n++] = 0x0f;
	return n;
}

static int send_bytes(const uint8_t *data, size_t length)
{
	size_t sent = 0;

	record('W', data, length);
	while (sent < length) {
		ssize_t n = write(device_fd, data + sent, length - sent);

		if (n < 0) {
			if (errno == EINTR)
				continue;
			perror("write");
			return -1;
		}
		sent += n;
	}
	return 0;
}

/* Calls handle for each complete frame. Returns after at most wait_ms. */
static void receive(int wait_ms, void (*handle)(unsigned int, const uint8_t *, size_t))
{
	struct pollfd poller = { .fd = device_fd, .events = POLLIN };
	size_t start = 0;

	if (poll(&poller, 1, wait_ms) > 0 && (poller.revents & POLLIN)) {
		ssize_t n = read(device_fd, pending + pending_length,
				 sizeof(pending) - pending_length);

		if (n > 0) {
			record('R', pending + pending_length, n);
			pending_length += n;
		}
	}
	for (;;) {
		uint8_t raw[4096];
		size_t i, begin, end, out = 0;

		for (begin = start; begin + 1 < pending_length; begin++)
			if (pending[begin] == 0xaa && pending[begin + 1] == 0xf0)
				break;
		if (begin + 1 >= pending_length) {
			start = begin;
			break;
		}
		for (end = begin + 2; end + 1 < pending_length; end++)
			if (pending[end] == 0xaa && pending[end + 1] == 0x0f)
				break;
		if (end + 1 >= pending_length) {
			start = begin;
			break;
		}
		for (i = begin + 2; i < end && out < sizeof(raw); i++) {
			if (pending[i] == 0xde && i + 1 < end) {
				i++;
				raw[out++] = pending[i] == 0xdf ? 0xaa :
					     pending[i] == 0xe0 ? 0xde : pending[i];
			} else {
				raw[out++] = pending[i];
			}
		}
		start = end + 2;
		if (out >= 6) {
			counts[raw[2]]++;
			handle(raw[2] | raw[3] << 8, raw + 4, out - 6);
		}
	}
	if (start >= pending_length) {
		pending_length = 0;
	} else if (start) {
		memmove(pending, pending + start, pending_length - start);
		pending_length -= start;
	} else if (pending_length == sizeof(pending)) {
		pending_length = 0;
	}
}

static double last_frame;

static void on_frame(unsigned int id, const uint8_t *payload, size_t length)
{
	(void)id;
	(void)payload;
	(void)length;
	last_frame = monotonic();
}

static int run_second(long millis, int first)
{
	static uint8_t out[8192];
	uint8_t head[4] = { 0, 0, millis & 0xff, (millis >> 8) & 0xff };
	uint8_t status[17] = { 0 }, all_ones[28];
	double now = time(NULL) - GPS_EPOCH + LEAP;
	long units = (long)((now - 604800.0 * (long)(now / 604800.0)) / 1.5);
	size_t n = 0;
	int i;

	memcpy(status + 4, params.status4.data, 2);
	status[11] = (units >> 16) & 0xff;
	status[12] = (units >> 24) & 0xff;
	status[13] = units & 0xff;
	status[14] = (units >> 8) & 0xff;
	n += put_frame(out + n, 0xfe00, head, sizeof(head));
	n += put_frame(out + n, 0xfe01, status, sizeof(status));
	for (i = 0; i < params.nlists; i++)
		n += put_frame(out + n, 0xfe03, params.lists[i].data, params.lists[i].length);
	if (first) {
		memset(all_ones, 0xff, sizeof(all_ones));
		n += put_frame(out + n, 0xfe04, all_ones, sizeof(all_ones));
	}
	n += put_frame(out + n, 0xfe08, params.setting.data, params.setting.length);
	if (first)
		n += put_frame(out + n, 0xfe08, params.setting_first.data,
			       params.setting_first.length);
	n += put_frame(out + n, 0xfe1c, NULL, 0);
	n += put_frame(out + n, 0xfe05, (const uint8_t *)"\x29\x00", 2);
	return send_bytes(out, n);
}

static int session(double seconds)
{
	static uint8_t out[2 * (MAX_ITEM + 8)];
	double start, next_tick;
	long millis = params.first_millis;
	size_t n;
	int i, first = 1;

	for (i = 0; i < params.setups; i++) {
		n = put_frame(out, 0xfe05, params.setup[i].data, params.setup[i].length);
		if (send_bytes(out, n))
			return EXIT_WRITE;
	}
	start = next_tick = monotonic();
	last_frame = 0;
	while (monotonic() - start < seconds) {
		double now = monotonic(), wait = next_tick - now;

		if (signalled)
			return EXIT_SIGNALLED;
		if (now >= next_tick) {
			if (run_second(millis, first))
				return EXIT_WRITE;
			first = 0;
			millis += 1000;
			next_tick += 1;
			wait = 0.01;
		}
		receive(wait > 0.2 ? 200 : wait < 0.01 ? 10 : (int)(wait * 1000), on_frame);
		if (now - start > 30 && now - last_frame > 10) {
			puts("DSP silent for 10 s");
			return EXIT_SILENT;
		}
	}
	return 0;
}

static int parse_hex(struct item *item, const char *text)
{
	size_t length = strlen(text) / 2, i;

	if (length > MAX_ITEM)
		return -1;
	for (i = 0; i < length; i++) {
		unsigned int value;

		if (sscanf(text + 2 * i, "%2x", &value) != 1)
			return -1;
		item->data[i] = value;
	}
	item->length = length;
	return 0;
}

static int read_params(const char *path)
{
	char line[1024], key[32], value[1024];
	FILE *file = fopen(path, "r");
	int bad = 0;

	if (!file)
		return -1;
	while (fgets(line, sizeof(line), file)) {
		int two = sscanf(line, "%31s %1023s", key, value) == 2;

		if (!two)
			continue;
		if (!strcmp(key, "image_offset") || !strcmp(key, "image_size") ||
		    !strcmp(key, "header"))
			continue;
		if (!strcmp(key, "first_millis"))
			params.first_millis = atol(value);
		else if (!strcmp(key, "status4"))
			bad |= parse_hex(&params.status4, value);
		else if (!strcmp(key, "setting"))
			bad |= parse_hex(&params.setting, value);
		else if (!strcmp(key, "setting_first"))
			bad |= parse_hex(&params.setting_first, value);
		else if (!strcmp(key, "setup") && params.setups < MAX_ITEMS)
			bad |= parse_hex(&params.setup[params.setups++], value);
		else if (!strcmp(key, "list") && params.nlists < MAX_ITEMS)
			bad |= parse_hex(&params.lists[params.nlists++], value);
		else
			bad = 1;
	}
	fclose(file);
	return bad ? -1 : 0;
}

int main(int argc, char **argv)
{
	struct sigaction action = { .sa_handler = on_signal };
	uint8_t stop[32];
	int status, i;
	size_t n;

	if (argc != 5) {
		fputs("usage: gnss-minihost DEVICE PARAMS OUTPUT SECONDS\n", stderr);
		return 2;
	}
	if (read_params(argv[2]) || params.status4.length != 2) {
		fputs("bad params\n", stderr);
		return 2;
	}
	logfile = fopen(argv[3], "w");
	if (!logfile) {
		perror("output");
		return 2;
	}
	sigaction(SIGTERM, &action, NULL);
	sigaction(SIGINT, &action, NULL);
	device_fd = open(argv[1], O_RDWR);
	if (device_fd < 0) {
		perror("open, which boots the DSP");
		return EXIT_OPEN;
	}
	puts("device open, DSP booted");
	fflush(stdout);
	status = session(atof(argv[4]));
	n = put_frame(stop, 0xfe05, (const uint8_t *)"\x04\x00", 2);
	send_bytes(stop, n);
	usleep(500000);
	close(device_fd);
	fputs("frames by low id byte:", stdout);
	for (i = 0; i < 256; i++)
		if (counts[i])
			printf(" %02x=%lu", i, counts[i]);
	printf("\nstop sent, closed, exit %d\n", status);
	fclose(logfile);
	return status;
}
