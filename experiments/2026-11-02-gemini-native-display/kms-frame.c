// SPDX-License-Identifier: MIT
/*
 * Put a test frame on the first connected DRM output and hold it, flipping
 * between two buffers to measure the refresh rate. Raw ioctls, so it builds
 * static with no libdrm:
 *
 *   aarch64-linux-gnu-gcc -O2 -static -o kms-frame kms-frame.c
 *
 * usage: kms-frame SECONDS
 *
 * The frame has eight colour bars across the scan direction, a white border, and
 * one solid square per corner: red at the start of the first scan line, green at
 * its end, blue at the start of the last line, white at its end. A black block
 * moves along the middle while it holds. It exits non-zero if a flip event is
 * late, and closing the device disables the output.
 */
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

#define MAX_RES 16

struct buf {
	uint32_t handle, fb, pitch;
	uint64_t size;
	uint32_t *map;
};

static int drm_fd;

static void die(const char *what)
{
	fprintf(stderr, "%s: %s\n", what, strerror(errno));
	exit(1);
}

static int xioctl(unsigned long req, void *arg)
{
	int ret;

	do {
		ret = ioctl(drm_fd, req, arg);
	} while (ret < 0 && (errno == EINTR || errno == EAGAIN));
	return ret;
}

static uint32_t pixel(int x, int y, int w, int h)
{
	static const uint32_t bars[8] = {
		0xffffff, 0xffff00, 0x00ffff, 0x00ff00,
		0xff00ff, 0xff0000, 0x0000ff, 0x404040,
	};
	const int c = 120;

	if (x < 4 || y < 4 || x >= w - 4 || y >= h - 4)
		return 0xffffff;
	if (y < c && x < c)
		return 0xff0000;
	if (y < c && x >= w - c)
		return 0x00ff00;
	if (y >= h - c && x < c)
		return 0x0000ff;
	if (y >= h - c && x >= w - c)
		return 0xffffff;
	return bars[y * 8 / h];
}

static void draw(struct buf *b, int w, int h)
{
	for (int y = 0; y < h; y++)
		for (int x = 0; x < w; x++)
			b->map[y * (b->pitch / 4) + x] = pixel(x, y, w, h);
}

/* Only the block's rows, so a flip is not held up by drawing a whole frame. */
static void draw_block(struct buf *b, int w, int h, int pos, int black)
{
	for (int y = pos; y < pos + 60 && y < h; y++)
		for (int x = w / 2 - 60; x < w / 2 + 60; x++)
			b->map[y * (b->pitch / 4) + x] = black ? 0 : pixel(x, y, w, h);
}

static void make_buf(struct buf *b, const struct drm_mode_modeinfo *m)
{
	struct drm_mode_create_dumb c = {
		.width = m->hdisplay, .height = m->vdisplay, .bpp = 32,
	};
	struct drm_mode_fb_cmd f = { 0 };
	struct drm_mode_map_dumb d = { 0 };

	if (xioctl(DRM_IOCTL_MODE_CREATE_DUMB, &c))
		die("CREATE_DUMB");
	b->handle = c.handle;
	b->pitch = c.pitch;
	b->size = c.size;
	f.width = m->hdisplay;
	f.height = m->vdisplay;
	f.pitch = c.pitch;
	f.bpp = 32;
	f.depth = 24;
	f.handle = c.handle;
	if (xioctl(DRM_IOCTL_MODE_ADDFB, &f))
		die("ADDFB");
	b->fb = f.fb_id;
	d.handle = c.handle;
	if (xioctl(DRM_IOCTL_MODE_MAP_DUMB, &d))
		die("MAP_DUMB");
	b->map = mmap(NULL, c.size, PROT_READ | PROT_WRITE, MAP_SHARED, drm_fd, d.offset);
	if (b->map == MAP_FAILED)
		die("mmap");
}

static int open_kms(void)
{
	for (int i = 0; i < 8; i++) {
		char path[32];
		struct drm_mode_card_res r = { 0 };
		int fd;

		snprintf(path, sizeof(path), "/dev/dri/card%d", i);
		fd = open(path, O_RDWR | O_CLOEXEC);
		if (fd < 0)
			continue;
		drm_fd = fd;
		if (!xioctl(DRM_IOCTL_MODE_GETRESOURCES, &r) && r.count_crtcs && r.count_connectors) {
			printf("device %s\n", path);
			return 0;
		}
		close(fd);
	}
	return -1;
}

