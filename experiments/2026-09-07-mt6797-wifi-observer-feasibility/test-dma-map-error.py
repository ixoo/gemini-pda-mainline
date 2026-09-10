#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute native port bodies with injected mapping success and failure."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
AHB = 'drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c'
spec = importlib.util.spec_from_file_location('dma_native_map', HERE/'test-dma-native-lifetime.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

CAPTURE = r'''
typedef uint32_t u32;
struct wfc_fw_tx { int unused; };
static int aborted;
static void wfc_dma_abort(void) { assert(HifLock && irq_masked); aborted++; }
#define wfc_dma_map(...) ((void)0)
#define wfc_dma_program(...) ((void)0)
#define wfc_dma_poll_begin(...) ((void)0)
#define wfc_dma_poll_end(...) ((void)0)
#define wfc_dma_unmap(...) ((void)0)
#define wfc_fw_tx_payload(...) ((void)0)
#define wfc_fw_tx_dma(...) ((void)0)
static BOOLEAN wfc_fw_tx_port_return(struct wfc_fw_tx *tx, BOOLEAN result) { (void)tx; return result; }
static int dma_mapping_error(void *dev, ULONG address) {
    assert(dev && HifLock && irq_masked && address==mapped_address);
    mapping_checks++;
    return map_failure;
}
'''

WRAPPER = r'''
static GLUE_INFO_T glue;
static UINT_8 buffer[512];
static int transfer(int tx) {
    return tx ? kalDevPortWriteCapture(&glue,MCR_WTDR1,32,buffer,sizeof(buffer),NULL) :
                kalDevPortRead(&glue,MCR_WRDR0,32,buffer,sizeof(buffer));
}
int run(int tx,int failed,int zero) {
    HifLock=mapped=irq_masked=clocks=WlanDmaFatalErr=fgIsResetting=aborted=mapping_checks=0;
    maps=unmaps=configs=starts=acks=stops=dumps=intr_reads=idle_reads=0;
    map_failure=failed; mapped_address=zero ? 0 : 0x123456780ULL;
    ticks=0; tick_step=1; intr_ready_at=idle_ready_at=2;
    glue=(GLUE_INFO_T){{&ops,TRUE,&ops,registers},NULL}; pfWlanDmaOps=&ops;
    return transfer(tx);
}
int again(int tx) { return transfer(tx); }
'''


def build(tree, support, work, name):
    source=(tree/AHB).read_text()
    shim=native.SHIM.replace('mapped = 1; maps++;','mapped = !map_failure; maps++;')
    shim=shim.replace('dev && mapped && HifLock','dev && (mapped || map_failure) && HifLock')
    callbacks=native.CALLBACKS.replace('irq_masked && mapped &&','irq_masked &&')
    callbacks=callbacks.replace('hif && HifLock && mapped','hif && HifLock')
    code='static int map_failure, mapping_checks;\n'+shim+CAPTURE
    code+=native.native_definitions((support/'hif.h').read_text(),(support/'sdio.h').read_text(),source)
    code+=callbacks
    if 'static void HifDmaMapError(void)' in source:
        code+=native.fixture.function(source,'HifDmaMapError')
    for function in ('kalDevPortRead','kalDevPortWriteCapture'):
        code+='BOOLEAN\n'+native.fixture.function(source,function)
    code+=WRAPPER
    for var in ('maps','unmaps','configs','starts','acks','stops','HifLock','mapped',
                'irq_masked','clocks','aborted','mapping_checks','WlanDmaFatalErr','intr_reads','idle_reads'):
        code+=f'int get_{var}(void) {{ return {var}; }}\n'
    path=work/name
    path.with_suffix('.c').write_text(code)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function',
                    '-Wno-unused-but-set-variable','-shared','-fPIC',str(path.with_suffix('.c')),
                    '-o',str(path.with_suffix('.so'))],check=True)
    return ctypes.CDLL(str(path.with_suffix('.so')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('child',type=Path)
    parser.add_argument('support',type=Path)
    args=parser.parse_args()
    pins=json.loads((HERE/'results/dma-map-error-sources.json').read_text())
    for key,tree in (('parents',args.parent),('outputs',args.child)):
        assert hashlib.sha256((tree/AHB).read_bytes()).hexdigest()==pins[key][AHB]
    for name,digest in pins['support'].items():
        assert hashlib.sha256((args.support/name).read_bytes()).hexdigest()==digest,name
    cases=0
    with tempfile.TemporaryDirectory(prefix='wifi-dma-map-error-') as directory:
        work=Path(directory)
        old,new=[build(tree,args.support,work,name) for tree,name in ((args.parent,'parent'),(args.child,'child'))]
        for tx in (0,1):
            for failed in (0,1):
                for zero in (0,1):
                    before,after=old.run(tx,failed,zero),new.run(tx,failed,zero)
                    assert before==1 and after==int(not failed)
                    assert new.get_maps()==1 and new.get_mapping_checks()==1
                    assert not any(getattr(new,'get_'+n)() for n in ('HifLock','mapped','irq_masked','clocks'))
                    for n in ('configs','starts','acks','stops','unmaps'):
                        assert getattr(old,'get_'+n)()==1
                        assert getattr(new,'get_'+n)()==int(not failed)
                    assert new.get_intr_reads()==new.get_idle_reads()==(0 if failed else 2)
                    assert new.get_aborted()==new.get_WlanDmaFatalErr()==failed
                    if failed:
                        for direction in (0,1): assert new.again(direction)==0
                        assert new.get_maps()==1 and new.get_mapping_checks()==1 and new.get_unmaps()==0
                    cases+=1
    print(f'dma-map-error=pass comparisons={cases}; both invalid-map submissions reproduced and prevented')
    print('scope=actual port bodies with injected DMA/MMIO/locks and stubbed capture; no hardware or timeout recovery')


if __name__=='__main__':
    main()
