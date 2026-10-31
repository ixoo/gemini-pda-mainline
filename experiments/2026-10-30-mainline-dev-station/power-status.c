// SPDX-License-Identifier: MIT
/*
 * Power status from the BQ25896 charger at 0x6b on I2C0 (experiment
 * 2026-10-31-gemini-power-status). Reads REG14 first and stops unless the
 * part number is BQ25896's. Unless the ADC already converts continuously, it
 * then starts one conversion: REG02 written back with only CONV_START (bit 7)
 * added, the one register write, and REG02 polled for at most 2 s until the
 * bit clears. Then REG02, REG0B and REG0E to REG12 are read, one SMBus byte
 * each. REG0C, whose fault bits clear on read, is never read. Battery
 * percentage is a coarse estimate from voltage alone. ADC fields are marked
 * stale if no conversion completed.
 * usage: power-status [-r] [BUS]   (-r adds the raw registers; BUS defaults
 * to the adapter under the 11007000.i2c platform device)
 */
#include <dirent.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define ADDR 0x6b
#define I2C0 "/sys/bus/platform/devices/11007000.i2c"

static int read_reg(int fd, unsigned char reg)
{
	union i2c_smbus_data data;
	struct i2c_smbus_ioctl_data args = {
		.read_write = I2C_SMBUS_READ,
		.command = reg,
		.size = I2C_SMBUS_BYTE_DATA,
		.data = &data,
	};

	if (ioctl(fd, I2C_SMBUS, &args) < 0)
		return -1;
	return data.byte;
}

static int write_reg(int fd, unsigned char reg, unsigned char value)
{
	union i2c_smbus_data data = { .byte = value };
	struct i2c_smbus_ioctl_data args = {
		.read_write = I2C_SMBUS_WRITE,
		.command = reg,
		.size = I2C_SMBUS_BYTE_DATA,
		.data = &data,
	};

	return ioctl(fd, I2C_SMBUS, &args) < 0 ? -1 : 0;
}

/* One conversion: 1 if it completed, 0 if not. Only CONV_START is added. */
static int convert(int fd)
{
	int reg02 = read_reg(fd, 0x02), i;

	if (reg02 < 0)
		return 0;
	if (reg02 & 0x40)
		return 1;
	if (write_reg(fd, 0x02, reg02 | 0x80))
		return 0;
	for (i = 0; i < 20; i++) {
		usleep(100000);
		reg02 = read_reg(fd, 0x02);
		if (reg02 >= 0 && !(reg02 & 0x80))
			return 1;
	}
	return 0;
}

static int find_bus(void)
{
	struct dirent *e;
	DIR *d = opendir(I2C0);
	int bus = -1;

	if (!d)
		return -1;
	while ((e = readdir(d)))
		if (!strncmp(e->d_name, "i2c-", 4))
			bus = atoi(e->d_name + 4);
	closedir(d);
	return bus;
}

/* Rough resting Li-ion curve; not the vendor profile. */
static int estimate(int mv)
{
	static const int curve[][2] = {
		{ 3300, 0 }, { 3600, 10 }, { 3700, 30 }, { 3750, 45 }, { 3800, 55 },
		{ 3900, 70 }, { 4000, 80 }, { 4100, 90 }, { 4200, 100 },
	};
	unsigned int i;

	if (mv <= curve[0][0])
		return 0;
	for (i = 1; i < sizeof(curve) / sizeof(curve[0]); i++)
		if (mv <= curve[i][0])
			return curve[i - 1][1] + (mv - curve[i - 1][0]) *
			       (curve[i][1] - curve[i - 1][1]) / (curve[i][0] - curve[i - 1][0]);
	return 100;
}

int main(int argc, char **argv)
{
	static const char *const vbus[] = { "none", "usb-sdp", "usb-cdp", "usb-dcp",
					    "hvdcp", "unknown", "non-standard", "otg" };
	static const char *const chrg[] = { "no", "pre", "fast", "done" };
	static const unsigned char regs[] = { 0x02, 0x0b, 0x0e, 0x0f, 0x10, 0x11, 0x12 };
	int raw = 0, bus = -1, fd, id, live, v[sizeof(regs)];
	unsigned int i;
	char path[32];
	const char *adc;

	for (i = 1; i < (unsigned int)argc; i++) {
		if (!strcmp(argv[i], "-r"))
			raw = 1;
		else
			bus = atoi(argv[i]);
	}
	if (bus < 0)
		bus = find_bus();
	if (bus < 0) {
		fprintf(stderr, "power-status: no I2C0 adapter\n");
		return 1;
	}
	snprintf(path, sizeof(path), "/dev/i2c-%d", bus);
	fd = open(path, O_RDWR | O_CLOEXEC);
	if (fd < 0 || ioctl(fd, I2C_SLAVE, ADDR) < 0) {
		perror(path);
		return 1;
	}
	id = read_reg(fd, 0x14);
	if (id < 0 || ((id >> 3) & 7) != 0) {
		fprintf(stderr, "power-status: REG14=%d is not a BQ25896; stopped\n", id);
		return 1;
	}
	live = convert(fd);
	for (i = 0; i < sizeof(regs); i++) {
		v[i] = read_reg(fd, regs[i]);
		if (v[i] < 0) {
			fprintf(stderr, "power-status: REG%02X read failed; stopped\n", regs[i]);
			return 1;
		}
	}
	close(fd);
	adc = live ? "live" : "stale";
	printf("power=%s good=%d charging=%s battery=%.2fV (estimate %d%%) sys=%.2fV vbus=%.1fV ichg=%.2fA ts=%.1f%% therm=%d adc=%s\n",
	       vbus[(v[1] >> 5) & 7], !!(v[1] & 0x04), chrg[(v[1] >> 3) & 3],
	       (2304 + 20 * (v[2] & 0x7f)) / 1000.0, estimate(2304 + 20 * (v[2] & 0x7f)),
	       (2304 + 20 * (v[3] & 0x7f)) / 1000.0, (2600 + 100 * (v[5] & 0x7f)) / 1000.0,
	       50 * (v[6] & 0x7f) / 1000.0, 21 + 0.465 * (v[4] & 0x7f), !!(v[2] & 0x80), adc);
	if (raw) {
		printf("raw 14=%02x", id);
		for (i = 0; i < sizeof(regs); i++)
			printf(" %02x=%02x", regs[i], v[i]);
		printf("\n");
	}
	return 0;
}
