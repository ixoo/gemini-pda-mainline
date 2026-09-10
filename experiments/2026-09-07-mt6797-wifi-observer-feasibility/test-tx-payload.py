#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Actual native section, staging and DMA path with injected hardware and crypto."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tx_dma',HERE/'test-dma-capture.py');dma=importlib.util.module_from_spec(spec);spec.loader.exec_module(dma)
r=dma.r
BASE='drivers/misc/mediatek/connectivity/wlan/gen3/'
HIF=BASE+'os/linux/hif/ahb_sdioLike/'
SHIM=r'''
typedef uint16_t u16;
typedef void *PVOID;
typedef u32 WLAN_STATUS, *PUINT_32;
#define WLAN_STATUS_SUCCESS 0
#define WLAN_STATUS_FAILURE 0xc0000001U
#define DEBUGFUNC(...) ((void)0)
#define CFG_ENABLE_FW_DOWNLOAD 1
#define CFG_ENABLE_FW_DIVIDED_DOWNLOAD 1
#define CMD_PKT_SIZE_FOR_IMAGE 2048
#define INIT_CMD_PDA_PQ_ID 0xc000
#define INIT_CMD_PDA_PACKET_TYPE_ID 0xa0
#define ACPI_STATE_D3 3
#define HIF_TX_HDR_TX_BYTE_COUNT_MASK 0xffff
#define TFCB_FRAME_PAD_TO_DW ALIGN_4
#define __aligned(n) __attribute__((aligned(n)))
#define CRYPTO_MINALIGN_ATTR __aligned(8)
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define memzero_explicit(p,n) memset(p,0,n)
#define min(a,b) ((a)<(b)?(a):(b))
#define ALIGN(n,a) (((n)+(a)-1)&~((a)-1))
u16 get_unaligned_le16(const u8 *p) { return p[0] | ((u16)p[1]<<8); }
struct task_struct { int id; } tasks[2];
static struct task_struct *current;
struct _ADAPTER_T { struct { u8 *pucTxCoalescingBufPtr; } rTxCtrl;
    u32 u4CoalescingBufCachedSize; P_GLUE_INFO_T prGlueInfo; int rAcpiState; };
typedef struct _ADAPTER_T ADAPTER_T, *P_ADAPTER_T;
typedef __typeof__(((P_ADAPTER_T)0)->rTxCtrl) *P_TX_CTRL_T;
struct _CMD_INFO_T { u16 u2InfoBufLen; u8 *pucInfoBuffer; };
typedef struct _CMD_INFO_T CMD_INFO_T, *P_CMD_INFO_T;
typedef struct { u16 u2TxByteCount, u2PQ_ID;
    struct { u8 ucCID, ucPktTypeID, ucSeqNum, ucReserved; u8 aucBuffer[]; } rInitWifiCmd;
} INIT_HIF_TX_HEADER_T, *P_INIT_HIF_TX_HEADER_T;
typedef struct { u32 u4Offset; u8 ucKIdx, ucEnc; u16 u2Reserved; u32 u4Length, u4DestAddr; } SECTION;
typedef struct { u32 u4Signature,u4CRC,u4NumOfEntries; u16 major,minor;
    u32 chip,reserved; SECTION arSection[]; } FIRMWARE_DIVIDED_DOWNLOAD_T,*P_FIRMWARE_DIVIDED_DOWNLOAD_T;
static GLUE_INFO_T glue;
static ADAPTER_T adapter;
static u8 firmware[WFC_FW_BYTES];
static u32 staging_words[1024], packet_words[514];
static CMD_INFO_T cmd;
static int mode;
static unsigned int allocations, frees, hashes, cfg_count, chunk_calls;
static u8 submitted[8][2560];
static unsigned int submitted_size[8];
static struct crypto_shash { int marker; } algorithm;
struct sha256_state { u32 state[8]; u64 count; u8 buf[64]; };
struct shash_desc { struct crypto_shash *tfm; u32 flags; void *__ctx[] CRYPTO_MINALIGN_ATTR; };
static int (*hash_callback)(const void *,u32,void *);
void set_hash(int (*p)(const void *,u32,void *)) { hash_callback=p; }
static struct crypto_shash *crypto_alloc_shash(const char *name,u32 type,u32 mask) {
    assert(!strcmp(name,"sha256-generic")&&!type&&!mask); allocations++; return &algorithm;
}
static unsigned int crypto_shash_descsize(struct crypto_shash *p) { assert(p==&algorithm);return sizeof(struct sha256_state); }
static unsigned int crypto_shash_digestsize(struct crypto_shash *p) { assert(p==&algorithm);return 32; }
static int crypto_shash_digest(struct shash_desc *desc,const u8 *bytes,u32 length,u8 *out) {
    assert(desc->tfm==&algorithm&&!desc->flags);
    assert((bytes==firmware && length==sizeof(firmware)) ||
           (!mapped && bytes==(u8 *)staging_words+8 && length<=2048));
    hashes++;
    if(mode==7 && hashes==2) return -EIO;
    return hash_callback(bytes,length,out);
}
static void crypto_free_shash(struct crypto_shash *p) { assert(p==&algorithm);frees++; }
static bool mt6797_wfc_request_firmware(u32 stage,u32 device,u32 image,int status) {
    assert((stage==2||stage==3)&&device==1&&image==1&&!status);return true;
}
static P_CMD_INFO_T cmdBufAllocateCmdInfo(P_ADAPTER_T p,u32 bytes) {
    assert(p==&adapter&&bytes<=sizeof(packet_words));chunk_calls++;
    if(mode==8) return NULL;
    memset(packet_words,0xa5,sizeof(packet_words));cmd.pucInfoBuffer=(u8 *)packet_words;return &cmd;
}
static void cmdBufFreeCmdInfo(P_ADAPTER_T p,P_CMD_INFO_T command) { assert(p==&adapter&&command==&cmd); }
static void kalMemCopy(void *dst,const void *src,size_t bytes) {
    memcpy(dst,src,bytes);
    if(dst==staging_words) {
        if(mode==2) ((u8 *)dst)[8]^=1;
        if(mode==3) current=&tasks[1];
    }
}
static WLAN_STATUS wlanImageSectionConfig(P_ADAPTER_T p,u32 dest,u32 bytes,BOOLEAN first,BOOLEAN enc,u8 key) {
    assert(p==&adapter&&dest&&bytes&&enc&&!key);(void)first;cfg_count++;return 0;
}
'''
WRAPPER=r'''
u32 run_case(int enabled,int fault) {
    mode=fault;loss_count=0;current=&tasks[0];
    HifLock=mapped=irq_masked=clocks=WlanDmaFatalErr=fgIsResetting=0;
    maps=unmaps=configs=starts=acks=stops=dumps=intr_reads=idle_reads=0;
    io_count=poll_kind=0;ticks=0;tick_step=1;
    intr_ready_at=mode==4?UINT32_MAX:2;idle_ready_at=2;
    allocations=frees=hashes=cfg_count=chunk_calls=0;
    memset(pdma,0,sizeof(pdma));pdma[6]=0x65432;pdma[21]=0x12;pdma[22]=0x34;
    memset(memory,0,sizeof(memory));memset(&state,0,sizeof(state));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    wfc_devices.counter=wfc_transactions.counter=0;
    memset(&glue,0,sizeof(glue));
    glue.rHifInfo.Dev=&ops;glue.rHifInfo.fgDmaEnable=TRUE;glue.rHifInfo.DmaOps=&ops;
    glue.rHifInfo.HifRegBaseAddr=registers;glue.rHifInfo.DmaRegBaseAddr=pdma;
    memset(&adapter,0,sizeof(adapter));adapter.prGlueInfo=&glue;glue.prAdapter=&adapter;
    adapter.rTxCtrl.pucTxCoalescingBufPtr=(u8 *)staging_words;adapter.u4CoalescingBufCachedSize=sizeof(staging_words);
    memset(staging_words,0xa5,sizeof(staging_words));memset(submitted,0,sizeof(submitted));
    memset(submitted_size,0,sizeof(submitted_size));pfWlanDmaOps=&ops;g_sdio_func.use_dma=mode!=5;
    memset(firmware,0,sizeof(firmware));put_unaligned_le32(0x454b544d,firmware);put_unaligned_le32(4,firmware+8);
    unsigned int offsets[]={88,5928,14920,346216},lengths[]={5840,8992,331296,65392};
    for(unsigned int i=0;i<4;i++) {
        u8 *section=firmware+24+i*16;
        put_unaligned_le32(offsets[i],section);section[5]=i<2;
        put_unaligned_le32(lengths[i],section+8);put_unaligned_le32(0x10001000+i*0x100000,section+12);
        for(unsigned int j=0;j<lengths[i];j++)firmware[offsets[i]+j]=(u8)(i+j);
    }
    if(enabled) {
        u8 cycle[16],identity[80];
        for(unsigned int i=0;i<16;i++)cycle[i]=i;
        for(unsigned int i=0;i<80;i++)identity[i]=i;
        assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    }
    wfc_dma_bind(&glue.rHifInfo.capture,&ops,1);
    struct wfc_fw_buffer read={firmware,sizeof(firmware),1,1};
    struct wfc_fw_image image;
    wfc_fw_image_begin(&image,&glue.rHifInfo.capture,&read,firmware,sizeof(firmware),firmware);
    if(mode==1)fgIsResetting=1;
    u32 status=0;
    for(unsigned int i=0;i<4;i++) {
        wfc_fw_image_section(&image,i);
        if(i<2) {
            status=STAGE_CALL;
            if(status)break;
        }
    }
    status=wfc_fw_image_return(&image,status);
    wfc_dma_unbind(&glue.rHifInfo.capture);
    u8 terminal[4]={1,0,0,0};
    if(ramoops_capture_active())ramoops_capture_append(255,0,terminal,4);
    return status;
}
u8 *data(void){return memory;}
u8 *image_data(void){return firmware;}
u8 *bus_data(void){return (u8 *)submitted;}
u32 *accesses(void){return io_log;}
unsigned int access_count(void){return io_count;}
unsigned int hash_count(void){return hashes;}
unsigned int stores(void){return writes;}
unsigned int allocation_count(void){return allocations;}
unsigned int free_count(void){return frees;}
'''

