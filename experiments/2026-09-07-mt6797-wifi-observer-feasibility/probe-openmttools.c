// SPDX-License-Identifier: MIT
/* Host-only counterexamples for pinned openmttools; all ioctls are mocked. */
#include <assert.h>
#include <stdarg.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <errno.h>
int probe_ioctl(int fd, unsigned long request, ...);
#define ioctl probe_ioctl
#define main openmttools_main
#include OPENMTTOOLS_SOURCE
#undef main
#undef ioctl
#undef assert
#define assert(test) do { if (!(test)) { fprintf(stderr, "failed: %s\n", #test); exit(1); } } while (0)
static int set_count, info_count, force_error, power_count, power_values[4];
int probe_ioctl(int fd, unsigned long request, ...) {
    (void)fd;
    va_list ap; va_start(ap, request);
    int result = 0;
    if (request == WMT_IOCTL_GET_CHIP_INFO) {
        int which = va_arg(ap, int);
        result = which == 0 ? 0x6752 : (which == 2 ? 0x0100 : 0);
    } else if (request == WMT_IOCTL_SET_PATCH_NUM) {
        assert(va_arg(ap, unsigned int) == 2); set_count++;
        if (force_error) {errno=EIO; result=-1;}
    } else if (request == WMT_IOCTL_SET_PATCH_INFO) {
        WMT_PATCH_INFO *info=va_arg(ap, WMT_PATCH_INFO *);
        assert(info->downloadSeq == 1); info_count++;
        if (force_error) {errno=EIO; result=-1;}
    } else if (request == WMT_IOCTL_LPBK_POWER_CTRL) {
        assert(power_count<4);power_values[power_count++]=va_arg(ap,int);
    } else {assert(0);}
    va_end(ap);return result;
}
static char directory[]="/tmp/openmttools-probe-XXXXXX";
static char paths[2][128];
static int created;
static void cleanup(void) {
    if (!created) return;
    for (int i=0;i<2;i++) if (paths[i][0]) unlink(paths[i]);
    rmdir(directory);
}
static void interrupted(int sig) { cleanup(); _Exit(128+sig); }
int main(void) {
    unsigned char header[28]={0};
    assert(!atexit(cleanup));
    signal(SIGINT,interrupted); signal(SIGTERM,interrupted);
    assert(mkdtemp(directory)); created=1;
    header[22]=1; header[24]=0x21; /* version 1.0, total 2, sequence 1 */
    for (int i=0;i<2;i++) {
        snprintf(paths[i],sizeof(paths[i]),"%s/ROMv2_lm_patch_%d",directory,i);
        FILE *file=fopen(paths[i],"wb");assert(file);
        assert(fwrite(header,1,sizeof(header),file)==sizeof(header));assert(!fclose(file));
    }
    assert(validateChipID(0x6797)==-1);
    strcpy(firmwareFolder,directory);
    for(force_error=0;force_error<=1;force_error++) {
        set_count=info_count=0;
        assert(search_patch_callback()==0);
        assert(set_count==1 && info_count==2);
    }
    powerOn(NULL);assert(power_count==2 && power_values[0]==0 && power_values[1]==1);
    for(int i=0;i<2;i++) assert(!unlink(paths[i]));
    assert(!rmdir(directory)); created=0;
    puts("probe=pass: unknown-MT6797, duplicate-sequence-accepted, failed-publication-accepted, automatic-off-on");
}
