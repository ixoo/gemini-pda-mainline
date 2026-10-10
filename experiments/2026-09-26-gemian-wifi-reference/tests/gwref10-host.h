/* SPDX-License-Identifier: GPL-2.0 */
/* Host stand-ins for the kernel interfaces gwref10.c uses; the fixture captures printk. */
#ifndef GWREF10_HOST_H
#define GWREF10_HOST_H
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define KERN_INFO "<6>"
#define KERN_DEBUG "<7>"
#define HZ 100
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define WRITE_ONCE(x, v) (*(volatile __typeof__(x) *)&(x) = (v))
#define time_after(a, b) ((long)((b) - (a)) < 0)
#define MODULE_PARM_DESC(name, desc)
#define __SPIN_LOCK_UNLOCKED(name) PTHREAD_MUTEX_INITIALIZER

typedef pthread_mutex_t spinlock_t;
struct kernel_param;
struct kernel_param_ops {
	int (*set)(const char *val, const struct kernel_param *kp);
	int (*get)(char *buffer, const struct kernel_param *kp);
};
#define module_param_cb(name, ops, arg, perm) const struct kernel_param_ops *gwref10_host_ops = (ops)

extern unsigned long jiffies;
void host_printk(const char *fmt, ...);
#define printk host_printk
#define spin_lock_irqsave(l, f) do { (void)(f); pthread_mutex_lock(l); } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(f); pthread_mutex_unlock(l); } while (0)
#define scnprintf snprintf
static inline int kstrtouint(const char *s, unsigned int base, unsigned int *out)
{
	char *end;
	unsigned long v = strtoul(s, &end, base);

	if (end == s || (*end && *end != '\n'))
		return -EINVAL;
	*out = (unsigned int)v;
	return 0;
}
#include "../lifecycle/gwref10.h"
#endif
