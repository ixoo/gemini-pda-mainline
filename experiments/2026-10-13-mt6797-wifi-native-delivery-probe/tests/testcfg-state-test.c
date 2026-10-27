/* SPDX-License-Identifier: GPL-2.0-only */
/* The per-join test surface (CONFIG_MT6797_WIFI_TESTCONFIG): the actual
 * testcfg.c behind its debugfs file operations, with the kernel calls it
 * makes stubbed here. Each lifetime takes the next entry; a refused entry
 * keeps the previous configuration; a lifetime that ended badly, or was
 * never measured, is followed by one at the build's configuration without
 * consuming an entry; reset starts the schedule again. Built by
 * run-testcfg-test.py.
 */
#include <assert.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

typedef unsigned char u8;
/* glibc has loff_t and macOS does not */
#define loff_t mt6797_test_loff_t
typedef long long mt6797_test_loff_t;
#define __user
#define GFP_KERNEL 0
#define THIS_MODULE NULL
#define EINVAL 22
#define ENOMEM 12
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((long)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define kzalloc_obj(o, f) calloc(1, sizeof(o))
#define kmalloc(n, f) malloc(n)
#define kcalloc(n, s, f) calloc(n, s)
#define kfree free

struct mutex { bool held; };
static void mutex_init(struct mutex *m) { m->held = false; }
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held = true; }
static void mutex_unlock(struct mutex *m) { assert(m->held); m->held = false; }

static int scnprintf(char *b, size_t n, const char *f, ...)
{
	va_list a;
	int r;

	if (!n)
		return 0;
	va_start(a, f);
	r = vsnprintf(b, n, f, a);
	va_end(a);
	return r < 0 ? 0 : (size_t)r >= n ? (int)n - 1 : r;
}

static void strscpy(char *d, const char *s, size_t n)
{
	snprintf(d, n, "%s", s);
}

static char *strim(char *s)
{
	size_t n = strlen(s);

	while (n && strchr(" \t\n", s[n - 1]))
		s[--n] = 0;
	while (*s && strchr(" \t\n", *s))
		s++;
	return s;
}

static char *memdup_user_nul(const char *b, size_t n)
{
	char *t = malloc(n + 1);

	memcpy(t, b, n);
	t[n] = 0;
	return t;
}

struct dentry { struct { const char *name; } d_name; };
struct file { void *private_data; struct { struct dentry *dentry; } f_path; };
struct file_operations {
	void *owner;
	int (*open)(void *, struct file *);
	ssize_t (*read)(struct file *, char *, size_t, loff_t *);
	ssize_t (*write)(struct file *, const char *, size_t, loff_t *);
	loff_t (*llseek)(struct file *, loff_t, int);
};
static int simple_open(void *inode, struct file *f) { (void)inode; (void)f; return 0; }
static loff_t default_llseek(struct file *f, loff_t o, int w) { (void)f; (void)w; return o; }

static ssize_t simple_read_from_buffer(char *to, size_t count, loff_t *pos,
				       const char *from, size_t available)
{
	size_t n;

	if (*pos >= (loff_t)available)
		return 0;
	n = available - *pos < count ? available - *pos : count;
	memcpy(to, from + *pos, n);
	*pos += n;
	return n;
}

static struct dentry files[4], root;
static void *file_data;
static const struct file_operations *file_ops;
static unsigned int file_count;
static struct dentry *debugfs_create_dir(const char *name, struct dentry *parent)
{
	assert(!strcmp(name, "mt6797_wifi") && !parent);
	return &root;
}
static void debugfs_create_file(const char *name, int mode, struct dentry *parent,
				void *data, const struct file_operations *ops)
{
	(void)mode;
	assert(parent == &root && file_count < 4);
	files[file_count++].d_name.name = name;
	file_data = data;
	file_ops = ops;
}
static void debugfs_remove_recursive(struct dentry *d) { assert(d == &root); }

#include "testcfg.c"

static struct dentry *named(const char *name)
{
	for (unsigned int i = 0; i < file_count; i++)
		if (!strcmp(files[i].d_name.name, name))
			return &files[i];
	assert(false);
	return NULL;
}

static ssize_t put(const char *name, const char *text)
{
	struct file f = { .private_data = file_data, .f_path.dentry = named(name) };
	loff_t pos = 0;

	return file_ops->write(&f, text, strlen(text), &pos);
}

static const char *get(const char *name)
{
	static char text[16384];
	struct file f = { .private_data = file_data, .f_path.dentry = named(name) };
	loff_t pos = 0;
	ssize_t n, total = 0;

	/* in small pieces, as a reader may */
	while ((n = file_ops->read(&f, text + total, 7, &pos)) > 0)
		total += n;
	text[total] = 0;
	return text;
}

static const struct mt6797_testcfg build = {
	.rate = 0x85, .bw40 = true, .sgi = false, .agg = true, .peek = true,
};

static char line[160];

static struct mt6797_testcfg next(struct mt6797_testcfg_state *t, unsigned int lifetime)
{
	struct mt6797_testcfg c;

