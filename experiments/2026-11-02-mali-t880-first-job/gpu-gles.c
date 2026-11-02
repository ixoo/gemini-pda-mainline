// SPDX-License-Identifier: GPL-2.0-only
/*
 * A bounded shader test for the Mali-T880 through Mesa's Panfrost driver.
 *
 * With a surfaceless EGL context, draws a green triangle over a blue clear into
 * a small offscreen image with a compiled vertex and fragment shader, at most
 * --frames times, reading it back each time. Unlike the Write Value job, this
 * runs shaders on the GPU's cores.
 *
 * With --seconds it instead runs a sustained load for that long: every pixel of a
 * --size image runs a loop in the fragment shader, reporting the temperatures
 * every 5 s. Every frame must give the first frame's pixel, so a computing error
 * under load fails the run. With --perfcnt, a 5 s window of the GPU's counters is
 * printed raw, by block, for offline reading (needs panfrost unstable_ioctls=1).
 *
 * It stops before any frame if the SoC zone is at or above --max-mc, or the
 * optional --battery-zone at or above --battery-max-mc.
 * Exit: 0 all frames correct, 1 wrong pixels or a GL error, 2 a thermal stop,
 * 3 setup.
 */

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define SIZE		64
#define MAX_FRAMES	2000
#define MAX_LOAD_SIZE	1024
#define MAX_LOAD_SECONDS 600

/* From include/uapi/drm/panfrost_drm.h. JM, tiler, L2 and four core blocks. */
struct panfrost_perfcnt_enable {
	uint32_t enable;
	uint32_t counterset;
};
struct panfrost_perfcnt_dump {
	uint64_t buf_ptr;
};
#define IOCTL_PERFCNT_ENABLE	_IOW('d', 0x40 + 0x06, struct panfrost_perfcnt_enable)
#define IOCTL_PERFCNT_DUMP	_IOW('d', 0x40 + 0x07, struct panfrost_perfcnt_dump)
#define PERFCNT_COUNTERS	64
#define PERFCNT_BLOCKS		7
#define PERFCNT_START_MS	5000
#define PERFCNT_WINDOW_MS	5000

static const char *vs_src =
	"attribute vec2 pos;\n"
	"void main() { gl_Position = vec4(pos, 0.0, 1.0); }\n";
static const char *fs_src =
	"precision mediump float;\n"
	"uniform vec4 color;\n"
	"void main() { gl_FragColor = color; }\n";

static const char *load_fs_src =
	"precision highp float;\n"
	"uniform vec4 color;\n"
	"void main() {\n"
	/* From the pixel and a uniform, so the compiler cannot fold the loop away. */
	"  float x = color.g * 0.25 + gl_FragCoord.x * 0.001;\n"
	"  for (int i = 0; i < 32; i++)\n"
	"    x = fract(sin(x * 12.9898 + 0.5) * 43.5453);\n"
	"  gl_FragColor = vec4(color.r, x, 0.0, 1.0);\n"
	"}\n";

static int read_temp(const char *zone)
{
	FILE *f = fopen(zone, "r");
	int t = -1;

	if (f) {
		if (fscanf(f, "%d", &t) != 1)
			t = -1;
		fclose(f);
	}
	return t;
}

static GLuint compile(GLenum type, const char *src)
{
	GLuint s = glCreateShader(type);
	GLint ok = 0;
	char log[512] = "";

	glShaderSource(s, 1, &src, NULL);
	glCompileShader(s);
	glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
	if (!ok) {
		glGetShaderInfoLog(s, sizeof(log), NULL, log);
		fprintf(stderr, "shader: %s\n", log);
		exit(3);
	}
	return s;
}

/* Exit status as in the header comment. */
static void perfcnt_print(int fd, long window_us)
{
	static uint32_t buf[PERFCNT_BLOCKS * PERFCNT_COUNTERS];
	struct panfrost_perfcnt_dump dump = { .buf_ptr = (uintptr_t)buf };
	int b, c;

	if (ioctl(fd, IOCTL_PERFCNT_DUMP, &dump)) {
		printf("perfcnt dump failed\n");
		return;
	}
	printf("perfcnt window_us=%ld\n", window_us);
	for (b = 0; b < PERFCNT_BLOCKS; b++) {
		printf("perfcnt block %d:", b);
		for (c = 0; c < PERFCNT_COUNTERS; c++)
			printf(" %x", buf[b * PERFCNT_COUNTERS + c]);
		printf("\n");
	}
}