GUARDS = r'''
void run_guard(unsigned int fault) {
    /* A fresh simulated boot; no device or native reset operation. */
    run_case(0,0);current=&tasks[0];
    memset(memory,0,sizeof(memory));memset(&state,0,sizeof(state));
    reads=writes=barriers=trace_length=cut=drop=fault_read=0;
    wfc_devices.counter=wfc_transactions.counter=0;
    u8 cycle[16],identity[80];
    for(unsigned int i=0;i<16;i++)cycle[i]=i;
    for(unsigned int i=0;i<80;i++)identity[i]=i;
    assert(!wfc_writer_begin(&state,memory,sizeof(memory),cycle,identity));
    wfc_dma_bind(&glue.rHifInfo.capture,&ops,1);
    struct wfc_dma_trace *binding=&glue.rHifInfo.capture;
    struct wfc_fw_buffer read={firmware,sizeof(firmware),1,1};
    struct wfc_fw_image image;struct wfc_fw_tx tx;
    wfc_fw_image_begin(&image,binding,&read,firmware,sizeof(firmware),firmware);
    wfc_fw_image_section(&image,0);
    if(fault==1)current=&tasks[1];
    wfc_fw_tx_begin(&tx,&image,firmware+88+(fault==2),fault==3?2047:2048);
    if(fault==4)current=&tasks[1];
    u8 *packet=(u8 *)packet_words,*staged=(u8 *)staging_words;
    put_unaligned_le16(2056,packet);put_unaligned_le16(0xc000,packet+2);
    packet[4]=0;packet[5]=0xa0;packet[6]=0;
    memcpy(packet+8,firmware+88,2048);memcpy(staged,packet,2056);
    wfc_fw_tx_command(&tx,firmware+88,2048,fault==5?NULL:packet,2056+(fault==6));
    if(fault==7)current=&tasks[1];
    wfc_fw_tx_staged(&tx,packet+(fault==8),2056,staged,2056+(fault==9),fault==10?2055:4096);
    if(fault==11)current=&tasks[1];
    if(fault==12)binding->retired.counter=1;
    if(fault==13)staged[2]^=1;
    wfc_fw_tx_payload(&tx,fault==14?NULL:binding,staged+(fault==15),2056,
                      fault==16?2055:2560,fault==17?2559:4096,fault==18?0x30:0x34);
    if(fault==19)wfc_fw_tx_payload(&tx,binding,staged,2056,2560,4096,0x34);
    if(fault==20)current=&tasks[1];
    binding->transaction=fault==21?0:1;
    wfc_fw_tx_dma(&tx,fault==22?NULL:binding);
    if(fault==23)wfc_fw_tx_dma(&tx,binding);
    binding->transaction=fault==24?1:0;
    if(fault==25)current=&tasks[1];
    wfc_fw_tx_port_return(&tx,fault==26?0:1);
    if(fault==27)wfc_fw_tx_port_return(&tx,1);
    if(fault==28)current=&tasks[1];
    wfc_fw_tx_finish(&tx,fault==29?0xc0000001U:0);
    assert(!image.transaction&&!ramoops_capture_active());
    wfc_fw_image_return(&image,0);
}
'''