	mt6797_testcfg_next(t, lifetime, &c, line, sizeof(line));
	return c;
}

int main(void)
{
	struct mt6797_testcfg_state *t = mt6797_testcfg_register(&build);
	struct mt6797_testcfg c;
	const char *s;

	assert(!IS_ERR(t) && file_count == 4);
	/* No schedule: the build, every lifetime. */
	c = next(t, 1);
	assert(!memcmp(&c, &build, sizeof(c)));
	assert(!strcmp(line, "lifetime=1 entry=0 config=- rate=0x85 bw=40 sgi=0 agg=1 peek=1 source=build"));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	/* A second stats line for the same lifetime is not recorded. */
	assert(!mt6797_testcfg_stats(t, "reason=again", true));
	/* A schedule that does not fit is refused whole. */
	assert(put("testcfg", "40M5,40M5,40M5,40M5,40M5,40M5,40M5,40M5,40M5,40M5,"
		   "40M5,40M5,40M5,40M5,40M5,40M5,40M5") == -EINVAL);
	assert(put("testcfg", "20M7,bogus,40M5,40M6+sgi\n") > 0);
	s = get("testcfg");
	assert(strstr(s, "20M7,bogus,40M5,40M6+sgi\nentries=4 next=0\n"));
	assert(strstr(s, "entry=2 config=bogus refused=unknown item\n"));
	/* lifetime 2: entry 1, which then fails */
	c = next(t, 2);
	assert(c.rate == 0x87 && !c.bw40);
	assert(!strcmp(line, "lifetime=2 entry=1 config=20M7 rate=0x87 bw=20 sgi=0 agg=1 peek=1 source=schedule"));
	s = mt6797_testcfg_stats(t, "reason=txfail", false);
	assert(s && !strcmp(s, "lifetime=2 config=20M7 ok=0 reason=txfail"));
	/* lifetime 3: the build, and entry 2 still waits */
	c = next(t, 3);
	assert(!memcmp(&c, &build, sizeof(c)) && strstr(line, "entry=0 config=- ") &&
	       strstr(line, "source=recovery"));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	/* lifetime 4: entry 2 is refused and keeps the previous (the build) */
	c = next(t, 4);
	assert(!memcmp(&c, &build, sizeof(c)));
	assert(strstr(line, "entry=2 config=bogus ") &&
	       strstr(line, "source=refused:unknown item"));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	/* lifetime 5: entry 3; then lifetime 6 begins with 5 never measured */
	c = next(t, 5);
	assert(c.rate == 0x85 && c.bw40 && !c.sgi);
	c = next(t, 6);
	assert(!memcmp(&c, &build, sizeof(c)) && strstr(line, "source=recovery"));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	/* lifetime 7: entry 4; lifetime 8: after the schedule */
	c = next(t, 7);
	assert(c.rate == 0x86 && c.bw40 && c.sgi && strstr(line, "entry=4 config=40M6+sgi"));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	c = next(t, 8);
	assert(!memcmp(&c, &build, sizeof(c)) && strstr(line, "source=after-schedule"));
	s = get("applied");
	assert(strstr(s, "lifetime=1 entry=0 config=- ") && strstr(s, "lifetime=8 entry=0 "));
	s = get("stats");
	assert(strstr(s, "lifetime=2 config=20M7 ok=0 reason=txfail\n") &&
	       strstr(s, "lifetime=7 config=40M6+sgi ok=1 reason=disconnect\n"));
	assert(!strstr(s, "reason=again"));
	/* reset: applied and stats empty, the schedule from its first entry */
	assert(put("reset", "1\n") > 0);
	assert(!get("applied")[0] && !get("stats")[0]);
	assert(strstr(get("testcfg"), "entries=4 next=0\n"));
	c = next(t, 9);
	assert(c.rate == 0x87 && strstr(line, "entry=1 "));
	assert(mt6797_testcfg_stats(t, "reason=disconnect", true));
	/* a refused entry after a scheduled one keeps that one's configuration */
	c = next(t, 10);
	assert(c.rate == 0x87 && !c.bw40 && strstr(line, "source=refused:unknown item"));
	/* an empty schedule is the build again */
	assert(put("testcfg", "\n") > 0);
	assert(strstr(get("testcfg"), "\nentries=0 next=0\n"));
	/* the build-time seed takes the same path as a write */
	{
		char seed[] = "40M6,agg=0\n", wide[600];

		assert(mt6797_testcfg_set(t, seed) == 2);
		assert(strstr(get("testcfg"), "40M6,agg=0\nentries=2 next=0\n"));
		memset(wide, 'x', sizeof(wide) - 1);
		wide[sizeof(wide) - 1] = 0;
		assert(mt6797_testcfg_set(t, wide) == -EINVAL);
		assert(strstr(get("testcfg"), "entries=2 next=0\n"));
	}
	mt6797_testcfg_unregister(t);
	printf("testcfg-state-test: PASS\n");
	return 0;
}
