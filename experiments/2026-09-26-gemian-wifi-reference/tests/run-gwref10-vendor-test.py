#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the observer's vendor helpers against the pinned gen3 declarations and test them.

Usage: run-gwref10-vendor-test.py <gen3 tree at 59e00a91>

The pinned tree is not vendored here. This script extracts, verbatim and only for
the fixture build, the structure, enumeration and macro declarations the helpers
use (checking that none contains a preprocessor conditional), audits every
structure field the helpers name against the real declarations, and compiles
tests/gwref10-vendor-test.c with lifecycle/gwref10.c in vendor-host mode.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE.parent / 'lifecycle/gwref10.c'

STRUCTS = {  # name -> header
    'WIFI_CMD_T': 'include/nic_cmd_event.h', 'WIFI_EVENT_T': 'include/nic_cmd_event.h',
    'CMD_802_11_KEY': 'include/nic_cmd_event.h', 'CMD_BSS_ACTIVATE_CTRL': 'include/nic_cmd_event.h',
    'CMD_UPDATE_STA_RECORD_T': 'include/nic_cmd_event.h', 'CMD_REMOVE_STA_RECORD_T': 'include/nic_cmd_event.h',
    'CMD_SET_BSS_RLM_PARAM_T': 'include/nic_cmd_event.h',
    'CMD_SET_BSS_INFO': 'include/nic_cmd_event.h', 'EVENT_ADD_KEY_DONE_INFO': 'include/nic_cmd_event.h',
    'EVENT_TX_DONE_T': 'include/nic_cmd_event.h', 'EVENT_ACTIVATE_STA_REC_T': 'include/nic_cmd_event.h',
    'EVENT_LINK_QUALITY_EX': 'include/nic_cmd_event.h', 'CHANNEL_INFO_T': 'include/nic_cmd_event.h',
    'EVENT_SCAN_DONE': 'include/nic_cmd_event.h', 'EVENT_CH_PRIVILEGE_T': 'include/nic_cmd_event.h',
    'EVENT_BSS_BEACON_TIMEOUT_T': 'include/nic_cmd_event.h', 'EVENT_STA_AGING_TIMEOUT_T': 'include/nic_cmd_event.h',
    'EVENT_RX_ADDBA_T': 'include/nic/que_mgt.h', 'EVENT_RX_DELBA_T': 'include/nic/que_mgt.h',
    'EVENT_CHECK_REORDER_BUBBLE_T': 'include/nic/que_mgt.h', 'EVENT_BSS_ABSENCE_PRESENCE_T': 'include/nic/que_mgt.h',
    'EVENT_STA_CHANGE_PS_MODE_T': 'include/nic/que_mgt.h', 'EVENT_STA_UPDATE_FREE_QUOTA_T': 'include/nic/que_mgt.h',
    'HW_MAC_RX_DESC_T': 'include/nic/nic_rx.h', 'HW_MAC_TX_DESC_T': 'include/nic/nic_tx.h',
    'TX_TCQ_STATUS_T': 'include/nic/nic_tx.h',
}
STRUCT_ORDER = ['CHANNEL_INFO_T', 'CMD_SET_BSS_RLM_PARAM_T'] + [n for n in STRUCTS if n not in ('CHANNEL_INFO_T', 'CMD_SET_BSS_RLM_PARAM_T')]
ENUM_MEMBERS = {'CMD_ID_ADD_REMOVE_KEY': 'include/nic_cmd_event.h', 'EVENT_ID_ADD_PKEY_DONE': 'include/nic_cmd_event.h',
                'TX_PACKET_TYPE_MGMT': 'include/nic/nic_tx.h', 'TC4_INDEX': 'include/nic/nic_tx.h',
                'COMMAND_TYPE_NETWORK_IOCTL': 'include/nic/cmd_buf.h'}
