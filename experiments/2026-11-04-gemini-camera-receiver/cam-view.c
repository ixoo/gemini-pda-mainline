// SPDX-License-Identifier: MIT
/*
 * Stream from a raw capture node and optionally show it on the panel. Raw ioctls,
 * so it builds static:
 *
 *   aarch64-linux-gnu-gcc -O2 -Wall -Wextra -static -o cam-view cam-view.c -lm
 *
 * usage: cam-view [-d VIDEO] [-s SUBDEV] [-n FRAMES] [-e EXPOSURE] [-g GAIN] [-p PATTERN]
 *                 [-D DIGITAL] [-R RED] [-B BLUE] [-f FLIP] [-b] [-F] [-m]
 *
 *   -s    the sensor's sub-device, needed for -e, -g, -p, -D, -R and -B
 *   -R -B the sensor's red and blue balance, 256 is unity; they turn the tool's own
 *         grey-world balance off
 *   -f    bit 0 mirrors, bit 1 flips, for the picture on the panel
 *   -b    the sensor is showing colour bars: count frames with any line that differs
 *         from line 0 or 1 of the same frame
 *   -F    do not touch the framebuffer
 *   -m    print the mean of each of the four positions in the 2x2 Bayer cell, and the
 *         share of pixels near full scale, over all frames but the first two
 *
 * The picture is rough: one RGB pixel per GRBG cell, black level off, a square-root
 * curve, and grey-world colour balance from the previous frame. Nothing is saved.
 * The panel scans 1080x2160 and is turned 90 degrees when held in landscape.
 */
#include <errno.h>
#include <fcntl.h>
#include <linux/videodev2.h>
#include <math.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define NBUF 3
#define MAX_FRAMES 3000
#define FB_W 1080
#define FB_H 2160
#define BLACK 64

static void die(const char *what)
{
	fprintf(stderr, "%s: %s\n", what, strerror(errno));
	exit(1);
}

static void set_ctrl(int fd, uint32_t id, int value, const char *name)
{
	struct v4l2_control c = { .id = id, .value = value };

	if (fd < 0) {
		fprintf(stderr, "%s needs -s\n", name);
		exit(2);
	}
	if (ioctl(fd, VIDIOC_S_CTRL, &c) < 0)
		die(name);
	printf("%s %d\n", name, c.value);
}

static inline unsigned int raw10(const uint8_t *line, unsigned int x)
{
	unsigned int off = x * 10 / 8;

	return ((line[off] | line[off + 1] << 8) >> (x % 4 * 2)) & 0x3ff;
}

static double now(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec + t.tv_nsec / 1e9;
}

/* Lines that match neither of the first two. */
static unsigned int bad_lines(const uint8_t *f, unsigned int stride, unsigned int h)
{
	unsigned int y, bad = 0;

	for (y = 2; y < h; y++)
		bad += memcmp(f + y * stride, f + (y & 1) * stride, stride) != 0;
	return bad;
}

static void draw(uint32_t *fb, unsigned int fb_stride, const uint8_t *f, unsigned int stride,
		 unsigned int w, unsigned int h, unsigned int flip, const uint8_t curve[3][1024],
		 uint64_t sum[3])
{
	unsigned int cw = w / 2, ch = h / 2;
	unsigned int u0 = (FB_H - cw) / 2, v0 = (FB_W - ch) / 2;
	unsigned int x, y;

	sum[0] = sum[1] = sum[2] = 0;
	for (y = 0; y < ch; y++) {
		const uint8_t *l0 = f + 2 * y * stride, *l1 = l0 + stride;
		unsigned int v = flip & 2 ? ch - 1 - y : y;

		for (x = 0; x < cw; x++) {
			unsigned int u = flip & 1 ? cw - 1 - x : x;
			unsigned int r = raw10(l0, 2 * x + 1);
			unsigned int g = (raw10(l0, 2 * x) + raw10(l1, 2 * x + 1)) / 2;
			unsigned int b = raw10(l1, 2 * x);
			uint32_t *px = (uint32_t *)((uint8_t *)fb +
						    (FB_H - 1 - (u0 + u)) * fb_stride) + v0 + v;

			sum[0] += r;
			sum[1] += g;
			sum[2] += b;
			*px = curve[0][r] << 16 | curve[1][g] << 8 | curve[2][b];
		}
	}
}