static double now(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char **argv)
{
	uint32_t crtcs[MAX_RES], conns[MAX_RES], encs[MAX_RES];
	struct drm_mode_card_res r = { 0 };
	struct drm_mode_modeinfo mode, modes[8];
	struct drm_mode_get_connector gc = { 0 };
	struct drm_mode_get_encoder ge = { 0 };
	struct drm_mode_crtc sc = { 0 };
	struct buf b[2];
	uint32_t conn_id = 0;
	unsigned int front = 0, flips = 0, late = 0;
	double start, end;
	int pos[2] = { 0 }, last[2] = { 0 };
	int seconds;

	if (argc != 2 || (seconds = atoi(argv[1])) <= 0) {
		fprintf(stderr, "usage: kms-frame SECONDS\n");
		return 2;
	}
	if (open_kms())
		die("no KMS device");

	r.crtc_id_ptr = (uintptr_t)crtcs;
	r.connector_id_ptr = (uintptr_t)conns;
	r.encoder_id_ptr = (uintptr_t)encs;
	r.count_crtcs = r.count_connectors = r.count_encoders = MAX_RES;
	if (xioctl(DRM_IOCTL_MODE_GETRESOURCES, &r))
		die("GETRESOURCES");

	for (unsigned int i = 0; i < r.count_connectors && !conn_id; i++) {
		/* Only a call asking for no modes makes the kernel probe the connector. */
		memset(&gc, 0, sizeof(gc));
		gc.connector_id = conns[i];
		if (xioctl(DRM_IOCTL_MODE_GETCONNECTOR, &gc))
			die("GETCONNECTOR");
		printf("connector %u connection %u modes %u\n", conns[i], gc.connection, gc.count_modes);
		if (gc.connection != 1 || !gc.count_modes)
			continue;
		if (gc.count_modes > 8)
			gc.count_modes = 8;
		gc.modes_ptr = (uintptr_t)modes;
		gc.count_props = gc.count_encoders = 0;
		if (xioctl(DRM_IOCTL_MODE_GETCONNECTOR, &gc))
			die("GETCONNECTOR");
		conn_id = conns[i];
	}
	if (!conn_id) {
		fprintf(stderr, "no connected output\n");
		return 1;
	}
	mode = modes[0];
	printf("connector %u mode %s clock %u h %u %u %u %u v %u %u %u %u vrefresh %u\n", conn_id,
	       mode.name, mode.clock, mode.hdisplay, mode.hsync_start, mode.hsync_end, mode.htotal,
	       mode.vdisplay, mode.vsync_start, mode.vsync_end, mode.vtotal, mode.vrefresh);

	ge.encoder_id = gc.encoder_id ? gc.encoder_id : encs[0];
	if (xioctl(DRM_IOCTL_MODE_GETENCODER, &ge))
		die("GETENCODER");
	for (unsigned int i = 0; i < r.count_crtcs; i++) {
		if (ge.possible_crtcs & (1u << i)) {
			sc.crtc_id = crtcs[i];
			break;
		}
	}
	if (!sc.crtc_id) {
		fprintf(stderr, "no CRTC for the encoder\n");
		return 1;
	}

	make_buf(&b[0], &mode);
	make_buf(&b[1], &mode);
	printf("buffers pitch %u size %llu\n", b[0].pitch, (unsigned long long)b[0].size);
	draw(&b[0], mode.hdisplay, mode.vdisplay);
	draw(&b[1], mode.hdisplay, mode.vdisplay);

	sc.set_connectors_ptr = (uintptr_t)&conn_id;
	sc.count_connectors = 1;
	sc.fb_id = b[0].fb;
	sc.mode = mode;
	sc.mode_valid = 1;
	start = now();
	if (xioctl(DRM_IOCTL_MODE_SETCRTC, &sc))
		die("SETCRTC");
	printf("modeset done in %.3f s\n", now() - start);
	fflush(stdout);

	start = now();
	while (now() - start < seconds) {
		struct drm_mode_crtc_page_flip pf = {
			.crtc_id = sc.crtc_id,
			.fb_id = b[!front].fb,
			.flags = DRM_MODE_PAGE_FLIP_EVENT,
		};
		struct pollfd p = { .fd = drm_fd, .events = POLLIN };
		char ev[256];

		pos[!front] = (flips * 8) % (mode.vdisplay - 60);
		if (flips > 1)
			draw_block(&b[!front], mode.hdisplay, mode.vdisplay, last[!front], 0);
		draw_block(&b[!front], mode.hdisplay, mode.vdisplay, pos[!front], 1);
		last[!front] = pos[!front];
		if (xioctl(DRM_IOCTL_MODE_PAGE_FLIP, &pf))
			die("PAGE_FLIP");
		if (poll(&p, 1, 1000) != 1) {
			late++;
			fprintf(stderr, "flip event late after %u flips\n", flips);
			break;
		}
		if (read(drm_fd, ev, sizeof(ev)) <= 0)
			die("read event");
		front = !front;
		flips++;
	}
	end = now();
	printf("flips %u in %.3f s, %.2f per second, late %u\n", flips, end - start,
	       flips / (end - start), late);
	return late ? 1 : 0;
}