MACROS = {
    'include/nic/nic_rx.h': ['RX_STATUS_PKT_TYPE_MASK', 'RX_STATUS_PKT_TYPE_OFFSET', 'RX_STATUS_HTC', 'RX_STATUS_UC2ME',
                             'RX_STATUS_MC_FRAME', 'RX_STATUS_BC_FRAME', 'RX_STATUS_HEADER_LEN_MASK',
                             'RX_STATUS_HEADER_OFFSET', 'RX_STATUS_HEADER_TRAN', 'RX_STATUS_PAYLOAD_FORMAT_MASK',
                             'RX_STATUS_PAYLOAD_FORMAT_OFFSET', 'RX_STATUS_BSSID_MASK', 'RX_STATUS_BSSID_OFFSET',
                             'RX_STATUS_TID_MASK', 'RX_STATUS_SEC_MASK', 'RX_STATUS_SEC_OFFSET',
                             'RX_STATUS_FLAG_CIPHER_MISMATCH', 'HAL_RX_STATUS_GET_RX_BYTE_CNT', 'HAL_RX_STATUS_GET_PKT_TYPE',
                             'HAL_RX_STATUS_IS_UC2ME', 'HAL_RX_STATUS_IS_MC', 'HAL_RX_STATUS_IS_BC',
                             'HAL_RX_STATUS_GET_HEADER_LEN', 'HAL_RX_STATUS_GET_HEADER_OFFSET', 'HAL_RX_STATUS_IS_HEADER_TRAN',
                             'HAL_RX_STATUS_GET_PAYLOAD_FORMAT', 'HAL_RX_STATUS_GET_BSSID', 'HAL_RX_STATUS_GET_WLAN_IDX',
                             'HAL_RX_STATUS_GET_TID', 'HAL_RX_STATUS_GET_SEC_MODE', 'HAL_RX_STATUS_IS_CIPHER_MISMATCH'],
    'include/nic/nic_tx.h': ['TX_DESC_HEADER_FORMAT_MASK', 'TX_DESC_HEADER_FORMAT_OFFSET', 'TX_DESC_TID_MASK',
                             'TX_DESC_TID_OFFSET', 'TX_DESC_PROTECTED_FRAME', 'TX_DESC_GET_FIELD',
                             'HAL_MAC_TX_DESC_GET_HEADER_FORMAT', 'HAL_MAC_TX_DESC_GET_TID', 'HAL_MAC_TX_DESC_IS_PROTECTION'],
    'include/nic/mac.h': ['MAC_ADDR_LEN', 'MASK_FC_TYPE', 'MASK_FC_SUBTYPE', 'MAC_FRAME_TYPE_MGT', 'MAC_FRAME_PROBE_RSP',
                          'MAC_FRAME_BEACON', 'IS_BMCAST_MAC_ADDR', 'EQUAL_MAC_ADDR', 'ELEM_MAX_LEN_SSID'],
    'include/config.h': ['HW_BSSID_NUM', 'CFG_RX_MAX_PKT_SIZE'],
    'include/nic_cmd_event.h': ['EVENT_HDR_SIZE'],
    'os/linux/include/gl_typedef.h': ['BIT', 'BITS', 'OFFSET_OF'],
}
# Fields of our own minimal stand-in structures, audited against the real declarations.
FIELDS = {
    ('BSS_INFO_T', 'include/nic/adapter.h'): ['aucBSSID', 'aucOwnMacAddr'],
    ('ADAPTER_T', 'include/nic/adapter.h'): ['aprBssInfo'],
    ('CMD_INFO_T', 'include/nic/cmd_buf.h'): ['eCmdType', 'u2InfoBufLen', 'pucInfoBuffer', 'ucBssIndex', 'ucStaRecIndex'],
    ('SW_RFB_T', 'include/nic/nic_rx.h'): ['pucRecvBuff', 'prRxStatus', 'pvHeader', 'u2PacketLen'],
    ('MSDU_INFO_T', 'include/nic/nic_tx.h'): ['ucPacketType', 'ucStaRecIndex', 'ucBssIndex', 'ucWlanIndex', 'fgIs802_1x',
                                             'fgIs802_11', 'u2FrameLength', 'ucPID', 'ucTC'],
    ('STA_RECORD_T', 'include/mgmt/cnm_mem.h'): ['ucIndex', 'ucWlanIndex', 'ucBssIndex', 'ucStaState'],
}


def block(text, name):
    """The verbatim typedef struct block ending in '} NAME' with no preprocessor line inside."""
    end = re.search(r'^\}\s*' + re.escape(name) + r'\s*[,;].*$', text, re.M)
    assert end, 'struct %s not found' % name
    start = text.rfind('typedef struct', 0, end.start())
    body = text[start:end.end()]
    assert not re.search(r'^\s*#', body, re.M), 'preprocessor line inside ' + name
    return body


def enum_block(text, member):
    """The verbatim typedef enum block; its conditionals are resolved by the C preprocessor later."""
    position = re.search(r'^\s*' + re.escape(member) + r'\b', text, re.M)
    assert position, member
    start = text.rfind('typedef enum', 0, position.start())
    end = text.index('}', position.end())
    end = text.index(';', end) + 1
    return text[start:end]


