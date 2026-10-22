/* SPDX-License-Identifier: MIT */
/* Userspace kernel-service shims; exercises actual snapshot.c, not real VFS. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef uint32_t u32;
typedef uint64_t u64;
typedef uint32_t __le32;
#define __user
#define GFP_KERNEL 0
#define GFP_KERNEL_ACCOUNT 0
#define CAP_SYS_RAWIO 0
#define THIS_MODULE NULL
#define ERESTARTSYS 512
#define NSEC_PER_MSEC 1000000ULL
#define U64_MAX UINT64_MAX
#define cpu_to_le32(x) (x)
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define IS_ERR_OR_NULL(p) (!(p) || (intptr_t)(p)<0)
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define scnprintf snprintf
static unsigned int refusal_logs;
#define pr_info(...) (refusal_logs++, fprintf(stderr, __VA_ARGS__))
static int capable(int cap) { return 1; }
static atomic_int allocations;
static void *kzalloc(size_t n,int flags) { void *p=calloc(1,n); if(p) atomic_fetch_add(&allocations,1); return p; }
static void kfree(void *p) { if(p){atomic_fetch_sub(&allocations,1); free(p);} }
#define kfree_sensitive kfree
struct mutex { pthread_mutex_t m; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->m,NULL)); }
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->m)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->m)); }
static int mutex_lock_interruptible(struct mutex *m) { mutex_lock(m); return 0; }
struct kref { atomic_int n; };
static void kref_init(struct kref *r) { atomic_init(&r->n,1); }
static void kref_get(struct kref *r) { assert(atomic_fetch_add(&r->n,1)>0); }
static void kref_put(struct kref *r,void (*f)(struct kref *)) { if(atomic_fetch_sub(&r->n,1)==1)f(r); }
struct completion { sem_t sem; atomic_bool done; };
static void init_completion(struct completion *c) { assert(!sem_init(&c->sem,0,0)); atomic_init(&c->done,false); }
static void complete_all(struct completion *c) { atomic_store(&c->done,true); assert(!sem_post(&c->sem)); }
static atomic_bool waiting;
static long wait_for_completion_interruptible_timeout(struct completion *c,unsigned long timeout) {
 if(atomic_load(&c->done))return 1;
 struct timespec end; clock_gettime(CLOCK_REALTIME,&end); end.tv_sec+=timeout/1000;
 end.tv_nsec+=(timeout%1000)*1000000L; if(end.tv_nsec>=1000000000L){end.tv_sec++;end.tv_nsec-=1000000000L;}
 atomic_store(&waiting,true);
 int ret=sem_timedwait(&c->sem,&end); atomic_store(&waiting,false);
 if(!ret)return 1;
 return errno==EINTR?-ERESTARTSYS:0;
}
static u64 ktime_get_ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (u64)t.tv_sec*1000000000+t.tv_nsec; }
#define msecs_to_jiffies(x) (x)
#define nsecs_to_jiffies(x) ((x)/1000000)
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; void (*fn)(struct work_struct *); };
#define to_delayed_work(w) container_of(w,struct delayed_work,work)
#define INIT_DELAYED_WORK(w,f) ((w)->fn=(f))
#define system_unbound_wq NULL
static void mod_delayed_work(void *q,struct delayed_work *w,unsigned long t) { }
static void cancel_delayed_work_sync(struct delayed_work *w) { }
struct device { int unused; };
struct dentry { struct { const char *name; } d_name; };
struct inode { void *i_private; };
struct file { void *private_data; struct { struct dentry *dentry; } f_path; };
struct file_operations {
 void *owner;
 int (*open)(struct inode *,struct file *);
 int (*release)(struct inode *,struct file *);
 ssize_t (*read)(struct file *,char *,size_t,loff_t *);
 ssize_t (*write)(struct file *,const char *,size_t,loff_t *);
 void *llseek;
};
static int nonseekable_open(struct inode *i,struct file *f){return 0;}
static ssize_t simple_read_from_buffer(char *to,size_t n,loff_t *pos,const void *from,size_t len){
 if(*pos<0)return -EINVAL;
 if((size_t)*pos>=len)return 0;
 if(n>len-*pos)n=len-*pos;
 memcpy(to,(const char *)from+*pos,n); *pos+=n; return n;
}
static int copy_from_user(char *to,const char *from,size_t n){memcpy(to,from,n);return 0;}
static char *strim(char *s){while(*s==' '||*s=='\n')s++;size_t n=strlen(s);while(n&&(s[n-1]=='\n'||s[n-1]==' '))s[--n]=0;return s;}
static int kstrtobool(const char *s,bool *b){if(!strcmp(s,"1")){*b=true;return 0;}if(!strcmp(s,"0")){*b=false;return 0;}return -EINVAL;}
static struct dentry fake_entry;
static struct dentry *debugfs_create_dir(const char *n,struct dentry *p){return &fake_entry;}
static struct dentry *debugfs_create_file(const char *n,int m,struct dentry *p,void *s,const struct file_operations *f){return &fake_entry;}
static void debugfs_remove_recursive(struct dentry *d){}
#define _LINUX_TYPES_H
#include "snapshot.h"
/* ACTUAL_SNAPSHOT_SOURCE */
static bool probe_ok=true, owner_alive=true;
static unsigned int inspections;
static bool ready(void *owner){return probe_ok;}
static void inspect(void *owner,struct mt6797_snapshot_readiness *r){
 assert(owner_alive);inspections++;
 *r=(struct mt6797_snapshot_readiness){.ready=probe_ok,.epoch_enabled=true,
 .configured=probe_ok,.running=true,.data_active=true,.associated=true,
 .ptk_present=true,.gtk_present=true,.window_open=true,.mac_state=2};
}
static int step(void *o,u32 a,unsigned int ordinal,u64 deadline,struct mt6797_snapshot_word *w){w->value=ordinal+0x100;w->valid=true;return 0;}
static const struct mt6797_snapshot_range ranges[]={{0x1000,4}};
static const struct mt6797_snapshot_set sets[]={{"test",ranges,1}};
static const struct mt6797_snapshot_ops ops={.sets=sets,.nsets=1,.ready=ready,.readiness=inspect,.step=step};
static void open_file(struct mt6797_snapshot *s,struct file *f){struct inode i={.i_private=s};assert(!mt6797_snapshot_data_ops.open(&i,f));}
static void close_file(struct file *f){assert(!mt6797_snapshot_data_ops.release(NULL,f));}
struct reader {struct file file;ssize_t result;u32 data[4];};
static void *read_thread(void *arg){struct reader *r=arg;loff_t p=0;r->result=mt6797_snapshot_data_ops.read(&r->file,(char *)r->data,sizeof(r->data),&p);return NULL;}
static void caught(int sig){}
int main(void){
 struct sigaction sa={.sa_handler=caught};sigemptyset(&sa.sa_mask);assert(!sigaction(SIGUSR1,&sa,NULL));
 for(unsigned int round=0;round<100;round++){
  owner_alive=true;probe_ok=true;
  struct mt6797_snapshot *s=mt6797_snapshot_register(NULL,&fake_entry,&ops,NULL,true);assert(s);
  struct file gate={0},select={0};open_file(s,&gate);open_file(s,&select);
  struct dentry gd={.d_name={"gate"}},sd={.d_name={"set"}};gate.f_path.dentry=&gd;select.f_path.dentry=&sd;
  loff_t pos=0;assert(mt6797_snapshot_control_ops.write(&gate,"1",1,&pos)==1);
  assert(mt6797_snapshot_control_ops.write(&select,"test",4,&pos)==4);
  struct dentry status_name={.d_name={"status"}};
  struct file status={0};open_file(s,&status);status.f_path.dentry=&status_name;
  char text[1024]={0};loff_t status_pos=0;
  assert(mt6797_snapshot_control_read(&status,text,sizeof(text)-1,&status_pos)>0);
  assert(strstr(text,"readiness_valid=1 ready=1")&&strstr(text,"mac_state=0x00000002"));
  assert(!s->last&&s->generation==0);close_file(&status);
  probe_ok=false;struct reader denied={0};open_file(s,&denied.file);
  unsigned int logs=refusal_logs;read_thread(&denied);
  assert(denied.result==-ENODEV&&refusal_logs==logs+1&&!s->last&&s->generation==0);
  close_file(&denied.file);probe_ok=true;
  struct reader a={0},b={0};open_file(s,&a.file);open_file(s,&b.file);
  pthread_t task;atomic_store(&waiting,false);assert(!pthread_create(&task,NULL,read_thread,&a));
  while(!atomic_load(&waiting))usleep(100);
  assert(mt6797_snapshot_active(s));assert(s->generation==1);
  read_thread(&b);assert(b.result==-EBUSY);close_file(&b.file);
  struct file ephemeral={0};open_file(s,&ephemeral);close_file(&ephemeral);
  assert(s->generation==1&&s->last->words==0);
  assert(mt6797_snapshot_control_ops.write(&select,"test",4,&pos)==-EBUSY);
  assert(!pthread_kill(task,SIGUSR1));assert(!pthread_join(task,NULL));assert(a.result==-ERESTARTSYS);
  close_file(&a.file);assert(mt6797_snapshot_active(s));
  for(int j=0;j<4;j++)assert(!mt6797_snapshot_tick(s));
  assert(s->last->terminal&&!s->last->error&&s->last->words==4);
  assert(mt6797_snapshot_control_ops.write(&gate,"0",1,&pos)==1);
  struct reader retained={0};open_file(s,&retained.file);read_thread(&retained);
  assert(retained.result==16&&retained.data[0]==0x100&&retained.data[3]==0x103&&s->generation==1);
  close_file(&gate);close_file(&select);
  struct file removed_status={0};open_file(s,&removed_status);removed_status.f_path.dentry=&status_name;
  mt6797_snapshot_unregister(s);owner_alive=false;
  unsigned int before_inspections=inspections;status_pos=0;memset(text,0,sizeof(text));
  assert(mt6797_snapshot_control_read(&removed_status,text,sizeof(text)-1,&status_pos)>0);
  assert(strstr(text,"readiness_valid=0")&&inspections==before_inspections);
  close_file(&removed_status);
  /* Open reader owns immutable result even after owner removal. */
  assert(retained.data[3]==0x103);close_file(&retained.file);
  assert(!atomic_load(&allocations));
 }
 puts("PASS: 100 rounds, concurrent gate-on reader EBUSY, signal-terminated read/release, open-close during capture, retained generation, owner removal; ASAN/UBSAN. Service shims, NOT mounted debugfs/SIGKILL.");
}
