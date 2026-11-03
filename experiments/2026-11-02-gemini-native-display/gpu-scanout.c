// SPDX-License-Identifier: GPL-2.0-only
/*
 * Render with the Mali through Mesa's Panfrost and show it on the panel: buffers
 * come from the display driver as dumb buffers, the GPU draws into them through
 * dma-buf, and the display scans them out with page flips. The display side has no
 * IOMMU here, so its buffers must be contiguous, which is why the display allocates
 * them and the GPU imports them. The GPU has its own MMU and can map them.
 *
 * It draws a slowly turning triangle, red, green and blue at its corners, in a
 * shader over a dark blue clear, plus a white band that sweeps along the long side.
 *
 * usage: gpu-scanout SECONDS SOC_ZONE_TEMP_FILE MAX_MC
 * Exit: 0 ran for SECONDS, 1 a failure, 2 a thermal stop.
 */
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

#define MAX_RES 16
#define FOURCC_XR24 0x34325258
/* Panfrost wants a linear render target's stride on 64 bytes, as the loader's is. */
#define DUMB_WIDTH(w) (((w) + 15) & ~15u)

struct buf {
	uint32_t handle, fb, pitch;
	int fd;
	EGLImageKHR image;
	GLuint rb, fbo;
};

static int drm_fd;

static void die(const char *what)
{
	fprintf(stderr, "%s: %s\n", what, strerror(errno));
	exit(1);
}

static void die_egl(const char *what)
{
	fprintf(stderr, "%s: egl 0x%x gl 0x%x\n", what, eglGetError(), glGetError());
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

static double now(void)
{
	struct timespec t;

	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec + t.tv_nsec / 1e9;
}

static int read_mc(const char *path)
{
	FILE *f = fopen(path, "r");
	int mc = -1;

	if (f) {
		if (fscanf(f, "%d", &mc) != 1)
			mc = -1;
		fclose(f);
	}
	return mc;
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
			printf("display %s\n", path);
			return 0;
		}
		close(fd);
	}
	return -1;
}

static void make_buf(struct buf *b, const struct drm_mode_modeinfo *m)
{
	struct drm_mode_create_dumb c = {
		.width = DUMB_WIDTH(m->hdisplay), .height = m->vdisplay, .bpp = 32,
	};
	struct drm_mode_fb_cmd f = { 0 };
	struct drm_prime_handle p = { 0 };

	if (xioctl(DRM_IOCTL_MODE_CREATE_DUMB, &c))
		die("CREATE_DUMB");
	b->handle = c.handle;
	b->pitch = c.pitch;
	f.width = m->hdisplay;
	f.height = m->vdisplay;
	f.pitch = c.pitch;
	f.bpp = 32;
	f.depth = 24;
	f.handle = c.handle;
	if (xioctl(DRM_IOCTL_MODE_ADDFB, &f))
		die("ADDFB");
	b->fb = f.fb_id;
	p.handle = c.handle;
	p.flags = DRM_CLOEXEC | DRM_RDWR;
	if (xioctl(DRM_IOCTL_PRIME_HANDLE_TO_FD, &p))
		die("PRIME_HANDLE_TO_FD");
	b->fd = p.fd;
}

static GLuint shader(GLenum type, const char *src)
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
		exit(1);
	}
	return s;
}