static int run_load(GLint color, int seconds, int size, const char *zone, int max_mc,
		    const char *battery, int battery_max_mc, int perfcnt)
{
	struct panfrost_perfcnt_enable en = { .enable = 1 };
	struct timespec window_start = { 0 };
	int fd = -1, window = 0;

	GLubyte first[4] = { 0 }, now[4];
	struct timespec start, b;
	long frames = 0, slowest = 0, next_report = 0, elapsed_ms, last_ms = 0;

	glViewport(0, 0, size, size);
	clock_gettime(CLOCK_MONOTONIC, &start);
	for (;;) {
		int t = read_temp(zone), bt = battery ? read_temp(battery) : 0;

		if (t < 0 || t >= max_mc || bt < 0 || (battery && bt >= battery_max_mc)) {
			printf("thermal stop after %ld frames: soc %d mC, battery %d mC\n",
			       frames, t, bt);
			return 2;
		}

		glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
		glClear(GL_COLOR_BUFFER_BIT);
		glUniform4f(color, 0.5f, 1.0f, 0.0f, 1.0f);
		glDrawArrays(GL_TRIANGLES, 0, 3);
		glFinish();
		glReadPixels(size / 2, size / 2, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, now);
		if (glGetError() != GL_NO_ERROR)
			return 1;
		if (!frames)
			memcpy(first, now, sizeof(first));
		if (memcmp(first, now, sizeof(first))) {
			printf("frame %ld: pixel %d,%d,%d, first frame gave %d,%d,%d\n", frames,
			       now[0], now[1], now[2], first[0], first[1], first[2]);
			return 1;
		}
		frames++;

		clock_gettime(CLOCK_MONOTONIC, &b);
		elapsed_ms = (b.tv_sec - start.tv_sec) * 1000 + (b.tv_nsec - start.tv_nsec) / 1000000;
		if (elapsed_ms - last_ms > slowest)
			slowest = elapsed_ms - last_ms;
		last_ms = elapsed_ms;
		if (elapsed_ms >= next_report) {
			printf("t=%lds frames=%ld soc=%d mC battery=%d mC\n", elapsed_ms / 1000,
			       frames, t, bt);
			fflush(stdout);
			next_report += 5000;
		}
		if (perfcnt && !window && elapsed_ms >= PERFCNT_START_MS) {
			fd = open("/dev/dri/renderD128", O_RDWR | O_CLOEXEC);
			if (fd < 0 || ioctl(fd, IOCTL_PERFCNT_ENABLE, &en)) {
				printf("perfcnt enable failed\n");
				perfcnt = 0;
			} else {
				clock_gettime(CLOCK_MONOTONIC, &window_start);
				window = 1;
			}
		} else if (window == 1 && elapsed_ms >= PERFCNT_START_MS + PERFCNT_WINDOW_MS) {
			clock_gettime(CLOCK_MONOTONIC, &b);
			perfcnt_print(fd, (b.tv_sec - window_start.tv_sec) * 1000000 +
				      (b.tv_nsec - window_start.tv_nsec) / 1000);
			en.enable = 0;
			ioctl(fd, IOCTL_PERFCNT_ENABLE, &en);
			close(fd);
			window = 2;
		}
		if (elapsed_ms >= seconds * 1000L)
			break;
	}

	printf("passed %ld frames in %ld ms, slowest %ld ms, pixel %d,%d,%d, soc %d mC\n", frames,
	       last_ms, slowest, first[0], first[1], first[2], read_temp(zone));
	return 0;
}

