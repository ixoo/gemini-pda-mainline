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
    'CHANNEL_INFO_T': 'include/nic_cmd_event.h',
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
    'include/nic_cmd_event.h': ['EVENT_HDR_SIZE'],
    'include/config.h': ['HW_BSSID_NUM', 'CFG_RX_MAX_PKT_SIZE'],
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
    """The typedef struct block ending in '} NAME' from preprocessed header text (so a definition that the
    pinned configuration compiles out, such as EVENT_LINK_QUALITY_EX, is absent and the fixture fails)."""
    end = re.search(r'^\}\s*' + re.escape(name) + r'\s*[,;].*$', text, re.M)
    assert end, 'struct %s not found in the preprocessed pinned headers' % name
    start = text.rfind('typedef struct', 0, end.start())
    body = text[start:end.end()]
    assert not re.search(r'^\s*#', body, re.M), 'preprocessor line inside ' + name
    return body


def preprocess_header(tree, rel):
    """The header as the kernel build sees it: the real config.h and the Makefile's -D flags, then cpp."""
    with tempfile.TemporaryDirectory(prefix='gwref10-cpp-') as tmp:
        shim = pathlib.Path(tmp) / 'shim.h'
        shim.write_text('typedef unsigned char UINT_8, BOOLEAN, BOOL, *PUINT_8, *P_UINT_8; typedef signed char INT_8;\n'
                        'typedef unsigned short UINT_16; typedef unsigned int UINT_32; typedef int INT_32;\n'
                        'typedef unsigned long long UINT_64; typedef void *PVOID; typedef void VOID;\n')
        source = pathlib.Path(tmp) / 'header.c'
        source.write_text('#include "config.h"\nGWREF10_MARKER\n#include "%s"\n' % (tree / rel))
        # gl_vendor.h pulls in Linux headers and defines no type used here; an empty stand-in
        # in the temporary include directory lets the pinned declarations preprocess without a
        # kernel tree.
        (pathlib.Path(tmp) / 'gl_vendor.h').write_text('')
        out = subprocess.run(['cpp', '-P', '-nostdinc', '-undef', '-include', str(shim), '-I', tmp,
                              '-I', str(tree / 'include'), '-I', str(tree / 'include/nic'),
                              '-I', str(tree / 'include/mgmt'), '-I', str(tree / 'os/linux/include')]
                             + makefile_defines(tree) + [str(source)],
                             check=True, capture_output=True, text=True).stdout
    return out.split('GWREF10_MARKER', 1)[1]


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
    preprocessed = {}
    for name in STRUCT_ORDER:
        rel = STRUCTS[name]
        if rel not in preprocessed:
            preprocessed[rel] = preprocess_header(tree, rel)
        out.append(block(preprocessed[rel], name))
    # The feature flags that decide which declarations exist, resolved exactly as the kernel build does.
    resolved = subprocess.run(['cpp', '-P', '-nostdinc', '-undef', '-I', str(tree / 'include')] + makefile_defines(tree) + ['-'],
                              input='#include "config.h"\nGWREF10_MARKER CFG_SUPPORT_P2P_RSSI_QUERY CFG_ENABLE_WIFI_DIRECT\n',
                              check=True, capture_output=True, text=True).stdout.split('GWREF10_MARKER', 1)[1].split()
    assert resolved[0] == '0', 'CFG_SUPPORT_P2P_RSSI_QUERY must resolve to 0 in the pinned configuration: %r' % resolved
    assert 'EVENT_LINK_QUALITY_EX' not in preprocessed['include/nic_cmd_event.h'], \
        'EVENT_LINK_QUALITY_EX must be compiled out of the pinned headers'
    assert 'EVENT_LINK_QUALITY_V2' in preprocessed['include/nic_cmd_event.h']
    code = re.sub(r'/\*.*?\*/', '', SOURCE.read_text(), flags=re.S)   # comments may name it; code may not
    assert 'EVENT_LINK_QUALITY_EX' not in code, 'the observer must not use the compiled-out link-quality structure'
    header = '\n'.join(out) + '\n'
    with tempfile.TemporaryDirectory(prefix='gwref10-vendor-') as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / 'gwref10-vendor-gen.h').write_text(header)
        if os.environ.get('GWREF10_KEEP_HEADER'):
            pathlib.Path(os.environ['GWREF10_KEEP_HEADER']).write_text(header)
        # Two oracles of the same fixture: a sanitized build (address and undefined-behaviour
        # instrumentation) and a plain build; both must exit 0. The sanitized binary runs with
        # address-space randomisation off, as the other C fixtures do, and with the sanitizer's
        # signal handlers disabled. Twice on this host a sanitized run printed only
        # "AddressSanitizer:DEADLYSIGNAL" repeatedly, never a bug report, until the runner's
        # timeout; fifteen bounded reruns of the same binaries (randomisation on and off, plain)
        # all passed, so the cause is unproven. The runner therefore keeps every nonzero exit,
        # signal death and timeout visible as a failure and claims nothing about the cause.
        common = ['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-pthread',
                  '-I', str(tmp), '-I', str(HERE), str(HERE / 'gwref10-vendor-test.c')]
        sanitized = tmp / 'gwref10-vendor-test.asan'
        plain = tmp / 'gwref10-vendor-test.plain'
        subprocess.run(common + ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-o', str(sanitized)], check=True)
        subprocess.run(common + ['-o', str(plain)], check=True)
        env = dict(os.environ, ASAN_OPTIONS='handle_segv=0:handle_sigbus=0:handle_sigfpe=0:handle_abort=0:detect_leaks=1',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        machine = os.uname().machine
        results = {}
        for label, argv in (('sanitized', ['setarch', machine, '-R', str(sanitized)]), ('plain', [str(plain)])):
            try:
                results[label] = subprocess.run(argv, env=env, timeout=120).returncode
            except subprocess.TimeoutExpired:
                results[label] = 'timeout'
            print('%s fixture exit=%s' % (label, results[label]))
        sys.exit(0 if all(rc == 0 for rc in results.values()) else 1)


if __name__ == '__main__':
    main()
