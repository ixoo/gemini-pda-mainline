// SPDX-License-Identifier: GPL-2.0-only
/*
 * F5: play the MT6797 FM receiver on the headphones.
 *
 * Usage: fm-listen RADIO FREQ_KHZ VOLUME SECONDS PRIVATE_FILE
 *
 * Opens the radio, sets its volume (0-15) and tunes, then starts the card's
 * Hostless_FM front end in both directions with raw ALSA ioctls: capture starts
 * the CONNSYS I2S input, playback the downlink to the codec. No sample is
 * written or read; the hardware carries the audio. Every 5 s it prints the
 * tuner's signal and stereo flag. Then it stops both streams and closes.
 *
 * The frequency goes only to PRIVATE_FILE; stdout carries no station identity.
 */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <sound/asound.h>

static struct snd_mask *mask(struct snd_pcm_hw_params *p, int n)
{
	return &p->masks[n - SNDRV_PCM_HW_PARAM_FIRST_MASK];
}

static struct snd_interval *interval(struct snd_pcm_hw_params *p, int n)
{
	return &p->intervals[n - SNDRV_PCM_HW_PARAM_FIRST_INTERVAL];
}

static void set_mask(struct snd_pcm_hw_params *p, int n, unsigned int bit)
{
	struct snd_mask *m = mask(p, n);

	memset(m, 0, sizeof(*m));
	m->bits[bit >> 5] |= 1U << (bit & 31);
}

static void set_int(struct snd_pcm_hw_params *p, int n, unsigned int v)
{
	struct snd_interval *i = interval(p, n);

	i->min = v;
	i->max = v;
	i->integer = 1;
}

/* The Hostless_FM device number on the first card, from /proc/asound/pcm. */
static int find_device(int *card, int *dev)
{
	char line[256];
	FILE *f = fopen("/proc/asound/pcm", "r");
	int found = 0;

	if (!f)
		return -1;
	while (fgets(line, sizeof(line), f))
		if (strstr(line, "Hostless_FM") && sscanf(line, "%d-%d", card, dev) == 2) {
			found = 1;
			break;
		}
	fclose(f);
	return found ? 0 : -1;
}

static int pcm_open(int card, int dev, char dir)
{
	struct snd_pcm_hw_params hw;
	struct snd_pcm_sw_params sw;
	char path[64];
	int fd, n;

	snprintf(path, sizeof(path), "/dev/snd/pcmC%dD%d%c", card, dev, dir);
	fd = open(path, (dir == 'p' ? O_WRONLY : O_RDONLY) | O_NONBLOCK);
	if (fd < 0) {
		printf("open %c: %s\n", dir, strerror(errno));
		return -1;
	}
	memset(&hw, 0, sizeof(hw));
	for (n = SNDRV_PCM_HW_PARAM_FIRST_MASK; n <= SNDRV_PCM_HW_PARAM_LAST_MASK; n++)
		memset(mask(&hw, n), 0xff, sizeof(struct snd_mask));
	for (n = SNDRV_PCM_HW_PARAM_FIRST_INTERVAL; n <= SNDRV_PCM_HW_PARAM_LAST_INTERVAL; n++) {
		interval(&hw, n)->min = 0;
		interval(&hw, n)->max = UINT_MAX;
	}
	hw.rmask = ~0U;
	set_mask(&hw, SNDRV_PCM_HW_PARAM_ACCESS, SNDRV_PCM_ACCESS_RW_INTERLEAVED);
	set_mask(&hw, SNDRV_PCM_HW_PARAM_FORMAT, SNDRV_PCM_FORMAT_S16_LE);
	set_mask(&hw, SNDRV_PCM_HW_PARAM_SUBFORMAT, SNDRV_PCM_SUBFORMAT_STD);
	set_int(&hw, SNDRV_PCM_HW_PARAM_CHANNELS, 2);
	set_int(&hw, SNDRV_PCM_HW_PARAM_RATE, 48000);
	set_int(&hw, SNDRV_PCM_HW_PARAM_PERIOD_SIZE, 1024);
	set_int(&hw, SNDRV_PCM_HW_PARAM_PERIODS, 4);
	if (ioctl(fd, SNDRV_PCM_IOCTL_HW_PARAMS, &hw)) {
		printf("hw_params %c: %s\n", dir, strerror(errno));
		close(fd);
		return -1;
	}
	memset(&sw, 0, sizeof(sw));
	sw.period_step = 1;
	sw.avail_min = 1;
	sw.start_threshold = 1;
	/* Never stop for lack of data: the hardware moves the audio. */
	sw.stop_threshold = LONG_MAX;
	if (ioctl(fd, SNDRV_PCM_IOCTL_SW_PARAMS, &sw))
		printf("sw_params %c: %s\n", dir, strerror(errno));
	if (ioctl(fd, SNDRV_PCM_IOCTL_PREPARE) || ioctl(fd, SNDRV_PCM_IOCTL_START)) {
		printf("prepare/start %c: %s\n", dir, strerror(errno));
		close(fd);
		return -1;
	}
	printf("%s started\n", dir == 'p' ? "playback (downlink)" : "capture (CONNSYS I2S)");
	return fd;
}

int main(int argc, char **argv)
{
	struct v4l2_frequency freq = { .type = V4L2_TUNER_RADIO };
	struct v4l2_control vol = { .id = V4L2_CID_AUDIO_VOLUME };
	int radio, cap, play, card, dev, seconds, t;
	FILE *priv;

	if (argc < 6) {
		fprintf(stderr, "usage: %s RADIO FREQ_KHZ VOLUME SECONDS PRIVATE_FILE\n", argv[0]);
		return 2;
	}
	freq.frequency = strtoul(argv[2], NULL, 10) * 16;
	vol.value = atoi(argv[3]);
	seconds = atoi(argv[4]);
	priv = fopen(argv[5], "w");
	if (!priv) {
		perror("private file");
		return 1;
	}
	fprintf(priv, "tuning %s kHz\n", argv[2]);
	fclose(priv);

	radio = open(argv[1], O_RDWR);
	if (radio < 0) {
		printf("radio open: %s\n", strerror(errno));
		return 1;
	}
	printf("radio volume %d: %s\n", vol.value,
	       ioctl(radio, VIDIOC_S_CTRL, &vol) ? strerror(errno) : "ok");
	printf("tune: %s\n", ioctl(radio, VIDIOC_S_FREQUENCY, &freq) ? strerror(errno) : "ok");

	if (find_device(&card, &dev)) {
		printf("no Hostless_FM device\n");
		close(radio);
		return 1;
	}
	printf("Hostless_FM is card %d device %d\n", card, dev);
	cap = pcm_open(card, dev, 'c');
	play = cap < 0 ? -1 : pcm_open(card, dev, 'p');

	for (t = 0; play >= 0 && t < seconds; t += 5) {
		struct v4l2_tuner tuner = { 0 };

		sleep(5);
		ioctl(radio, VIDIOC_G_TUNER, &tuner);
		printf("t=%d signal=%u stereo=%u\n", t + 5, tuner.signal,
		       !!(tuner.rxsubchans & V4L2_TUNER_SUB_STEREO));
		fflush(stdout);
	}

	if (play >= 0) {
		ioctl(play, SNDRV_PCM_IOCTL_DROP);
		close(play);
		printf("playback stopped\n");
	}
	if (cap >= 0) {
		ioctl(cap, SNDRV_PCM_IOCTL_DROP);
		close(cap);
		printf("capture stopped\n");
	}
	close(radio);
	printf("radio closed\n");
	return play >= 0 ? 0 : 1;
}
