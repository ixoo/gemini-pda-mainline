// SPDX-License-Identifier: MIT
/*
 * Battery-temperature charging stop (experiment
 * 2026-10-31-gemini-thermal-protection, step 3), as Gemian does it: charging
 * stops at 50 C and resumes below 47 C. The temperature is the MT6351 BATON
 * channel through IIO, converted as power-status does; an unreadable
 * temperature counts as hot.
 *
 * The one register touched is BQ25896 REG03 (I2C0, 0x6b), after REG14 reads
 * part number 000: stopping clears CHG_CONFIG (bit 4); while stopped, every
 * pass rewrites it with WD_RST (bit 6) so the chip's 40 s I2C watchdog never
 * returns it to its defaults; resuming sets CHG_CONFIG again once and stops
 * the kicks. Whenever charging is allowed and CHG_CONFIG reads clear, it is
 * set, so a new run also restores what an earlier one stopped, and the
 * bootloader's disabled state ends at the first pass rather than at the
 * chip's watchdog. Every other bit of REG03 is written back as read.
 *
 * Charging also stops at a capacity limit, to slow the cell's aging: it stops
 * when the fuel gauge's capacity reaches the limit and resumes 5 points
 * below it. The limit is -l, or the number in /run/station/charge-limit
 * whenever that file exists, read at every pass; 100 turns it off. An
 * unreadable capacity does not stop charging, since only the temperature
 * window is a safety stop.
 *
 * usage: charge-guard [-n] [-q] [-s STOP_DC] [-r RESUME_DC] [-l PERCENT] [-p SECONDS] [-c PASSES]
 *   -n  dry run: decide and log, never write
 *   -q  log only the passes that stop or resume, plus one every 60 passes
 *   -s/-r  stop and resume thresholds in 0.1 C (default 500 and 470)
 *   -l  capacity limit in percent, 50 to 100 (default 80)
 *   -p  seconds between passes (default 10, at most 30)
 *   -c  stop after this many passes (default: run until killed)
 */
#include <fcntl.h>
#include <limits.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define ADDR 0x6b
#define REG03_CHG_CONFIG 0x10
#define REG03_WD_RST 0x40
#define LIMIT_FILE "/run/station/charge-limit"
#define LIMIT_HYSTERESIS 5

static const int ntc_ohms[] = {
	68237, 53650, 42506, 33892, 27219, 22021, 17926, 14674, 12081,
	10000, 8315, 6948, 5834, 4917, 4161, 3535, 3014,
};

/* Battery temperature in 0.1 C from the BATON raw code, or INT_MIN. */
static int batt_decicelsius(int raw)
{
	long mv = raw * 3600L / 4096, ohms;
	unsigned int i;

	if (raw <= 0 || mv >= 2800)
		return INT_MIN;
	ohms = 24000L * mv / (2800 - mv);
	if (ohms >= ntc_ohms[0])
		return -200;
	for (i = 1; i < sizeof(ntc_ohms) / sizeof(ntc_ohms[0]); i++)
		if (ohms >= ntc_ohms[i])
			return -200 + 50 * (int)i - (int)(50 * (ohms - ntc_ohms[i]) /
				(ntc_ohms[i - 1] - ntc_ohms[i]));
	return 600;
}

static int batt_raw(void)
{
	char path[96], name[16] = "";
	int dev, raw = -1;
	FILE *f;

	for (dev = 0; dev < 8 && raw < 0; dev++) {
		snprintf(path, sizeof(path), "/sys/bus/iio/devices/iio:device%d/name", dev);
		f = fopen(path, "r");
		if (!f)
			continue;
		if (!fgets(name, sizeof(name), f))
			name[0] = 0;
		fclose(f);
		if (strncmp(name, "MT6351", 6))
			continue;
		snprintf(path, sizeof(path), "/sys/bus/iio/devices/iio:device%d/in_temp0_raw", dev);
		f = fopen(path, "r");
		if (f) {
			if (fscanf(f, "%d", &raw) != 1)
				raw = -1;
			fclose(f);
		}
	}
	return raw;
}

/* The first integer in a file, or -1. */
static int read_int(const char *path)
{
	FILE *f = fopen(path, "r");
	int value = -1;

	if (f) {
		if (fscanf(f, "%d", &value) != 1)
			value = -1;
		fclose(f);
	}
	return value;
}

