// SPDX-License-Identifier: GPL-2.0
/*
 * Host fixture for the gemini-wifi-ref-v10 observer core: arm and seal
 * semantics, exact caps under concurrent writers, no record after the seal,
 * the deadline seal, refused repeats, and the sanitising rule that records
 * carry only the fields their call site formats.
 */
#define GWREF10_HOST_CORE
#include "gwref10-host.h"
#include "../lifecycle/gwref10.c"
#include <assert.h>

unsigned long jiffies;
extern const struct kernel_param_ops *gwref10_host_ops;

static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static char **log_lines;
static size_t log_count, log_cap;

void host_printk(const char *fmt, ...)
{
	char line[512];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(line, sizeof(line), fmt, ap);
	va_end(ap);
	pthread_mutex_lock(&log_lock);
	if (log_count == log_cap) {
		log_cap = log_cap ? log_cap * 2 : 256;
		log_lines = realloc(log_lines, log_cap * sizeof(*log_lines));
		assert(log_lines);
	}
	log_lines[log_count++] = strdup(line);
	pthread_mutex_unlock(&log_lock);
}

static void log_reset(void)
{
	size_t i;

	for (i = 0; i < log_count; i++)
		free(log_lines[i]);
	log_count = 0;
}

static size_t count_prefix(const char *prefix)
{
	size_t i, n = 0;

	for (i = 0; i < log_count; i++)
		if (!strncmp(log_lines[i], prefix, strlen(prefix)))
			n++;
	return n;
}

static int set(const char *v) { return gwref10_host_ops->set(v, NULL); }

static void reset_state(void)
{
	memset(&gwref10, 0, sizeof(gwref10));
	pthread_mutex_init(&gwref10.lock, NULL);
	log_reset();
}

struct worker { unsigned int category, count; };

static void *hammer(void *arg)
{
	struct worker *w = arg;
	unsigned int i;

	for (i = 0; i < w->count; i++)
		gwref10_record(w->category, "worker=%u i=%u", w->category, i);
	return NULL;
}

static void *sealer(void *arg)
{
	(void)arg;
	assert(set("2") == 0);
	return NULL;
}