def makefile_defines(tree):
    """The literal -D flags the gen3 Makefile passes, plus the platform ones it derives."""
    flags = ['-DLINUX', '-DMT6797']
    for line in (tree / 'Makefile').read_text().splitlines():
        if line.startswith('ccflags-y') and '-D' in line and '$(' not in line:
            flags += [token for token in line.split() if token.startswith('-D')]
    return flags


def preprocess_enums(tree, blocks):
    """Resolve the enums' conditionals exactly as the kernel build does: the real config.h and -D flags."""
    source = '#include "config.h"\n#include "nic/nic_tx.h"\nGWREF10_MARKER\n' + '\n'.join(blocks) + '\n'
    with tempfile.TemporaryDirectory(prefix='gwref10-cpp-') as tmp:
        path = pathlib.Path(tmp) / 'enums.c'
        path.write_text(source)
        shim = pathlib.Path(tmp) / 'shim.h'
        shim.write_text('typedef unsigned char UINT_8, BOOLEAN, BOOL, *PUINT_8, *P_UINT_8; typedef signed char INT_8;\n'
                        'typedef unsigned short UINT_16; typedef unsigned int UINT_32; typedef int INT_32;\n'
                        'typedef unsigned long long UINT_64; typedef void *PVOID; typedef void VOID;\n')
        out = subprocess.run(['cpp', '-P', '-nostdinc', '-undef', '-include', str(shim),
                              '-I', str(tree / 'include'), '-I', str(tree / 'include/nic'),
                              '-I', str(tree / 'os/linux/include')] + makefile_defines(tree) + [str(path)],
                             check=True, capture_output=True, text=True).stdout
    return out.split('GWREF10_MARKER', 1)[1]


def macro_lines(text, name):
    match = re.search(r'^#define\s+' + re.escape(name) + r'\b(?:[^\n]*\\\n)*[^\n]*$', text, re.M)
    assert match, 'macro %s not found' % name
    return match.group(0)


def struct_fields(text, name):
    body = block(text, name) if name not in ('SW_RFB_T', 'ADAPTER_T', 'BSS_INFO_T', 'CMD_INFO_T', 'MSDU_INFO_T', 'STA_RECORD_T') else None
    if body is None:
        start = re.search(r'^(typedef )?struct _' + re.escape(name) + r'\s*\{', text, re.M)
        assert start, name
        depth, i = 0, start.end() - 1
        while True:
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
            if depth == 0:
                break
        body = text[start.start():i]
    return set(re.findall(r'\b(\w+)\s*(?:\[[^\]]*\])*\s*;', body))


def main():
    if len(sys.argv) != 2 or not pathlib.Path(sys.argv[1]).is_dir():
        sys.exit('usage: run-gwref10-vendor-test.py <gen3 tree at 59e00a91>')
    tree = pathlib.Path(sys.argv[1])
    texts = {}

    def text(rel):
        if rel not in texts:
            texts[rel] = (tree / rel).read_text(errors='replace')
        return texts[rel]

    for (name, rel), fields in FIELDS.items():
        missing = set(fields) - struct_fields(text(rel), name)
        assert not missing, 'fields missing from the pinned %s: %s' % (name, sorted(missing))
    out = ['/* generated for the fixture from the pinned gen3 tree; not vendored */',
           '#include <stdint.h>', '#include <string.h>',
           'typedef uint8_t UINT_8, *PUINT_8, BOOLEAN, BOOL; typedef int8_t INT_8; typedef uint16_t UINT_16;',
           'typedef uint32_t UINT_32; typedef int32_t INT_32; typedef uint64_t UINT_64; typedef void *PVOID;',
           '#define TRUE 1', '#define FALSE 0', '#define kalMemCmp memcmp']
    for rel, names in MACROS.items():
        for name in names:
            out.append(macro_lines(text(rel), name))
    out.append(preprocess_enums(tree, [enum_block(text(rel), member) for member, rel in ENUM_MEMBERS.items()]))
    for name in STRUCT_ORDER:
        out.append(block(text(STRUCTS[name]), name))
    header = '\n'.join(out) + '\n'
    with tempfile.TemporaryDirectory(prefix='gwref10-vendor-') as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / 'gwref10-vendor-gen.h').write_text(header)
        if os.environ.get('GWREF10_KEEP_HEADER'):
            pathlib.Path(os.environ['GWREF10_KEEP_HEADER']).write_text(header)
        binary = tmp / 'gwref10-vendor-test'
        subprocess.run(['cc', '-std=gnu99', '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-pthread',
                        '-I', str(tmp), '-I', str(HERE), '-o', str(binary), str(HERE / 'gwref10-vendor-test.c')], check=True)
        sys.exit(subprocess.run([str(binary)], timeout=120).returncode)


if __name__ == '__main__':
    main()
