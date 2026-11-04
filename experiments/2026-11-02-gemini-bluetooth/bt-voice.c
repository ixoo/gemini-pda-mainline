// SPDX-License-Identifier: MIT
/*
 * CVSD coder for the Gemini's Bluetooth voice path, from the parameters in the
 * Bluetooth Core Specification (Vol 2, Part B, audio): h = 1 - 1/32, beta = 1 - 1/1024,
 * J = K = 4, delta 10 to 1280, 16-bit accumulator, 64 kbit/s.
 *
 *   bt-voice encode [--msb] < 8 kHz S16LE mono > coded bytes
 *   bt-voice decode [--msb] [--raw] < records > 8 kHz S16LE mono
 *
 * decode reads the driver's capture records: 30 coded bytes and a 16-bit validity
 * word, or bare coded bytes with --raw. A byte holds eight bits in time order, first
 * bit in the least significant position, or the most with --msb. An invalid record
 * decodes as the alternating pattern that holds the signal. Counts go to stderr.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define FACTOR 8
#define TAPS 129
#define CUTOFF 3600.0
#define RATE 64000.0

static double fir[TAPS];

/* A Hamming-windowed sinc with unity gain at DC. */
static void fir_init(void)
{
	double sum = 0;
	int i;

	for (i = 0; i < TAPS; i++) {
		double t = i - (TAPS - 1) / 2.0;
		double x = 2 * CUTOFF / RATE;
		double sinc = t == 0 ? x : sin(M_PI * x * t) / (M_PI * t);

		fir[i] = sinc * (0.54 - 0.46 * cos(2 * M_PI * i / (TAPS - 1)));
		sum += fir[i];
	}
	for (i = 0; i < TAPS; i++)
		fir[i] /= sum;
}

struct cvsd {
	double accumulator, step;
	unsigned int history;
};

/* One time step shared by both directions: bit 1 steps up. Returns the new estimate. */
static double cvsd_step(struct cvsd *c, int bit)
{
	double y;

	c->history = (c->history << 1 | bit) & 15;
	if (c->history == 0 || c->history == 15) {
		c->step += 10;
		if (c->step > 1280)
			c->step = 1280;
	} else {
		c->step *= 1 - 1.0 / 1024;
		if (c->step < 10)
			c->step = 10;
	}
	y = c->accumulator + (bit ? c->step : -c->step);
	if (y > 32767)
		y = 32767;
	if (y < -32767)
		y = -32767;
	c->accumulator = y * (1 - 1.0 / 32);
	return c->accumulator;
}

static int encode(int msb)
{
	struct cvsd c = { .step = 10, .history = 5 };
	double pcm[TAPS / FACTOR + 1] = { 0 };
	const int span = TAPS / FACTOR + 1;
	unsigned char in[2], out = 0;
	int count = 0, i, m;

	while (fread(in, 2, 1, stdin) == 1) {
		memmove(pcm + 1, pcm, (span - 1) * sizeof(*pcm));
		pcm[0] = (int16_t)(in[0] | in[1] << 8);
		for (m = 0; m < FACTOR; m++) {
			double x = 0;
			int bit;

			for (i = 0; i < span && m + i * FACTOR < TAPS; i++)
				x += pcm[i] * fir[m + i * FACTOR];
			x *= FACTOR;
			bit = x >= c.accumulator;
			cvsd_step(&c, bit);
			if (msb)
				out |= bit << (7 - count);
			else
				out |= bit << count;
			if (++count == 8) {
				putchar(out);
				out = 0;
				count = 0;
			}
		}
	}
	return ferror(stdin) ? 1 : 0;
}

static void decode_byte(struct cvsd *c, unsigned char byte, int msb)
{
	static double y[TAPS];
	static unsigned int position, phase;
	int b;

	for (b = 0; b < 8; b++) {
		int bit = (byte >> (msb ? 7 - b : b)) & 1;
		double x = 0;
		int i;

		y[position] = cvsd_step(c, bit);
		position = (position + 1) % TAPS;
		if (++phase < FACTOR)
			continue;
		phase = 0;
		for (i = 0; i < TAPS; i++)
			x += y[(position + i) % TAPS] * fir[i];
		x = x > 32767 ? 32767 : x < -32768 ? -32768 : x;
		putchar((int)lrint(x) & 255);
		putchar(((int)lrint(x) >> 8) & 255);
	}
}

static int decode(int msb, int raw)
{
	struct cvsd c = { .step = 10, .history = 5 };
	unsigned char record[32];
	unsigned long good = 0, bad = 0;
	size_t size = raw ? 1 : sizeof(record);
	int i;

	while (fread(record, size, 1, stdin) == 1) {
		int valid = raw || record[30] || record[31];

		if (valid)
			good++;
		else
			bad++;
		for (i = 0; i < (raw ? 1 : 30); i++)
			decode_byte(&c, valid ? record[i] : 0x55, msb);
	}
	fprintf(stderr, "records: valid=%lu invalid=%lu\n", good, bad);
	return ferror(stdin) ? 1 : 0;
}

int main(int argc, char **argv)
{
	int msb = 0, raw = 0, i;

	for (i = 2; i < argc; i++) {
		if (!strcmp(argv[i], "--msb"))
			msb = 1;
		else if (!strcmp(argv[i], "--raw"))
			raw = 1;
		else
			argc = 0;
	}
	if (argc >= 2 && !strcmp(argv[1], "encode")) {
		fir_init();
		return encode(msb);
	}
	if (argc >= 2 && !strcmp(argv[1], "decode")) {
		fir_init();
		return decode(msb, raw);
	}
	fputs("usage: bt-voice encode|decode [--msb] [--raw]\n", stderr);
	return 2;
}
