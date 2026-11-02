// SPDX-License-Identifier: GPL-2.0-only
/*
 * A bounded job for the first Panfrost run on the Gemini's Mali-T880.
 *
 * Prints the GPU identity, then submits at most --jobs Write Value jobs of type
 * Zero, the same job Mesa uses on Midgard to clear a tiler heap. Each must zero a
 * seeded word in a GPU-mapped buffer. This exercises the job manager, the GPU MMU
 * and the job interrupt. It runs no shader.
 *
 * It stops at the first failure and before any job if the SoC zone is at or above
 * --max-mc. Exit: 0 all jobs passed, 1 a job failed, 2 a thermal stop, 3 setup.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

/* From include/uapi/drm/panfrost_drm.h, so this builds without kernel headers. */
#define DRM_CMD_BASE		0x40
struct panfrost_submit {
	uint64_t jc;
	uint64_t in_syncs;
	uint32_t in_sync_count;
	uint32_t out_sync;
	uint64_t bo_handles;
	uint32_t bo_handle_count;
	uint32_t requirements;
	uint32_t jm_ctx_handle;
	uint32_t pad;
};
struct panfrost_wait_bo {
	uint32_t handle;
	uint32_t pad;
	int64_t timeout_ns;
};
struct panfrost_create_bo {
	uint32_t size;
	uint32_t flags;
	uint32_t handle;
	uint32_t pad;
	uint64_t offset;
};
struct panfrost_mmap_bo {
	uint32_t handle;
	uint32_t flags;
	uint64_t offset;
};
struct panfrost_get_param {
	uint32_t param;
	uint32_t pad;
	uint64_t value;
};
#define IOC_RW(nr, type) _IOWR('d', DRM_CMD_BASE + (nr), type)
#define IOC_W(nr, type) _IOW('d', DRM_CMD_BASE + (nr), type)
#define IOCTL_SUBMIT		IOC_W(0x00, struct panfrost_submit)
#define IOCTL_WAIT_BO		IOC_W(0x01, struct panfrost_wait_bo)
#define IOCTL_CREATE_BO		IOC_RW(0x02, struct panfrost_create_bo)
#define IOCTL_MMAP_BO		IOC_RW(0x03, struct panfrost_mmap_bo)
#define IOCTL_GET_PARAM		IOC_RW(0x04, struct panfrost_get_param)
#define BO_NOEXEC		1

/* Mesa src/panfrost/genxml/v4.xml: Job Header and Write Value Job Payload. */
#define JOB_IS_64B		(1u << 0)
#define JOB_TYPE_WRITE_VALUE	(2u << 1)
#define JOB_INDEX_1		(1u << 16)
#define WRITE_VALUE_ZERO	3u

#define WORD_OFFSET		256
#define SEED			0x5a5a5a5a5a5a5a5aull
#define JOB_TIMEOUT_NS		1000000000ll
#define MAX_JOBS		1000

static const char *zone;

static int read_temp(void)
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

static uint64_t param(int fd, uint32_t p)
{
	struct panfrost_get_param g = { .param = p };

	if (ioctl(fd, IOCTL_GET_PARAM, &g))
		return ~0ull;
	return g.value;
}

int main(int argc, char **argv)
{
	struct panfrost_create_bo bo = { .size = 4096, .flags = BO_NOEXEC };
	struct panfrost_mmap_bo mm = { 0 };
	int jobs = 100, max_mc = 65000, i, fd;
	uint32_t *desc;
	uint8_t *map;

	for (i = 1; i + 1 < argc; i += 2) {
		if (!strcmp(argv[i], "--jobs"))
			jobs = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--max-mc"))
			max_mc = atoi(argv[i + 1]);
		else if (!strcmp(argv[i], "--zone"))
			zone = argv[i + 1];
	}
	if (!zone) {
		fprintf(stderr, "--zone is required\n");
		return 3;
	}
	if (jobs < 0 || jobs > MAX_JOBS) {
		fprintf(stderr, "jobs must be 0 to %d\n", MAX_JOBS);
		return 3;
	}

	fd = open("/dev/dri/renderD128", O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		perror("renderD128");
		return 3;
	}

	printf("prod_id=%#llx revision=%#llx shader_present=%#llx tiler_present=%#llx "
	       "l2_present=%#llx as_present=%#llx js_present=%#llx\n",
	       (unsigned long long)param(fd, 0), (unsigned long long)param(fd, 1),
	       (unsigned long long)param(fd, 2), (unsigned long long)param(fd, 3),
	       (unsigned long long)param(fd, 4), (unsigned long long)param(fd, 6),
	       (unsigned long long)param(fd, 7));

	if (ioctl(fd, IOCTL_CREATE_BO, &bo)) {
		perror("create_bo");
		return 3;
	}
	mm.handle = bo.handle;
	if (ioctl(fd, IOCTL_MMAP_BO, &mm)) {
		perror("mmap_bo");
		return 3;
	}
	map = mmap(NULL, bo.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, mm.offset);
	if (map == MAP_FAILED) {
		perror("mmap");
		return 3;
	}
	desc = (uint32_t *)map;
	printf("bo gpu_va=%#llx\n", (unsigned long long)bo.offset);

	for (i = 0; i < jobs; i++) {
		struct panfrost_submit sub = { 0 };
		struct panfrost_wait_bo wait = { 0 };
		volatile uint64_t *word = (volatile uint64_t *)(map + WORD_OFFSET);
		uint64_t target = bo.offset + WORD_OFFSET;
		uint32_t handle = bo.handle;
		struct timespec a, b;
		int t = read_temp();

		if (t < 0 || t >= max_mc) {
			printf("thermal stop before job %d: %d mC\n", i, t);
			return 2;
		}

		memset(map, 0, WORD_OFFSET);
		*word = SEED;
		desc[4] = JOB_IS_64B | JOB_TYPE_WRITE_VALUE | JOB_INDEX_1;
		desc[8] = (uint32_t)target;
		desc[9] = (uint32_t)(target >> 32);
		desc[10] = WRITE_VALUE_ZERO;
		__sync_synchronize();

		sub.jc = bo.offset;
		sub.bo_handles = (uintptr_t)&handle;
		sub.bo_handle_count = 1;
		clock_gettime(CLOCK_MONOTONIC, &a);
		if (ioctl(fd, IOCTL_SUBMIT, &sub)) {
			printf("job %d: submit failed: %s\n", i, strerror(errno));
			return 1;
		}
		wait.handle = bo.handle;
		wait.timeout_ns = (int64_t)a.tv_sec * 1000000000ll + a.tv_nsec + JOB_TIMEOUT_NS;
		if (ioctl(fd, IOCTL_WAIT_BO, &wait)) {
			printf("job %d: wait failed: %s\n", i, strerror(errno));
			return 1;
		}
		clock_gettime(CLOCK_MONOTONIC, &b);
		if (*word != 0) {
			printf("job %d: word still %#llx, exception status %#x\n", i,
			       (unsigned long long)*word, desc[0]);
			return 1;
		}
		if (i == 0 || i == jobs - 1)
			printf("job %d: ok in %ld us, exception status %#x, %d mC\n", i,
			       (long)((b.tv_sec - a.tv_sec) * 1000000 +
				      (b.tv_nsec - a.tv_nsec) / 1000), desc[0], t);
	}

	printf("passed %d of %d jobs, %d mC\n", i, jobs, read_temp());
	return 0;
}
