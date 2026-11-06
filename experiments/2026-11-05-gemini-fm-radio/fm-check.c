// SPDX-License-Identifier: GPL-2.0-only
/*
 * F3 check for the MT6797 FM receiver's V4L2 radio device.
 *
 * Usage: fm-check DEVICE FREQ_KHZ SECONDS PRIVATE_FILE [seek]
 *
 * Public lines go to stdout: capabilities, control results, one line a second
 * with signal strength, stereo and RDS block counts, and seek timing. Anything
 * that identifies the station or the place goes only to PRIVATE_FILE: the
 * frequency, the frequency a seek found, the RDS PI code and programme name.
 *
 * VIDIOC_LOG_STATUS is called at t=5, after the last second and after the seek;
 * the driver then logs the stereo registers and the channel's quality report to
 * the kernel log, without the channel.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <linux/videodev2.h>

static FILE *priv;

static double now(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static int set_ctrl(int fd, unsigned int id, int value, const char *name)
{
	struct v4l2_control c = { .id = id, .value = value };
	int ret = ioctl(fd, VIDIOC_S_CTRL, &c);

	printf("ctrl %s=%d: %s\n", name, value, ret ? strerror(errno) : "ok");
	return ret;
}

int main(int argc, char **argv)
{
	unsigned int good[5] = { 0 }, bad[5] = { 0 }, pi = 0, pi_count = 0, t, i;
	char ps[9] = "        ";
	struct v4l2_capability cap = { 0 };
	struct v4l2_tuner tuner = { 0 };
	struct v4l2_frequency freq = { 0 };
	int fd, seconds;
	unsigned long khz;

	if (argc < 5) {
		fprintf(stderr, "usage: %s DEVICE FREQ_KHZ SECONDS PRIVATE_FILE [seek]\n", argv[0]);
		return 2;
	}
	khz = strtoul(argv[2], NULL, 10);
	seconds = atoi(argv[3]);
	priv = fopen(argv[4], "w");
	if (!priv) {
		perror("private file");
		return 1;
	}

	double t0 = now();

	fd = open(argv[1], O_RDWR | O_NONBLOCK);
	printf("open: %s after %.2f s\n", fd < 0 ? strerror(errno) : "ok", now() - t0);
	if (fd < 0)
		return 1;
	if (!ioctl(fd, VIDIOC_QUERYCAP, &cap))
		printf("cap: driver=%s card=%s caps=%08x\n", cap.driver, cap.card, cap.device_caps);
	if (!ioctl(fd, VIDIOC_G_TUNER, &tuner))
		printf("tuner: %s cap=%08x range=%u-%u kHz audmode=%u\n", tuner.name,
		       tuner.capability, tuner.rangelow / 16, tuner.rangehigh / 16, tuner.audmode);

	set_ctrl(fd, V4L2_CID_AUDIO_MUTE, 1, "mute");
	set_ctrl(fd, V4L2_CID_AUDIO_MUTE, 0, "mute");
	set_ctrl(fd, V4L2_CID_AUDIO_VOLUME, 15, "volume");
	set_ctrl(fd, V4L2_CID_TUNE_DEEMPHASIS, V4L2_DEEMPHASIS_75_uS, "deemphasis");

	freq.type = V4L2_TUNER_RADIO;
	freq.frequency = khz * 16;
	t0 = now();
	printf("s_frequency: %s after %.2f s\n",
	       ioctl(fd, VIDIOC_S_FREQUENCY, &freq) ? strerror(errno) : "ok", now() - t0);
	memset(&freq, 0, sizeof(freq));
	if (!ioctl(fd, VIDIOC_G_FREQUENCY, &freq))
		fprintf(priv, "tuned %u kHz (asked %lu)\n", freq.frequency / 16, khz);

	for (t = 1; t <= (unsigned int)seconds; t++) {
		struct v4l2_rds_data rds[64];
		unsigned int g = 0, b = 0;
		ssize_t n;

		sleep(1);
		while ((n = read(fd, rds, sizeof(rds))) > 0) {
			for (i = 0; i < n / sizeof(rds[0]); i++) {
				unsigned int id = rds[i].block & V4L2_RDS_BLOCK_MSK;
				unsigned int v = rds[i].msb << 8 | rds[i].lsb;

				if (id > 4)
					continue;
				if (rds[i].block & V4L2_RDS_BLOCK_ERROR) {
					bad[id]++;
					b++;
					continue;
				}
				good[id]++;
				g++;
				if (id == 0) {
					pi = v;
					pi_count++;
				}
				/* Group 0A/0B: block D carries two PS characters. */
				if (id == 3 && i >= 2 &&
				    (rds[i - 2].block & V4L2_RDS_BLOCK_MSK) == 1 &&
				    !(rds[i - 2].block & V4L2_RDS_BLOCK_ERROR) &&
				    (rds[i - 2].msb >> 4) == 0) {
					unsigned int seg = rds[i - 2].lsb & 3;

					ps[2 * seg] = rds[i].msb;
					ps[2 * seg + 1] = rds[i].lsb;
				}
			}
		}
		memset(&tuner, 0, sizeof(tuner));
		ioctl(fd, VIDIOC_G_TUNER, &tuner);
		printf("t=%u signal=%u stereo=%u rds=%u blocks good=%u bad=%u\n", t, tuner.signal,
		       !!(tuner.rxsubchans & V4L2_TUNER_SUB_STEREO),
		       !!(tuner.rxsubchans & V4L2_TUNER_SUB_RDS), g, b);
		if (t == 5)
			printf("log_status at t=5: %s\n",
			       ioctl(fd, VIDIOC_LOG_STATUS) ? strerror(errno) : "ok");
	}
	printf("log_status at end: %s\n", ioctl(fd, VIDIOC_LOG_STATUS) ? strerror(errno) : "ok");
	printf("rds totals: good A=%u B=%u C=%u D=%u C'=%u, bad A=%u B=%u C=%u D=%u C'=%u, PI seen %u times\n",
	       good[0], good[1], good[2], good[3], good[4], bad[0], bad[1], bad[2], bad[3], bad[4],
	       pi_count);
	fprintf(priv, "PI %04x, PS \"%s\"\n", pi, ps);

	if (argc > 5 && !strcmp(argv[5], "seek")) {
		struct v4l2_hw_freq_seek seek = {
			.type = V4L2_TUNER_RADIO, .seek_upward = 1, .wrap_around = 1,
		};
		int ret;

		/* Seek needs a blocking file. */
		fcntl(fd, F_SETFL, 0);
		t0 = now();
		ret = ioctl(fd, VIDIOC_S_HW_FREQ_SEEK, &seek);
		printf("seek up: %s after %.2f s\n", ret ? strerror(errno) : "ok", now() - t0);
		memset(&freq, 0, sizeof(freq));
		if (!ioctl(fd, VIDIOC_G_FREQUENCY, &freq))
			fprintf(priv, "seek found %u kHz\n", freq.frequency / 16);
		memset(&tuner, 0, sizeof(tuner));
		ioctl(fd, VIDIOC_G_TUNER, &tuner);
		printf("after seek: signal=%u stereo=%u\n", tuner.signal,
		       !!(tuner.rxsubchans & V4L2_TUNER_SUB_STEREO));
		printf("log_status after seek: %s\n",
		       ioctl(fd, VIDIOC_LOG_STATUS) ? strerror(errno) : "ok");
	}

	t0 = now();
	close(fd);
	printf("close after %.2f s\n", now() - t0);
	fclose(priv);
	return 0;
}