/* Over every cell of the frame. */
static void measure(const uint8_t *f, unsigned int stride, unsigned int w, unsigned int h,
		    uint64_t mean[4], uint64_t high[4])
{
	unsigned int x, y;

	for (y = 0; y < h; y++) {
		const uint8_t *l = f + y * stride;

		for (x = 0; x < w; x++) {
			unsigned int pos = (y & 1) * 2 + (x & 1);
			unsigned int v = raw10(l, x);

			mean[pos] += v;
			high[pos] += v >= 1000;
		}
	}
}

static void make_curves(uint8_t curve[3][1024], const uint64_t sum[3])
{
	unsigned int c, i;

	for (c = 0; c < 3; c++) {
		double gain = 1.0;

		if (sum[c] && sum[1]) {
			gain = (double)sum[1] / sum[c];
			gain = gain < 0.5 ? 0.5 : gain > 3.0 ? 3.0 : gain;
		}
		for (i = 0; i < 1024; i++) {
			double v = i <= BLACK ? 0 : gain * (i - BLACK) / (1023.0 - BLACK);

			curve[c][i] = v >= 1 ? 255 : (uint8_t)(255 * sqrt(v));
		}
	}
}

int main(int argc, char **argv)
{
	const char *video = "/dev/video0", *subdev = NULL;
	unsigned int frames = 30, flip = 0, i, bad_frames = 0, gaps = 0;
	int exposure = -1, gain = -1, pattern = -1, digital = -1, red = -1, blue = -1;
	int bars = 0, use_fb = 1, means = 0, opt, fd, sfd = -1, fbfd;
	struct v4l2_format fmt = { .type = V4L2_BUF_TYPE_VIDEO_CAPTURE };
	struct v4l2_requestbuffers req = { 0 };
	struct v4l2_buffer buf;
	enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	void *map[NBUF];
	uint8_t *copy, curve[3][1024];
	uint64_t sum[3] = { 0, 0, 0 }, mean[4] = { 0 }, high[4] = { 0 };
	unsigned int measured = 0;
	uint32_t *fb = NULL, last_seq = 0;
	double start = 0, end = 0;

	while ((opt = getopt(argc, argv, "d:s:n:e:g:p:D:R:B:f:bFm")) != -1) {
		switch (opt) {
		case 'd': video = optarg; break;
		case 's': subdev = optarg; break;
		case 'n': frames = atoi(optarg); break;
		case 'e': exposure = atoi(optarg); break;
		case 'g': gain = atoi(optarg); break;
		case 'p': pattern = atoi(optarg); break;
		case 'D': digital = atoi(optarg); break;
		case 'R': red = atoi(optarg); break;
		case 'B': blue = atoi(optarg); break;
		case 'f': flip = atoi(optarg); break;
		case 'b': bars = 1; break;
		case 'F': use_fb = 0; break;
		case 'm': means = 1; break;
		default: return 2;
		}
	}
	if (!frames || frames > MAX_FRAMES) {
		fprintf(stderr, "frames must be 1 to %d\n", MAX_FRAMES);
		return 2;
	}

	if (subdev) {
		sfd = open(subdev, O_RDWR);
		if (sfd < 0)
			die(subdev);
	}
	if (pattern >= 0)
		set_ctrl(sfd, V4L2_CID_TEST_PATTERN, pattern, "pattern");
	if (exposure >= 0)
		set_ctrl(sfd, V4L2_CID_EXPOSURE, exposure, "exposure");
	if (gain >= 0)
		set_ctrl(sfd, V4L2_CID_ANALOGUE_GAIN, gain, "gain");
	if (digital >= 0)
		set_ctrl(sfd, V4L2_CID_DIGITAL_GAIN, digital, "digital");
	if (red >= 0)
		set_ctrl(sfd, V4L2_CID_RED_BALANCE, red, "red");
	if (blue >= 0)
		set_ctrl(sfd, V4L2_CID_BLUE_BALANCE, blue, "blue");

	fd = open(video, O_RDWR);
	if (fd < 0)
		die(video);
	if (ioctl(fd, VIDIOC_G_FMT, &fmt) < 0)
		die("G_FMT");
	printf("format %.4s %ux%u stride %u size %u\n", (char *)&fmt.fmt.pix.pixelformat,
	       fmt.fmt.pix.width, fmt.fmt.pix.height, fmt.fmt.pix.bytesperline,
	       fmt.fmt.pix.sizeimage);

	if (use_fb) {
		fbfd = open("/dev/fb0", O_RDWR);
		if (fbfd < 0)
			die("/dev/fb0");
		fb = mmap(NULL, FB_W * 4 * FB_H, PROT_READ | PROT_WRITE, MAP_SHARED, fbfd, 0);
		if (fb == MAP_FAILED)
			die("mmap fb0");
	}

	req.count = NBUF;
	req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
	req.memory = V4L2_MEMORY_MMAP;
	if (ioctl(fd, VIDIOC_REQBUFS, &req) < 0)
		die("REQBUFS");
	if (req.count != NBUF) {
		fprintf(stderr, "got %u buffers\n", req.count);
		return 1;
	}
	for (i = 0; i < NBUF; i++) {
		memset(&buf, 0, sizeof(buf));
		buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		buf.memory = V4L2_MEMORY_MMAP;
		buf.index = i;
		if (ioctl(fd, VIDIOC_QUERYBUF, &buf) < 0)
			die("QUERYBUF");
		map[i] = mmap(NULL, buf.length, PROT_READ, MAP_SHARED, fd, buf.m.offset);
		if (map[i] == MAP_FAILED)
			die("mmap");
		if (ioctl(fd, VIDIOC_QBUF, &buf) < 0)
			die("QBUF");
	}
	copy = malloc(fmt.fmt.pix.sizeimage);
	if (!copy)
		die("malloc");
	make_curves(curve, sum);

	if (ioctl(fd, VIDIOC_STREAMON, &type) < 0)
		die("STREAMON");
	for (i = 0; i < frames; i++) {
		struct pollfd p = { .fd = fd, .events = POLLIN };
		int r = poll(&p, 1, 2000);

		if (r <= 0) {
			fprintf(stderr, "frame %u: %s\n", i, r ? strerror(errno) : "timed out");
			break;
		}
		memset(&buf, 0, sizeof(buf));
		buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
		buf.memory = V4L2_MEMORY_MMAP;
		if (ioctl(fd, VIDIOC_DQBUF, &buf) < 0)
			die("DQBUF");
		if (i == 0)
			start = now();
		end = now();
		if (i && buf.sequence != last_seq + 1)
			gaps += buf.sequence - last_seq - 1;
		last_seq = buf.sequence;
		if (buf.flags & V4L2_BUF_FLAG_ERROR)
			printf("frame %u: error flag\n", i);

		memcpy(copy, map[buf.index], fmt.fmt.pix.sizeimage);
		if (ioctl(fd, VIDIOC_QBUF, &buf) < 0)
			die("QBUF");

		if (means && i >= 2) {
			measure(copy, fmt.fmt.pix.bytesperline, fmt.fmt.pix.width,
				fmt.fmt.pix.height, mean, high);
			measured++;
		}
		if (bars) {
			unsigned int bad = bad_lines(copy, fmt.fmt.pix.bytesperline,
						     fmt.fmt.pix.height);

			if (bad) {
				bad_frames++;
				printf("frame %u seq %u: %u lines differ\n", i, buf.sequence, bad);
			}
		}
		if (fb) {
			draw(fb, FB_W * 4, copy, fmt.fmt.pix.bytesperline, fmt.fmt.pix.width,
			     fmt.fmt.pix.height, flip, curve, sum);
			if (!bars && red < 0 && blue < 0)
				make_curves(curve, sum);
		}
	}
	if (ioctl(fd, VIDIOC_STREAMOFF, &type) < 0)
		die("STREAMOFF");

	printf("frames %u of %u, last seq %u, frames skipped by sequence %u", i, frames, last_seq,
	       gaps);
	if (i > 1)
		printf(", %.2f delivered per second", (i - 1) / (end - start));
	printf("\n");
	if (means && measured) {
		uint64_t n = (uint64_t)measured * (fmt.fmt.pix.width / 2) * (fmt.fmt.pix.height / 2);

		printf("means over %u frames: p00 %.1f p01 %.1f p10 %.1f p11 %.1f\n", measured,
		       (double)mean[0] / n, (double)mean[1] / n, (double)mean[2] / n,
		       (double)mean[3] / n);
		printf("share near full scale: p00 %.4f p01 %.4f p10 %.4f p11 %.4f\n",
		       (double)high[0] / n, (double)high[1] / n, (double)high[2] / n,
		       (double)high[3] / n);
	}
	if (bars)
		printf("frames with a bad line %u\n", bad_frames);
	return i == frames && !bad_frames ? 0 : 1;
}
