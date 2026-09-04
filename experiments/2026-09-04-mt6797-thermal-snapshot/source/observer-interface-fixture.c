/* SPDX-License-Identifier: MIT */
/* Userspace fixture: actual kernel bodies are inserted at marked locations. */
#include <assert.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include "mt6797_thermal_observer.h"
#define PAGE_SIZE 4096
#define THERMAL_TEMP_INVALID (-274000)
#define MT8173_TEMP_MIN (-20000)
#define MT8173_TEMP_MAX 150000
#define max(a,b) ({ __typeof__(a) va=(a); __typeof__(b) vb=(b); va>vb?va:vb; })
struct mtk_thermal;
struct bank_data { int num_sensors; int sensors[2]; };
struct mtk_thermal_data { int num_banks; struct bank_data bank_data[6]; int msr[2]; };
struct mtk_thermal_bank { struct mtk_thermal *mt; int id; };
struct mtk_thermal {
    const struct mtk_thermal_data *conf;
    void *thermal_base;
    struct mtk_thermal_bank banks[6];
    int (*raw_to_mcelsius)(struct mtk_thermal *, int, int32_t);
    struct mt6797_thermal_observer observer;
};
struct thermal_zone_device { struct mtk_thermal *mt; };
struct device { struct mtk_thermal *mt; };
struct device_attribute { int unused; };
static struct mtk_thermal *thermal_zone_device_priv(struct thermal_zone_device *tz) { return tz->mt; }
static void *dev_get_drvdata(struct device *dev) { return dev->mt; }
static pthread_mutex_t bank_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_barrier_t start_barrier;
static atomic_uint io_count, clock_count;
static _Thread_local int selected, slot, invalid;
static unsigned char registers[8];
static uint32_t readl(void *address) {
    (void)address;
    atomic_fetch_add(&io_count, 1);
    return 0;
}
static int convert(struct mtk_thermal *mt, int sensor, int32_t raw) {
    (void)mt; (void)sensor; (void)raw;
    return invalid ? 150001 : 35000 + selected * 100;
}
static void mtk_thermal_get_bank(struct mtk_thermal_bank *bank) {
    assert(pthread_mutex_lock(&bank_lock) == 0);
    selected = bank->id; slot = 0;
}
static void mtk_thermal_put_bank(struct mtk_thermal_bank *bank) {
    (void)bank;
    assert(pthread_mutex_unlock(&bank_lock) == 0);
}
static u64 ktime_get_ns(void) { return atomic_fetch_add(&clock_count, 1) + 1; }
static int sysfs_emit(char *buf, const char *format, ...) {
    va_list ap; va_start(ap, format);
    int n = vsnprintf(buf, PAGE_SIZE, format, ap);
    va_end(ap); assert(n >= 0 && n < PAGE_SIZE); return n;
}
static int sysfs_emit_at(char *buf, int at, const char *format, ...) {
    assert(at >= 0 && at < PAGE_SIZE);
    va_list ap; va_start(ap, format);
    int n = vsnprintf(buf + at, PAGE_SIZE - at, format, ap);
    va_end(ap); assert(n >= 0 && n < PAGE_SIZE - at); return n;
}
/* ACTUAL_FUNCTIONS */
static void status(struct device *dev, unsigned expected) {
    char buf[PAGE_SIZE], wanted[80];
    snprintf(wanted, sizeof(wanted), "abi=1 attempts=%u limit=3\n", expected);
    assert(mt6797_temperature_snapshot_status_show(dev, NULL, buf) == (ssize_t)strlen(wanted));
    assert(strcmp(buf, wanted) == 0);
}
static unsigned record(struct device *dev, int wanted_error) {
    char buf[PAGE_SIZE];
    unsigned abi, attempt, complete, count, mask, winner;
    int error, maximum;
    unsigned long long start, end;
    ssize_t n = mt6797_temperature_snapshot_show(dev, NULL, buf);
    assert(n > 0 && n < PAGE_SIZE && n == (ssize_t)strlen(buf));
    assert(sscanf(buf, "abi=%u attempt=%u error=%d complete=%u count=%u valid_mask=%u winner=%u maximum=%d start_ns=%llu end_ns=%llu",
                  &abi, &attempt, &error, &complete, &count, &mask, &winner, &maximum, &start, &end) == 10);
    assert(abi == 1 && attempt >= 1 && attempt <= 3);
    if (wanted_error != INT_MAX) assert(error == wanted_error);
    if (!error) {
        assert(complete == 1 && count == 7 && mask == 127 && winner == 6 && maximum == 35500);
        assert(end > start);
        const char *line = strchr(buf, '\n') + 1;
        const unsigned banks[] = {0,1,2,2,3,4,5}, sensors[] = {0,3,1,2,1,1,1};
        for (unsigned i = 0; i < 7; i++) {
            char wanted[96];
            snprintf(wanted, sizeof(wanted), "slot=%u bank=%u sensor=%u temperature=%u valid=1\n", i,banks[i],sensors[i],35000+banks[i]*100);
            assert(strncmp(line, wanted, strlen(wanted)) == 0);
            line += strlen(wanted);
        }
        assert(*line == '\0');
    } else if (error == -ENOSPC) {
        assert(!complete && !count && !mask && !start && !end);
        assert(strstr(buf, "slot=") == NULL);
    } else {
        assert(!complete && count == 7 && !mask && end > start);
    }
    return error == -ENOSPC ? 0 : attempt;
}
struct task { struct device *dev; unsigned attempt; };
static void *capture_thread(void *arg) {
    struct task *t = arg;
    pthread_barrier_wait(&start_barrier);
    t->attempt = record(t->dev, INT_MAX);
    return NULL;
}
static void *poll_thread(void *arg) {
    struct device *dev = arg;
    struct thermal_zone_device tz = {.mt=dev->mt};
    pthread_barrier_wait(&start_barrier);
    for (int i=0; i<100; i++) {
        int value;
        assert(mtk_read_temp(&tz, &value) == 0 && value == 35500);
    }
    return NULL;
}
int main(void) {
    const struct mtk_thermal_data conf = {.num_banks=6,
        .bank_data={{1,{0,0}},{1,{3,0}},{2,{1,2}},{1,{1,0}},{1,{1,0}},{1,{1,0}}}, .msr={0,4}};
    struct mtk_thermal mt = {.conf=&conf,.thermal_base=registers,.raw_to_mcelsius=convert};
    struct device dev = {.mt=&mt};
    struct thermal_zone_device tz = {.mt=&mt};
    for (int i=0;i<6;i++) { mt.banks[i].mt=&mt; mt.banks[i].id=i; }
    mt6797_thermal_observer_init(&mt.observer);
    status(&dev,0); assert(io_count==0 && clock_count==0);
    for (int i=0;i<100;i++) { int v; assert(!mtk_read_temp(&tz,&v)); }
    status(&dev,0); assert(io_count==700 && clock_count==0);
    invalid=1; assert(record(&dev,-EBADMSG)==1); invalid=0;
    assert(record(&dev,0)==2 && record(&dev,0)==3);
    unsigned before=io_count, clocks=clock_count;
    for (int i=0;i<10;i++) { assert(record(&dev,-ENOSPC)==0); status(&dev,3); }
    assert(io_count==before && clock_count==clocks && clocks==6);
    assert(!pthread_mutex_destroy(&mt.observer.lock.native));
    mt6797_thermal_observer_init(&mt.observer);
    atomic_store(&io_count,0); atomic_store(&clock_count,0);
    assert(!pthread_barrier_init(&start_barrier,NULL,9));
    pthread_t threads[9]; struct task tasks[8];
    for (int i=0;i<8;i++) { tasks[i]=(struct task){.dev=&dev}; assert(!pthread_create(&threads[i],NULL,capture_thread,&tasks[i])); }
    assert(!pthread_create(&threads[8],NULL,poll_thread,&dev));
    for (int i=0;i<9;i++) assert(!pthread_join(threads[i],NULL));
    unsigned seen=0;
    for (int i=0;i<8;i++) if (tasks[i].attempt) { assert(!(seen & (1U<<tasks[i].attempt))); seen |= 1U<<tasks[i].attempt; }
    assert(seen==14 && io_count==721 && clock_count==6); status(&dev,3);
    pthread_barrier_destroy(&start_barrier); pthread_mutex_destroy(&mt.observer.lock.native);
    puts("actual_show_status=pass failure_text=pass exhausted_IO=0 concurrent_admitted=3 concurrent_refused=5 concurrent_normal_polls=100");
    return 0;
}
