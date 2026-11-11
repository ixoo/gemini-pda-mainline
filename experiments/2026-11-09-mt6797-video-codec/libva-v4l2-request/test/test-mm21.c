// SPDX-License-Identifier: GPL-3.0-or-later
/*
 * Off-device test of the MM21 detiler in libva-v4l2_request (src/mm21.c).
 *
 *   test-mm21 detile W H PITCH PADH < frames.mm21 > frames.i420
 *       Detile MM21 frames stored back to back (luma PITCH*PADH bytes, then
 *       chroma PITCH*PADH/2) and write the visible W x H picture as I420,
 *       for comparison with an ffmpeg framemd5.
 *   test-mm21 check W H PITCH PADH
 *       Random MM21 data; compare the detiler with a per-pixel address
 *       formula. Exit status 0 when identical.
 *   test-mm21 bench W H PITCH PADH N
 *       Detile N times, print ns per frame.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "mm21.h"

static uint32_t align(uint32_t v, uint32_t a)
{
	return (v + a - 1) / a * a;
}

/* MM21 address of luma (x, y) and chroma byte (x, y). */
static size_t luma_at(uint32_t pitch, uint32_t x, uint32_t y)
{
	return (size_t)(y / 32) * pitch * 32 + (x / 16) * 512 + (y % 32) * 16 + x % 16;
}

static size_t chroma_at(uint32_t pitch, uint32_t x, uint32_t y)
{
	return (size_t)(y / 16) * pitch * 16 + (x / 16) * 256 + (y % 16) * 16 + x % 16;
}

int main(int argc, char **argv)
{
	uint32_t w, h, pitch, padh, dpitch;
	size_t ysz, csz, dsz;
	uint8_t *src, *dst;

	if (argc < 6)
		return 2;
	w = atoi(argv[2]);
	h = atoi(argv[3]);
	pitch = atoi(argv[4]);
	padh = atoi(argv[5]);
	dpitch = align(pitch, 64);
	ysz = (size_t)pitch * padh;
	csz = ysz / 2;
	dsz = (size_t)dpitch * padh * 3 / 2;
	src = malloc(ysz + csz);
	dst = malloc(dsz);
	if (!src || !dst)
		return 1;

	if (!strcmp(argv[1], "detile")) {
		uint8_t *row = malloc(w);
		unsigned int n = 0;

		while (fread(src, 1, ysz + csz, stdin) == ysz + csz) {
			uint8_t *uv = dst + (size_t)dpitch * padh;

			v4l2r_mm21_detile(dst, uv, dpitch, src, src + ysz,
					  pitch, pitch, padh);
			for (uint32_t y = 0; y < h; y++)
				fwrite(dst + (size_t)y * dpitch, 1, w, stdout);
			for (int c = 0; c < 2; c++) {
				for (uint32_t y = 0; y < h / 2; y++) {
					for (uint32_t x = 0; x < w / 2; x++)
						row[x] = uv[(size_t)y * dpitch + 2 * x + c];
					fwrite(row, 1, w / 2, stdout);
				}
			}
			n++;
		}
		fprintf(stderr, "detiled %u frames\n", n);
		return 0;
	}

	srand(1234);
	for (size_t i = 0; i < ysz + csz; i++)
		src[i] = rand();

	if (!strcmp(argv[1], "check")) {
		uint8_t *uv = dst + (size_t)dpitch * padh;
		unsigned long bad = 0;

		memset(dst, 0xaa, dsz);
		v4l2r_mm21_detile(dst, uv, dpitch, src, src + ysz, pitch,
				  pitch, padh);
		for (uint32_t y = 0; y < padh; y++)
			for (uint32_t x = 0; x < pitch; x++)
				bad += dst[(size_t)y * dpitch + x] !=
				       src[luma_at(pitch, x, y)];
		for (uint32_t y = 0; y < padh / 2; y++)
			for (uint32_t x = 0; x < pitch; x++)
				bad += uv[(size_t)y * dpitch + x] !=
				       src[ysz + chroma_at(pitch, x, y)];
		printf("%ux%u pitch %u padded height %u: %lu mismatches\n",
		       w, h, pitch, padh, bad);
		return bad != 0;
	}

	if (!strcmp(argv[1], "bench") && argc > 6) {
		/* Cycle through 32 source and destination frames (~150 MB at
		 * 1080p) so the caches do not hold them between passes. */
		enum { FRAMES = 32 };
		unsigned int n = atoi(argv[6]);
		uint8_t *srcs[FRAMES], *dsts[FRAMES];
		struct timespec a, b;

		for (int i = 0; i < FRAMES; i++) {
			srcs[i] = malloc(ysz + csz);
			dsts[i] = malloc(dsz);
			if (!srcs[i] || !dsts[i])
				return 1;
			memcpy(srcs[i], src, ysz + csz);
			memset(dsts[i], 0, dsz);
		}
		clock_gettime(CLOCK_MONOTONIC, &a);
		for (unsigned int i = 0; i < n; i++)
			v4l2r_mm21_detile(dsts[i % FRAMES],
					  dsts[i % FRAMES] + (size_t)dpitch * padh,
					  dpitch, srcs[i % FRAMES],
					  srcs[i % FRAMES] + ysz, pitch, pitch,
					  padh);
		clock_gettime(CLOCK_MONOTONIC, &b);
		printf("%ux%u (pitch %u, %u rows): %.0f ns/frame\n", w, h,
		       pitch, padh,
		       ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec)) / n);
		return 0;
	}

	return 2;
}