int main(int argc, char **argv)
{
	static const char *vs =
		"attribute vec2 pos;\nattribute vec3 col;\nvarying vec3 v;\nuniform float a;\n"
		"void main() {\n"
		"  float c = cos(a), s = sin(a);\n"
		"  v = col;\n"
		"  gl_Position = vec4((c * pos.x - s * pos.y) * 0.8, (s * pos.x + c * pos.y) * 0.4, 0.0, 1.0);\n"
		"}\n";
	static const char *fs =
		"precision mediump float;\nvarying vec3 v;\n"
		"void main() { gl_FragColor = vec4(v, 1.0); }\n";
	static const char *band_fs =
		"precision mediump float;\nvoid main() { gl_FragColor = vec4(1.0); }\n";
	static const GLfloat tri[] = {
		0.0, 1.0, 1.0, 0.0, 0.0,
		-0.87, -0.5, 0.0, 1.0, 0.0,
		0.87, -0.5, 0.0, 0.0, 1.0,
	};
	uint32_t crtcs[MAX_RES], conns[MAX_RES], encs[MAX_RES], conn_id = 0;
	struct drm_mode_card_res r = { 0 };
	struct drm_mode_modeinfo mode, modes[8];
	struct drm_mode_get_connector gc = { 0 };
	struct drm_mode_get_encoder ge = { 0 };
	struct drm_mode_crtc sc = { 0 };
	struct buf b[2];
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display;
	PFNEGLCREATEIMAGEKHRPROC create_image;
	PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC target;
	EGLDisplay d;
	EGLConfig cfg;
	EGLint n;
	EGLSurface surf;
	EGLContext ctx;
	GLuint prog, band;
	GLint a_loc;
	unsigned int front = 0, frames = 0, late = 0;
	double start, last_check = 0, draw = 0, worst = 0;
	int seconds, max_mc, status = 0;
	const char *zone;

	if (argc != 4 || (seconds = atoi(argv[1])) <= 0) {
		fprintf(stderr, "usage: gpu-scanout SECONDS SOC_ZONE_TEMP_FILE MAX_MC\n");
		return 1;
	}
	zone = argv[2];
	max_mc = atoi(argv[3]);
	if (read_mc(zone) < 0 || read_mc(zone) >= max_mc) {
		fprintf(stderr, "too hot or no zone: %d\n", read_mc(zone));
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
		memset(&gc, 0, sizeof(gc));
		gc.connector_id = conns[i];
		if (xioctl(DRM_IOCTL_MODE_GETCONNECTOR, &gc))
			die("GETCONNECTOR");
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
		fprintf(stderr, "no CRTC\n");
		return 1;
	}
	make_buf(&b[0], &mode);
	make_buf(&b[1], &mode);
	printf("mode %ux%u pitch %u\n", mode.hdisplay, mode.vdisplay, b[0].pitch);

	get_display = (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
	d = get_display(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	if (d == EGL_NO_DISPLAY || !eglInitialize(d, NULL, NULL) || !eglBindAPI(EGL_OPENGL_ES_API))
		die_egl("eglInitialize");
	{
		static const EGLint cfg_attr[] = {
			EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
			EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_NONE,
		};
		static const EGLint sur_attr[] = { EGL_WIDTH, 16, EGL_HEIGHT, 16, EGL_NONE };
		static const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };

		if (!eglChooseConfig(d, cfg_attr, &cfg, 1, &n) || n != 1)
			die_egl("eglChooseConfig");
		surf = eglCreatePbufferSurface(d, cfg, sur_attr);
		ctx = eglCreateContext(d, cfg, EGL_NO_CONTEXT, ctx_attr);
		if (surf == EGL_NO_SURFACE || ctx == EGL_NO_CONTEXT ||
		    !eglMakeCurrent(d, surf, surf, ctx))
			die_egl("eglMakeCurrent");
	}
	printf("renderer %s\n", glGetString(GL_RENDERER));
	create_image = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	target = (PFNGLEGLIMAGETARGETRENDERBUFFERSTORAGEOESPROC)
		eglGetProcAddress("glEGLImageTargetRenderbufferStorageOES");
	if (!create_image || !target)
		die_egl("no dma-buf import entry points");
	for (int i = 0; i < 2; i++) {
		EGLint attr[] = {
			EGL_WIDTH, mode.hdisplay, EGL_HEIGHT, mode.vdisplay,
			EGL_LINUX_DRM_FOURCC_EXT, FOURCC_XR24,
			EGL_DMA_BUF_PLANE0_FD_EXT, b[i].fd,
			EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
			EGL_DMA_BUF_PLANE0_PITCH_EXT, (EGLint)b[i].pitch,
			EGL_NONE,
		};

		b[i].image = create_image(d, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL, attr);
		if (b[i].image == EGL_NO_IMAGE_KHR)
			die_egl("eglCreateImageKHR");
		glGenRenderbuffers(1, &b[i].rb);
		glBindRenderbuffer(GL_RENDERBUFFER, b[i].rb);
		target(GL_RENDERBUFFER, b[i].image);
		glGenFramebuffers(1, &b[i].fbo);
		glBindFramebuffer(GL_FRAMEBUFFER, b[i].fbo);
		glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, b[i].rb);
		status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
		if (status != GL_FRAMEBUFFER_COMPLETE) {
			fprintf(stderr, "framebuffer status 0x%x\n", status);
			return 1;
		}
	}

	prog = glCreateProgram();
	glAttachShader(prog, shader(GL_VERTEX_SHADER, vs));
	glAttachShader(prog, shader(GL_FRAGMENT_SHADER, fs));
	glBindAttribLocation(prog, 0, "pos");
	glBindAttribLocation(prog, 1, "col");
	glLinkProgram(prog);
	a_loc = glGetUniformLocation(prog, "a");
	band = glCreateProgram();
	glAttachShader(band, shader(GL_VERTEX_SHADER, "attribute vec2 pos;\nvoid main() { gl_Position = vec4(pos, 0.0, 1.0); }\n"));
	glAttachShader(band, shader(GL_FRAGMENT_SHADER, band_fs));
	glBindAttribLocation(band, 0, "pos");
	glLinkProgram(band);
	glViewport(0, 0, mode.hdisplay, mode.vdisplay);
	glEnableVertexAttribArray(0);

	start = now();
	sc.set_connectors_ptr = (uintptr_t)&conn_id;
	sc.count_connectors = 1;
	sc.mode = mode;
	sc.mode_valid = 1;

	while (now() - start < seconds) {
		struct buf *back = &b[!front];
		double t0 = now(), t = t0 - start, y = 2.0 * fmod(t / 4.0, 1.0) - 1.0, dt;
		GLfloat strip[] = { -1, (GLfloat)y, 1, (GLfloat)y, -1, (GLfloat)y + 0.03f, 1, (GLfloat)y + 0.03f };

		glBindFramebuffer(GL_FRAMEBUFFER, back->fbo);
		glClearColor(0.0, 0.0, 0.25, 1.0);
		glClear(GL_COLOR_BUFFER_BIT);
		glUseProgram(prog);
		glUniform1f(a_loc, (GLfloat)t);
		glEnableVertexAttribArray(1);
		glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(GLfloat), tri);
		glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(GLfloat), tri + 2);
		glDrawArrays(GL_TRIANGLES, 0, 3);
		glDisableVertexAttribArray(1);
		glUseProgram(band);
		glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, strip);
		glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
		glFinish();
		if (glGetError() != GL_NO_ERROR)
			die_egl("draw");
		dt = now() - t0;
		draw += dt;
		if (dt > worst)
			worst = dt;

		if (!frames) {
			sc.fb_id = back->fb;
			if (xioctl(DRM_IOCTL_MODE_SETCRTC, &sc))
				die("SETCRTC");
			printf("first frame set after %.3f s\n", now() - start);
			fflush(stdout);
		} else {
			struct drm_mode_crtc_page_flip pf = {
				.crtc_id = sc.crtc_id, .fb_id = back->fb,
				.flags = DRM_MODE_PAGE_FLIP_EVENT,
			};
			struct pollfd p = { .fd = drm_fd, .events = POLLIN };
			char ev[256];

			if (xioctl(DRM_IOCTL_MODE_PAGE_FLIP, &pf))
				die("PAGE_FLIP");
			if (poll(&p, 1, 1000) != 1) {
				late++;
				fprintf(stderr, "flip event late after %u frames\n", frames);
				break;
			}
			if (read(drm_fd, ev, sizeof(ev)) <= 0)
				die("read event");
		}
		front = !front;
		frames++;

		if (t - last_check >= 1.0) {
			int mc = read_mc(zone);

			last_check = t;
			if (mc >= max_mc) {
				printf("thermal stop at %d mC after %u frames\n", mc, frames);
				return 2;
			}
		}
	}
	printf("frames %u in %.3f s, %.2f per second, draw mean %.2f ms worst %.2f ms, late %u, soc %d mC\n",
	       frames, now() - start, frames / (now() - start), 1000 * draw / frames, 1000 * worst, late,
	       read_mc(zone));
	return late ? 1 : 0;
}