static int smbus(int fd, char rw, unsigned char reg, union i2c_smbus_data *data)
{
	struct i2c_smbus_ioctl_data args = {
		.read_write = rw,
		.command = reg,
		.size = I2C_SMBUS_BYTE_DATA,
		.data = data,
	};

	return ioctl(fd, I2C_SMBUS, &args) < 0 ? -1 : 0;
}

static int read_reg(int fd, unsigned char reg)
{
	union i2c_smbus_data data;

	return smbus(fd, I2C_SMBUS_READ, reg, &data) ? -1 : data.byte;
}

static int write_reg(int fd, unsigned char reg, unsigned char value)
{
	union i2c_smbus_data data = { .byte = value };

	return smbus(fd, I2C_SMBUS_WRITE, reg, &data);
}

/* Open the charger and confirm REG14's part number, or -1. */
static int open_charger(void)
{
	int fd = open("/dev/i2c-0", O_RDWR | O_CLOEXEC), id;

	if (fd < 0 || ioctl(fd, I2C_SLAVE, ADDR) < 0) {
		if (fd >= 0)
			close(fd);
		return -1;
	}
	id = read_reg(fd, 0x14);
	if (id < 0 || ((id >> 3) & 7) != 0) {
		close(fd);
		return -1;
	}
	return fd;
}

int main(int argc, char **argv)
{
	int dry = 0, quiet = 0, stop_dc = 500, resume_dc = 470, limit_arg = 80, period = 10;
	int passes = -1, opt, stopped = 0, hot = 0, full = 0;
	unsigned long pass = 0;

	while ((opt = getopt(argc, argv, "nqs:r:l:p:c:")) != -1) {
		switch (opt) {
		case 'n': dry = 1; break;
		case 'q': quiet = 1; break;
		case 's': stop_dc = atoi(optarg); break;
		case 'r': resume_dc = atoi(optarg); break;
		case 'l': limit_arg = atoi(optarg); break;
		case 'p': period = atoi(optarg); break;
		case 'c': passes = atoi(optarg); break;
		default: return 2;
		}
	}
	if (period < 1 || period > 30 || resume_dc >= stop_dc || limit_arg < 50 || limit_arg > 100) {
		fprintf(stderr, "charge-guard: period 1-30 s, resume below stop, limit 50-100\n");
		return 2;
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	printf("charge-guard: stop=%d resume=%d (0.1 C) limit=%d%% period=%ds%s\n",
	       stop_dc, resume_dc, limit_arg, period, dry ? " dry-run" : "");
	while (passes) {
		int raw = batt_raw(), t = raw < 0 ? INT_MIN : batt_decicelsius(raw);
		int fd = open_charger(), reg03 = fd < 0 ? -1 : read_reg(fd, 0x03);
		int limit = read_int(LIMIT_FILE), cap = read_int("/sys/class/power_supply/battery/capacity");
		int want_hot = t == INT_MIN || t >= stop_dc ? 1 : t < resume_dc ? 0 : hot;
		int want_full, want_stop;
		const char *action = "none";
		int value = reg03;

		if (limit < 50 || limit > 100)
			limit = limit_arg;
		want_full = limit == 100 || cap < 0 ? 0 : cap >= limit ? 1 :
			    cap <= limit - LIMIT_HYSTERESIS ? 0 : full;
		want_stop = want_hot || want_full;
		if (fd < 0 || reg03 < 0) {
			action = "no-charger";
		} else if (want_stop) {
			value = (reg03 & ~REG03_CHG_CONFIG) | REG03_WD_RST;
			action = stopped ? "hold" : "stop";
		} else if (!(reg03 & REG03_CHG_CONFIG)) {
			value = reg03 | REG03_CHG_CONFIG;
			action = "resume";
		}
		if (value != reg03 && !dry && fd >= 0 && write_reg(fd, 0x03, value))
			action = "write-failed";
		else if (fd >= 0 && reg03 >= 0) {
			stopped = want_stop;
			hot = want_hot;
			full = want_full;
		}
		if (!quiet || (strcmp(action, "none") && strcmp(action, "hold")) || pass % 60 == 0)
			printf("t=%ld temp=%d raw=%d cap=%d limit=%d reg03=0x%02x action=%s%s%s%s\n",
			       (long)time(NULL), t == INT_MIN ? -9999 : t, raw, cap, limit,
			       reg03 & 0xff, action, want_hot ? " hot" : "", want_full ? " full" : "",
			       dry && value != reg03 ? " (dry)" : "");
		pass++;
		if (fd >= 0)
			close(fd);
		if (passes > 0)
			passes--;
		if (passes)
			sleep(period);
	}
	return 0;
}
