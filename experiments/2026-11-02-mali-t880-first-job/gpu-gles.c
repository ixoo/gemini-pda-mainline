// SPDX-License-Identifier: GPL-2.0-only
/*
 * A bounded shader test for the Mali-T880 through Mesa's Panfrost driver.
 *
 * With a surfaceless EGL context, draws a green triangle over a blue clear into
 * a small offscreen image with a compiled vertex and fragment shader, at most
 * --frames times, reading it back each time. Unlike the Write Value job, this
 * runs shaders on the GPU's cores.
 *
 * It stops before any frame if the SoC zone is at or above --max-mc.
 * Exit: 0 all frames correct, 1 wrong pixels or a GL error, 2 a thermal stop,
 * 3 setup.
 */

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define SIZE		64
#define MAX_FRAMES	2000

static const char *vs_src =
	"attribute vec2 pos;\n"
	"void main() { gl_Position = vec4(pos, 0.0, 1.0); }\n";
static const char *fs_src =
	"precision mediump float;\n"
	"uniform vec4 color;\n"
	"void main() { gl_FragColor = color; }\n";

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

int main(int argc, char **argv)
{
	static const EGLint cfg_attr[] = {
		EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
		EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE
	};
	static const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	static const EGLint sur_attr[] = { EGL_WIDTH, SIZE, EGL_HEIGHT, SIZE, EGL_NONE };
	static const GLfloat tri[] = { -0.5f, -0.5f, 0.5f, -0.5f, 0.0f, 0.5f };
	static GLubyte px[SIZE * SIZE * 4];
	PFNEGLGETPLATFORMDISPLAYEXTPROC get_display;
	const char *zone = NULL;
	int frames = 20, max_mc = 65000, i, n;
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
	}
	if (!zone || frames < 0 || frames > MAX_FRAMES) {
		fprintf(stderr, "need --zone, and frames 0 to %d\n", MAX_FRAMES);
		return 3;
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
	glAttachShader(prog, compile(GL_FRAGMENT_SHADER, fs_src));
	glBindAttribLocation(prog, 0, "pos");
	glLinkProgram(prog);
	glUseProgram(prog);
	color = glGetUniformLocation(prog, "color");
	glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, tri);
	glEnableVertexAttribArray(0);
	glViewport(0, 0, SIZE, SIZE);

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