def build(root, parent, changed, support, child):
 tree=changed if child else parent
 helpers=changed/HIF
 source='static unsigned int loss_site,loss_count;\n'+dma.writer.SHIM+dma.without_includes((HERE/'capture-slot-writer.h').read_text())+dma.EXTRA
 source=source.replace('{ return wfc_slot_write(&state, kind, tx, p, n); }','{ if(kind==7 && n>=4 && get_unaligned_le32(p)>=12 && get_unaligned_le32(p)<=14 && ++loss_count==loss_site) drop=writes+1; return wfc_slot_write(&state, kind, tx, p, n); }')
 for rel in ('include/hif_capture.h','hif_capture.c'):source+=dma.without_includes((helpers/rel).read_text())
 source+='typedef uint16_t u16;\n'+dma.without_includes((tree/HIF/'include/hif_fw_capture.h').read_text())
 shim=dma.native.SHIM.replace('typedef int BOOLEAN, MTK_WCN_BOOL;','typedef uint8_t BOOLEAN; typedef int MTK_WCN_BOOL;').replace('#define MCR_WTDR1 4','#define MCR_WTDR1 0x34')
 start=shim.index('static void writel(');end=shim.index('static void wmb(',start);shim=shim[:start]+dma.MMIO+shim[end:]
 shim=shim.replace('void *HifRegBaseAddr; }','void *HifRegBaseAddr; void *DmaRegBaseAddr; struct wfc_dma_trace capture; }').replace('typedef struct { GL_HIF_INFO_T rHifInfo;','typedef struct _GLUE_INFO_T { GL_HIF_INFO_T rHifInfo;')
 # Snapshot exactly the actual mapped extent in the injected DMA backend.
 shim=shim.replace('static ULONG dma_map_single(', 'static void snapshot(const void *,size_t);\nstatic ULONG dma_map_single(').replace('mapped = 1; maps++;','snapshot(buffer,length); mapped = 1; maps++;')
 source+=shim+SHIM
 source+='static void snapshot(const void *p,size_t n){assert(maps<8&&n<=2560);if(mode==6)((u8 *)p)[8]^=1;memcpy(submitted[maps],p,n);submitted_size[maps]=n;}\n'
 hif=(support/'hif.h').read_text();ahb=(tree/HIF/'ahb.c').read_text()
 source+=dma.native.native_definitions(hif,(support/'sdio.h').read_text(),ahb)+dma.without_includes((support/'hif_pdma.h').read_text())
 for name in ('HIF_DMAR_READL','HIF_DMAR_WRITEL'):source+=re.search(r'^#define '+name+r'[^\n]*\\\n[^\n]*',hif,re.M).group()+'\n'
 pdma=(support/'ahb_pdma-capture.c').read_text()
 for name in ('Config','Start','Stop','PollIntr','PollStart','AckIntr'):source+=dma.native.fixture.function(pdma,'HifPdma'+name)
 source+=dma.CALLBACKS+dma.without_includes((tree/HIF/'hif_fw_capture.c').read_text())
 name='kalDevPortWriteCapture' if child else 'kalDevPortWrite';source+='BOOLEAN\n'+dma.native.fixture.function(ahb,name)
 if child:source+=dma.native.fixture.function(ahb,'kalDevPortWrite')
 hal=(tree/BASE/'include/nic/hal.h').read_text()
 names=('HAL_PORT_WR','HAL_WRITE_TX_PORT')
 for name in names:
  matches=re.findall(r'^#define '+name+r'\([^\n]*\n(?:[^\n]*\\\n)*[^\n]*',hal,re.M);assert matches,name;source+=matches[-1]+'\n'
 nic=(tree/BASE/'nic/nic_tx.c').read_text();source+=dma.native.fixture.function(nic,'nicTxInitCmdCapture'if child else'nicTxInitCmd')
 wl=(tree/BASE/'common/wlan_lib.c').read_text()
 source+='WLAN_STATUS\n'+dma.native.fixture.function(wl,'wlanFwChunkCapture'if child else'wlanImageSectionDownload') if child else dma.native.fixture.function(wl,'wlanImageSectionDownload')
 source+='WLAN_STATUS\n'+dma.native.fixture.function(wl,'wlanImageSectionDownloadStage')
 call='wlanImageSectionDownloadStage(&adapter,firmware,i,sizeof(firmware),TRUE,0'+(',&image)'if child else')')
 source+=WRAPPER.replace('STAGE_CALL',call)+'\nvoid set_loss(unsigned int n){loss_site=n;}\n'
 if child:source+=GUARDS
 p=root/('child'if child else'parent');p.with_suffix('.c').write_text(source)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-fPIC','-shared',str(p.with_suffix('.c')),'-o',str(p.with_suffix('.so'))],check=True)
 c=ctypes.CDLL(str(p.with_suffix('.so')))
 for name in ('data','image_data','bus_data'):getattr(c,name).restype=ctypes.POINTER(ctypes.c_ubyte)
 c.accesses.restype=ctypes.POINTER(ctypes.c_uint32);c.run_case.restype=ctypes.c_uint32
 callback=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p)
 def digest(address,length,out):ctypes.memmove(out,hashlib.sha256(ctypes.string_at(address,length)).digest(),32);return 0
 c.callback=callback(digest);c.set_hash(c.callback);return c

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--parent', type=Path, required=True)
 parser.add_argument('--tree', type=Path, required=True)
 parser.add_argument('--support', type=Path, required=True)
 options=parser.parse_args()
 pins=json.loads((HERE/'results/tx-payload-sources.json').read_text())
 for label, tree in (('parents', options.parent), ('outputs', options.tree)):
  for name, digest in pins[label].items():
   assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest, name
 for entry in json.loads((HERE/'results/dma-hook-sources.json').read_text())['sources']:
  assert hashlib.sha256((options.support/Path(entry['path']).name).read_bytes()).hexdigest()==entry['sha256']
 dma_pins=json.loads((HERE/'results/dma-capture-sources.json').read_text())['outputs']
 for name in ('include/hif_capture.h','hif_capture.c'):
  assert hashlib.sha256((options.tree/HIF/name).read_bytes()).hexdigest()==dma_pins[HIF+name]
 assert hashlib.sha256((options.support/'ahb_pdma-capture.c').read_bytes()).hexdigest()==dma_pins[HIF+'ahb_pdma.c']
 with tempfile.TemporaryDirectory(prefix='wifi-tx-test-')as directory:
  root=Path(directory)
  parent,child=[build(root,options.parent,options.tree,options.support,x)for x in(False,True)]
  parent.run_case(0,0)
  raw=bytes(parent.image_data()[:411632]);sections=[];digests=[]
  for i in range(4):
   offset,key,enc,_,length,dest=struct.unpack_from('<IBBHII',raw,24+i*16)
   sections.append((offset,length,dest,enc,key))
   if i<2:
    digests.extend(hashlib.sha256(raw[offset+j:offset+min(j+2048,length)]).digest()for j in range(0,length,2048))
  args=(dma.writer.CYCLE,hashlib.sha256(raw).digest(),len(raw),sections,digests)
  for mode in (0,1,2,3,4,5,6,7,8):
   a=parent.run_case(0,mode);effects=list(parent.accesses()[:parent.access_count()]);bus=bytes(parent.bus_data()[:8*2560])
   for enabled in (0,1):
    b=child.run_case(enabled,mode);assert a==b,(mode,enabled,a,b)
    assert effects==list(child.accesses()[:child.access_count()]),(mode,'effects')
    assert bus==bytes(child.bus_data()[:8*2560]),(mode,'bus')
    if not enabled:assert child.stores()==child.hash_count()==child.allocation_count()==0
    else:
     data,result=dma.stream(child)
     if mode in (0,6):
      assert r.check_image_tx(data,*args)['checked_payload_chunks']==list(range(1,9))
      assert child.hash_count()==10 and child.allocation_count()==child.free_count()==1
     else:
      try:r.check_image_tx(data,*args)
      except ValueError:pass
      else:raise AssertionError(('accepted fault',mode))
     assert child.allocation_count()==child.free_count()==1
  child.run_case(1,0)
  valid,_=dma.stream(child)
  rows=r.decode(valid,dma.writer.CYCLE)
  def packed(items):return b''.join(r.encode(row['kind'],i,dma.writer.CYCLE,row['transaction'],row['payload'])for i,row in enumerate(items))
  def refused(data):
   try:r.check_image_tx(data,*args)
   except ValueError:return
   raise AssertionError('malformed TX accepted')
  for index,row in enumerate(rows):
   if row['kind']!=7 or int.from_bytes(row['payload'][:4],'little')not in(12,13,14):continue
   refused(packed(rows[:index]+rows[index+1:]))
   refused(packed(rows[:index]+[row]+rows[index:]))
   limit=32 if int.from_bytes(row['payload'][:4],'little')==12 else len(row['payload'])
   for byte in list(range(4,limit,4))+[len(row['payload'])-1]:
    payload=bytearray(row['payload']);payload[byte]^=1
    changed=dict(row,payload=bytes(payload))
    try:mutated=packed(rows[:index]+[changed]+rows[index+1:])
    except ValueError:continue
    refused(mutated)
   if int.from_bytes(row['payload'][:4],'little')==13:
    moved=rows.copy();entry=moved.pop(index);moved.insert(index-1,entry);refused(packed(moved))
   if int.from_bytes(row['payload'][:4],'little')==14:
    moved=rows.copy();entry=moved.pop(index);moved.insert(index-1,entry);refused(packed(moved))
  for fault in range(1,30):child.run_guard(fault)
  parent.run_case(0,0);effects=list(parent.accesses()[:parent.access_count()]);bus=bytes(parent.bus_data()[:8*2560])
  for lost in range(1,25):
   child.set_loss(lost);assert child.run_case(1,0)==0
   assert effects==list(child.accesses()[:child.access_count()])
   assert bus==bytes(child.bus_data()[:8*2560])
   data,_=dma.stream(child);refused(data)
  print('native TX comparison; 29 guards, 24 lost records and CRC-valid mutations passed')


if __name__ == "__main__":
 main()