int main(int argc, char **argv)
{
	static const EGLint cfg_attr[] = {
		EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
		EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE
	};
	static const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	EGLint sur_attr[] = { EGL_WIDTH, SIZE, EGL_HEIGHT, SIZE, EGL_NONE };
	static const GLfloat tri[] = { -0.5f, -0.5f, 0.5f, -0.5f, 0.0f, 0.5f };
	static const GLfloat full[] = { -1.0f, -1.0f, 3.0f, -1.0f, -1.0f, 3.0f };
	static GLubyte px[SIZE * SIZE * 4];
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display;
	const char *zone = NULL, *battery = NULL;
	int frames = 20, max_mc = 75000, battery_max_mc = 46000, seconds = 0, size = 512, i, n;
	int perfcnt = 0;
	long max_us = 0;
	EGLConfig cfg;
	EGLDisplay d;
	EGLSurface surf;
	EGLContext ctx;
	GLuint prog;
	GLint color;

	for (i = 1; i + 1 < argc; i += 2) {
		if (!strcmp(argv[i], "--frames"))
			frames = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--max-mc"))
			max_mc = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--zone"))
			zone = argv[i + 1];
		else if (!strcmp(argv[i], "--battery-zone"))
			battery = argv[i + 1];
		else if (!strcmp(argv[i], "--battery-max-mc"))
			battery_max_mc = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--seconds"))
			seconds = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--size"))
			size = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--perfcnt"))
			perfcnt = atoi(argv[i + 1]);
	}
	if (!zone || frames < 0 || frames > MAX_FRAMES || seconds < 0 ||
	    seconds > MAX_LOAD_SECONDS || size < 16 || size > MAX_LOAD_SIZE) {
		fprintf(stderr, "need --zone, frames 0 to %d, seconds to %d, size 16 to %d\n",
			MAX_FRAMES, MAX_LOAD_SECONDS, MAX_LOAD_SIZE);
		return 3;
	}
	if (seconds) {
		sur_attr[1] = size;
		sur_attr[3] = size;
	}

	get_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
	if (!get_display)
		return 3;
	d = get_display(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	if (d == EGL_NO_DISPLAY || !eglInitialize(d, NULL, NULL) ||
	    !eglChooseConfig(d, cfg_attr, &cfg, 1, &n) || !n || !eglBindAPI(EGL_OPENGL_ES_API)) {
		fprintf(stderr, "EGL setup failed: %#x\n", eglGetError());
		return 3;
	}
	surf = eglCreatePbufferSurface(d, cfg, sur_attr);
	ctx = eglCreateContext(d, cfg, EGL_NO_CONTEXT, ctx_attr);
	if (surf == EGL_NO_SURFACE || ctx == EGL_NO_CONTEXT || !eglMakeCurrent(d, surf, surf, ctx)) {
		fprintf(stderr, "EGL context failed: %#x\n", eglGetError());
		return 3;
	}
	printf("renderer=%s version=%s\n", glGetString(GL_RENDERER), glGetString(GL_VERSION));
	if (!strstr((const char *)glGetString(GL_RENDERER), "T880")) {
		fprintf(stderr, "not the Mali-T880\n");
		return 3;
	}

	prog = glCreateProgram();
	glAttachShader(prog, compile(GL_VERTEX_SHADER, vs_src));
	glAttachShader(prog, compile(GL_FRAGMENT_SHADER, seconds ? load_fs_src : fs_src));
	glBindAttribLocation(prog, 0, "pos");
	glLinkProgram(prog);
	glUseProgram(prog);
	color = glGetUniformLocation(prog, "color");
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, seconds ? full : tri);
	glEnableVertexAttribArray(0);
	glViewport(0, 0, SIZE, SIZE);

	if (seconds)
		return run_load(color, seconds, size, zone, max_mc, battery, battery_max_mc, perfcnt);

	for (i = 0; i < frames; i++) {
		/* The red channel changes per frame, so a stale image fails. */
		GLubyte red = (GLubyte)(i * 7 % 200 + 20);
		const GLubyte *mid = px + (SIZE / 2 * SIZE + SIZE / 2) * 4, *corner = px;
		struct timespec a, b;
		int t = read_temp(zone);
		long us;

		if (t < 0 || t >= max_mc) {
			printf("thermal stop before frame %d: %d mC\n", i, t);
			return 2;
		}

		clock_gettime(CLOCK_MONOTONIC, &a);
		glClearColor(0.0f, 0.0f, 1.0f, 1.0f);
		glClear(GL_COLOR_BUFFER_BIT);
		glUniform4f(color, red / 255.0f, 1.0f, 0.0f, 1.0f);
		glDrawArrays(GL_TRIANGLES, 0, 3);
		glFinish();
		glReadPixels(0, 0, SIZE, SIZE, GL_RGBA, GL_UNSIGNED_BYTE, px);
		clock_gettime(CLOCK_MONOTONIC, &b);
		us = (b.tv_sec - a.tv_sec) * 1000000 + (b.tv_nsec - a.tv_nsec) / 1000;
		if (us > max_us)
			max_us = us;

		if (glGetError() != GL_NO_ERROR || mid[0] < red - 2 || mid[0] > red + 2 ||
		    mid[1] != 255 || mid[2] != 0 || corner[0] != 0 || corner[1] != 0 ||
		    corner[2] != 255) {
			printf("frame %d: wrong: mid %d,%d,%d corner %d,%d,%d, wanted red %d\n", i,
			       mid[0], mid[1], mid[2], corner[0], corner[1], corner[2], red);
			return 1;
		}
		if (i == 0 || i == frames - 1)
			printf("frame %d: ok in %ld us, %d mC\n", i, us, t);
	}

	printf("passed %d of %d frames, slowest %ld us, %d mC\n", i, frames, max_us, read_temp(zone));
	return 0;
}
