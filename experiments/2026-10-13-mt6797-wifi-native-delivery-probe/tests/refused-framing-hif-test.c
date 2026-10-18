/* SPDX-License-Identifier: GPL-2.0-only */
/* Reuse actual C8 HIF/PIO selection cases before testing refusal-only hints. */
#include "c8-selected-baseline.inc"
#include <stdarg.h>

static unsigned int lines;
static char output[2][1024];
#ifdef FRAMING_CHILD
static bool hint_printed;
#endif
#define wiphy_dev(w) NULL
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args;
	(void)dev;
	assert(lines < 2);
	va_start(args, format);
	assert(vsnprintf(output[lines], sizeof(output[lines]), format, args) > 0);
	va_end(args);
	lines++;
}
#include "framing-log.inc"

struct counts { unsigned int io, clocks; };
static struct counts trial(unsigned int api, unsigned int port, unsigned int length,
		unsigned int header, size_t capacity, unsigned int type,
		unsigned int control, unsigned int status, unsigned int fail,
		unsigned int expire)
{
	struct mt6797_init_transaction t = { .phase = MT6797_INIT_IDLE,
		.free_pages = 104, .start_free_pages = 104 };
	struct mt6797_hif_rx_result r, again;
	struct mt6797_hif_command command;
	struct mt6797_hif *h;
	struct counts counts;
	unsigned char out[2352];
	bool valid;
	int rc;

	memset(&mock, 0, sizeof(mock));
	mock.base = calloc(1, 0x1004);
	assert(mock.base);
	mock.now = 1000;
	mock.port = port;
	mock.logical = length;
	mock.header_delta = header - length;
	mock.override_fields = true;
	mock.type_word = type;
	mock.header_control = control;
	mock.status_flags = status;
	mock.fail_at = fail;
	mock.expire_clock_at = expire;
	mock.copy_allowed = length >= 4 && length <= 2352 && capacity >= length;
	if (mock.copy_allowed) {
		assert(!mt6797_hif_encode_command(port ? 0x54 : 0x50,
			MT6797_HIF_READ, MT6797_HIF_PIO_ONLY, length + 4, 2560, &command));
		mock.words = command.transfer_bytes / 4;
	}
	h = mt6797_hif_alloc(mock.base, 0x1004, &t);
	assert(!IS_ERR(h));
	h->firmware_ready = h->capability_complete = true;
	h->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	memset(out, 0xa5, sizeof(out));
	if (api == 2)
		rc = mt6797_hif_receive_selected(h, 1000001000ULL, out, capacity, &r);
	else if (api == 1)
		rc = mt6797_hif_receive_runtime_packet(h, port, 1000001000ULL, out, capacity, &r);
	else
		rc = mt6797_hif_receive_packet(h, port, 1000001000ULL, out, capacity, &r);
	counts = (struct counts){mock.calls, mock.clocks};
	if (expire) {
		assert(rc == -ETIMEDOUT);
		/* Expire at the guard immediately after the full transfer. */
		assert(r.rx_setup && r.rx_complete && !r.header_valid);
	} else if (fail) {
		assert(rc == -EIO && mock.calls == fail);
	} else if (!length) {
		assert(rc == -EAGAIN);
	} else if (length < 4 || length > 2352 || length != header) {
		assert(rc == -EPROTO);
	} else if (capacity < length) {
		assert(rc == -ENOSPC);
	} else {
		assert(!rc && r.logical_bytes == length && r.packet_type == type);
		assert(r.rx_complete && r.staging_bytes == mock.words * 4);
		for (unsigned int i = 0; i < length; i++)
			assert(out[i] == ((word_at(i / 4) >> ((i % 4) * 8)) & 255));
	}
	if (rc) {
		assert(!r.packet_type && !r.logical_bytes);
		for (unsigned int i = 0; i < sizeof(out); i++)
			assert(out[i] == 0xa5);
	}
	valid = rc == -EPROTO && r.protocol_refusal == MT6797_HIF_RX_REFUSAL_HEADER &&
		r.rx_setup && r.rx_complete && r.header_valid && length >= 16 && header >= 16 &&
		r.staging_bytes >= 16 && (type >> 13) == 2;
#ifdef FRAMING_CHILD
	assert(r.refused_base_valid == valid);
	assert(r.refused_header_control == (valid ? control : 0));
	assert(r.refused_status_flags == (valid ? status : 0));
#endif
	lines = 0;
	memset(output, 0, sizeof(output));
	logged_refusal(rc, port, &r);
	if (rc == -EPROTO) {
		assert(strstr(output[0], "one-shot WLAN native HIF refused:"));
#ifdef FRAMING_CHILD
		char expected[128];

		assert(lines == 2);
		snprintf(expected, sizeof(expected), "base_valid=%u header_control=0x%02x status_flags=0x%04x",
			 valid, valid ? control : 0, valid ? status : 0);
		assert(strstr(output[1], expected));
		if (!hint_printed && api == 2 && !port && length == 88 && header == 40 &&
		    control == 0x18 && status == 0x1000 && valid) {
			fputs(output[1], stderr);
			hint_printed = true;
		}
#else
		assert(lines == 1);
#endif
	} else {
		assert(!lines);
	}
	if (rc && rc != -EAGAIN && rc != -ENOSPC) {
		unsigned int before = mock.calls;

		assert(h->first_error == rc && t.phase == MT6797_INIT_POISONED);
		assert(h->normal.phase == MT6797_NORMAL_FAILED);
		assert(mt6797_hif_receive_selected(h, 1000001000ULL, out, capacity, &again) == -EIO);
		assert(mock.calls == before && !again.pre_valid && !again.refused_type_valid);
#ifdef FRAMING_CHILD
		assert(!again.refused_base_valid && !again.refused_header_control && !again.refused_status_flags);
#endif
		logged_refusal(-EIO, port, &again);
		assert(lines == (rc == -EPROTO ?
#ifdef FRAMING_CHILD
			2U
#else
			1U
#endif
			: 0U));
	}
	printf("%u %u %u %u %zu %u %u %u %u %u %d %u %u %u %u %u\n",
		api, port, length, header, capacity, type, control, status, fail, expire,
		rc, counts.io, r.rx_setup, r.rx_complete, r.logical_bytes != 0, valid);
	mt6797_hif_free(h);
	free(mock.base);
	return counts;
}
int main(void)
{
	const unsigned int pairs[][2] = {{76, 28}, {80, 32}, {449, 401}, {427, 379}, {88, 40}};
	const unsigned int fields[][2] = {{0, 0}, {0x18, 0x1000}, {0x8e, 0xc000}, {0xff, 0xffff}};

	selected_baseline_main();
	for (unsigned int api = 0; api < 3; api++) {
		for (unsigned int port = 0; port < 2; port++) {
			trial(api, port, 0, 0, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 1, 16, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 2353, 2305, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 88, 88, 87, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 4, 20, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 15, 16, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 16, 15, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			trial(api, port, 16, 17, 2352, 0x4000, 0, 0, 0, 0);
			trial(api, port, 88, 0, 2352, 0x4000, 0x18, 0x1000, 0, 0);
			for (unsigned int i = 0; i < sizeof(pairs) / sizeof(pairs[0]); i++) {
				unsigned int length = pairs[i][0], header = pairs[i][1];
				struct counts c;

				for (unsigned int j = 0; j < sizeof(fields) / sizeof(fields[0]); j++)
					trial(api, port, length, header, 2352, 0x4000, fields[j][0], fields[j][1], 0, 0);
				trial(api, port, length, header, 2352, 0xe000, 0x18, 0x1000, 0, 0);
				trial(api, port, length, header, 2352, 0x5e00, 0x18, 0x1000, 0, 0);
				c = trial(api, port, length, header, 2352, 0x4000, 0x18, 0x1000, 0, 0);
				for (unsigned int f = 1; f <= c.io; f++)
					trial(api, port, length, header, 2352, 0x4000, 0x18, 0x1000, f, 0);
				trial(api, port, length, header, 2352, 0x4000, 0x18, 0x1000, 0, c.clocks);
				c = trial(api, port, length, length, 2352, 0x4000, 0x18, 0x1000, 0, 0);
				for (unsigned int f = 1; f <= c.io; f++)
					trial(api, port, length, length, 2352, 0x4000, 0x18, 0x1000, f, 0);
			}
		}
	}
	return 0;
}