int main(void)
{
	/* 1. Idle: nothing recorded, nothing printed; seal without arm refused. */
	reset_state();
	gwref10_record(GWREF10_CMD, "cid=0x81");
	gwref10_filtered(GWREF10_RXD);
	assert(log_count == 0 && !gwref10_armed());
	assert(set("2") == -EBUSY && set("7") == -EINVAL && set("x") == -EINVAL);
	assert(log_count == 0);

	/* 2. Arm prints the marker with the deadline and caps; a second arm is refused. */
	assert(set("1") == 0 && gwref10_armed());
	assert(log_count == 1 && !strncmp(log_lines[0], "<6>gwref10 arm: deadline_s=240 caps=512/1024/1024/2048/1024/256", 60));
	assert(set("1") == -EBUSY);
	{
		char buf[16];

		gwref10_host_ops->get(buf, NULL);
		assert(!strcmp(buf, "1\n"));
	}

	/* 3. Records are numbered from 1, KERN_DEBUG, and carry only the formatted fields. */
	gwref10_record(GWREF10_CMD, "cid=0x81 seq=%u", 7);
	gwref10_record(GWREF10_EVENT, "eid=0x02 seq=%u len=%u", 7, 20);
	assert(log_count == 3);
	assert(!strcmp(log_lines[1], "<7>gwref10 cmd: n=1 cid=0x81 seq=7\n"));
	assert(!strcmp(log_lines[2], "<7>gwref10 event: n=2 eid=0x02 seq=7 len=20\n"));
	gwref10_filtered(GWREF10_RXD);
	assert(log_count == 3);
	assert(gwref10_record != NULL);

	/* 4. Caps are exact under eight concurrent writers; one cap marker per category. */
	{
		pthread_t t[8];
		struct worker w[8];
		unsigned int i;

		for (i = 0; i < 8; i++) {
			w[i].category = GWREF10_RXD;
			w[i].count = 600;	/* 4800 attempts against a cap of 2048 */
			assert(!pthread_create(&t[i], NULL, hammer, &w[i]));
		}
		for (i = 0; i < 8; i++)
			pthread_join(t[i], NULL);
		assert(gwref10.recorded[GWREF10_RXD] == 2048);
		assert(gwref10.suppressed[GWREF10_RXD] == 4800 - 2048);
		assert(count_prefix("<7>gwref10 rxd: ") == 2048);
		assert(count_prefix("<6>gwref10 cap: rxd ") == 1);
		assert(gwref10.records == 2050);
	}

	/* 5. Record numbers are unique and contiguous across categories. */
	{
		unsigned char *seen = calloc(gwref10.records + 1, 1);
		size_t i;
		unsigned int n, found = 0;

		for (i = 0; i < log_count; i++) {
			const char *p = strstr(log_lines[i], " n=");

			if (!p || log_lines[i][1] != '7')
				continue;
			n = (unsigned int) strtoul(p + 3, NULL, 10);
			assert(n >= 1 && n <= gwref10.records && !seen[n]);
			seen[n] = 1;
			found++;
		}
		assert(found == gwref10.records);
		free(seen);
	}

	/* 6. Seal during concurrent writers: no record line after the seal line and the
	 *    seal counts equal the lines printed before it. */
	{
		pthread_t t[4], s;
		struct worker w[4];
		unsigned int i;
		size_t seal_at = 0, k, after = 0;
		unsigned int recorded_before = 0;

		for (i = 0; i < 4; i++) {
			w[i].category = GWREF10_TXD;
			w[i].count = 5000;
			assert(!pthread_create(&t[i], NULL, hammer, &w[i]));
		}
		assert(!pthread_create(&s, NULL, sealer, NULL));
		pthread_join(s, NULL);
		for (i = 0; i < 4; i++)
			pthread_join(t[i], NULL);
		assert(!gwref10_armed() && gwref10.state == 2);
		for (k = 0; k < log_count; k++)
			if (!strncmp(log_lines[k], "<6>gwref10 seal: reason=explicit", 32))
				seal_at = k + 1;
		assert(seal_at);
		for (k = 0; k < seal_at - 1; k++)
			if (!strncmp(log_lines[k], "<7>gwref10 txd: ", 16))
				recorded_before++;
		for (k = seal_at; k < log_count; k++)
			after++;
		assert(after == 0);
		assert(recorded_before == gwref10.recorded[GWREF10_TXD]);
		{
			unsigned int rec, sup, fil;
			const char *p = strstr(log_lines[seal_at - 1], " txd=");

			assert(p && sscanf(p, " txd=%u/%u/%u", &rec, &sup, &fil) == 3);
			assert(rec == recorded_before && fil == 0 && rec + sup <= 20000);
		}
		/* After the seal nothing is recorded, counted or printed, and arming again is refused. */
		gwref10_record(GWREF10_CMD, "late");
		gwref10_filtered(GWREF10_RXD);
		assert(log_count == seal_at);
		assert(set("1") == -EBUSY && set("2") == -EBUSY);
	}

	/* 7. The deadline seals from a writer's context with reason=deadline. */
	reset_state();
	jiffies = 1000;
	assert(set("1") == 0);
	gwref10_record(GWREF10_STATE, "bssdeact bss=0");
	jiffies = 1000 + 240 * HZ + 1;
	gwref10_record(GWREF10_STATE, "bssdeact bss=0");
	assert(gwref10.state == 2 && gwref10.recorded[GWREF10_STATE] == 1);
	assert(count_prefix("<6>gwref10 seal: reason=deadline records=1 truncated=0 ") == 1);
	assert(log_count == 3);

	/* 8. Filtered counts appear in the seal snapshot and are never records. */
	reset_state();
	jiffies = 0;
	assert(set("1") == 0);
	gwref10_filtered(GWREF10_RXD);
	gwref10_filtered(GWREF10_RXD);
	gwref10_record(GWREF10_RXD, "type=2");
	assert(set("2") == 0);
	assert(count_prefix("<6>gwref10 seal: reason=explicit records=1 truncated=0 ") == 1);
	assert(strstr(log_lines[log_count - 1], " rxd=1/0/2 "));

	/* 9. A record longer than the line bound is marked incomplete and counted. */
	reset_state();
	jiffies = 0;
	assert(set("1") == 0);
	{
		char big[400];

		memset(big, 'x', sizeof(big) - 1);
		big[sizeof(big) - 1] = 0;
		gwref10_record(GWREF10_CMD, "%s", big);
		gwref10_record(GWREF10_CMD, "ok=1");
		assert(gwref10.truncated == 1 && gwref10.records == 2);
		assert(strstr(log_lines[1], " trunc=1\n") && strlen(log_lines[1]) < 300);
		assert(!strcmp(log_lines[2], "<7>gwref10 cmd: n=2 ok=1\n"));
	}
	assert(set("2") == 0);
	assert(count_prefix("<6>gwref10 seal: reason=explicit records=2 truncated=1 ") == 1);

	/* 10. Past the deadline, a filtered call seals too, and an explicit seal is then refused. */
	reset_state();
	jiffies = 0;
	assert(set("1") == 0);
	jiffies = 240 * HZ + 1;
	gwref10_filtered(GWREF10_RXD);
	assert(gwref10.state == 2 && gwref10.filtered[GWREF10_RXD] == 0);
	assert(count_prefix("<6>gwref10 seal: reason=deadline records=0 ") == 1);
	assert(set("2") == -EBUSY);

	puts("gwref10-test: arm/seal, exact caps, seal ordering, deadline, filtered counts, truncation; no device");
	return 0;
}
