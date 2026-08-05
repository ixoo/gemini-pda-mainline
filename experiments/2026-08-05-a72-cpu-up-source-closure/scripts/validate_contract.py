#!/usr/bin/env python3
"""Validate the source-only A72 CPU-up closure contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Iterable


class ContractError(RuntimeError):
    """A frozen source-closure invariant was violated."""


SCRIPT = Path(__file__).resolve()
EXPERIMENT = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
RESULTS = EXPERIMENT / "results"
README = EXPERIMENT / "README.md"
DESIGN = EXPERIMENT / "DESIGN.md"
TRANSCRIPT = RESULTS / "contract-validation-20260805.txt"
OPTIONAL_TRANSCRIPT = RESULTS / "optional-evidence-validation-20260805.txt"

SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "f6f7aff7e8db59520eee22c52e726d91401ab209c6dc47e87024eefd215310d1"
SOURCE_STATE_SHA256 = "001976aca83e752b36d76e5b8b0ba40addd741cc8e31e6c046e27b9890db2b41"
CONFIG_SHA256 = "f655beba038ad5d98f3af5897fb080329d45781b637ab7dcb409e8a353c54440"
MANIFEST_SHA256 = "ea55ec7dd39ef96ed0d69f008405a8f5776bd3afe599ab4da9ea688d4c83687a"
SERIES_SHA256 = "592db4ae3bde6504786ff28e37e538b589bad83e3d61f52569db2ed9a5a609cf"
PATCH_0092_SHA256 = "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5"
PATCH_0092 = "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"

TABLES = {
    "source": {
        "path": RESULTS / "source-inventory.tsv",
        "fields": ("id", "scope", "artifact", "sha256", "source_anchor",
                   "observation", "decision"),
        "ids": tuple(f"S{i:02d}" for i in range(1, 56)),
        "sha256": "f5d61e515f4781618abeec1f4b3ed4840a0c4c96ec62aa35d5bc4d0d6a1c9c6f",
    },
    "config": {
        "path": RESULTS / "config-inventory.tsv",
        "fields": ("id", "option", "selected_value", "reachability",
                   "closure_effect"),
        "ids": tuple(f"C{i:02d}" for i in range(1, 48)),
        "sha256": "a24f85dea4ed4ae1549e7ee0dfc7ffaeff2356877f1ddccf17c1c27a317fca80",
    },
    "capability": {
        "path": RESULTS / "capability-admission.tsv",
        "fields": ("id", "capability", "early_a53_state", "late_a72_state",
                   "detection_basis", "required_side_effect", "acceptance",
                   "failure"),
        "ids": tuple(f"K{i:02d}" for i in range(1, 14)),
        "sha256": "d1dbfe5873deb9f5f4df1bb235593f9fcaf025debfb3cbc4c4711b352dac8008",
    },
    "early": {
        "path": RESULTS / "early-status-contract.tsv",
        "fields": ("id", "status_or_trigger", "publisher", "chronology",
                   "race_or_uncertainty", "closure", "terminal_result",
                   "forbidden"),
        "ids": ("P30K", "P30C", "P30P", "P30E", "P30U"),
        "sha256": "4ba7ea35c846be0c5c7ffc7f79be809318c275af46c3622c07ed7617d9877add",
    },
    "callbacks": {
        "path": RESULTS / "post-cpu-on-callbacks.tsv",
        "fields": ("id", "order_or_scope", "callback_set", "up_result",
                   "rollback_or_down_result", "selected_reachability",
                   "closure_effect"),
        "ids": tuple(f"H{i:02d}" for i in range(1, 16)),
        "sha256": "d697709a5c5f7800d521d75ab43c701e7e2c28f295a9f171798c02ce3fbb40a5",
    },
    "p32": {
        "path": RESULTS / "p30-p32-closure.tsv",
        "fields": ("id", "trigger", "publication_point", "guard_or_action",
                   "retained_state", "result_semantics", "recovery",
                   "forbidden"),
        "ids": ("P32A", "P32D", "P32F", "P32X", "P32R"),
        "sha256": "7d5b1830a750d6bfa54e756d78ff2846450f49014dc0d6ce476d28733ffb74fc",
    },
}

EXPECTED_SOURCE_HASHES = {
    "S01": SOURCE_SHA256,
    "S02": PATCHSET_SHA256,
    "S03": SOURCE_STATE_SHA256,
    "S04": PATCH_0092_SHA256,
    "S05": "3f34af99daddb6d30793d458aa504c66819506d1df936727af6fc5b8060ddc25",
    "S06": "1eb87f2754f7dd01393ef74429959dbc9fffa30b34dea6513045124c2ec8e031",
    "S07": "b665927a9c93713ee139311a354400cc9b9418e2c5651d81afe6c4868634adc4",
    "S08": "e6caf0bd4f63c52e570b28f089ec551eebccaf124087980a0d5d6ed156389c06",
    "S09": "db56887baf6cb87c24974609ffdb76ed5765a3756739c50a44384e384925977d",
    "S10": "b47ce91342071c78999a6db81a4d27366816ce01e05e3231137cd0ab980891d6",
    "S11": "634062ea1c0034439a07d48abafd03081ee81466d88658f80354b24f2acf9e4d",
    "S12": "685422537d348390bffde2d1f1fd443b82b113a54171f877749e64881663d58d",
    "S13": "bfcb84fea79dd339b708c7ff92ffb7594c1ca65a8abfab3152c86d79101ca056",
    "S14": "bcf0f0ac74a27fbf735893bb4b96cd8e35c55ef07b38f14ef47d5de1cc2be204",
    "S15": CONFIG_SHA256,
    "S16": "32aa83c01f6c3ea3e36d63e5154e007292e2bd840253ac1933b0240a1e6054e2",
    "S17": "1fa07344f9882b5039b983ec3a3cb25b4a94c17027bc2dc71db35c2b0ea5f5ac",
    "S18": "4efadfe25aa9c2641aa5512b14b0a7d766759d72e2674a3e5620627f6e730672",
    "S19": "123d80b2ad9c37b6e9b58296c217744747c87f483cfbc424a1f4695a64cb9728",
    "S20": "d188f7c92e0e6dddff5820173f8f8753ddef1387fadefac2c5f961423ee74515",
    "S21": "1d6e1ebbed42797517d89fc44213553242020df3c08faea400056711d5015f3e",
    "S22": "130ac3f7ab837cf31194a7683c92ad07b2f437528256aaf71e83283085f9d8c4",
    "S23": "bdeb0c45a1b2f08145b4ea26ead4c299b0f71e8628b3a94dffae7821e797b7dc",
    "S24": "a2c99295c3be92bf6cea468159978bce51af7055b5f38a5a3701106b02cf5684",
    "S25": "b58032c87866b4432a7e6978a34bff2209edbc9b32eb541444747a66646eec63",
    "S26": "5a6ddda12d1f1731a421e3e76d22f05e10fbb4aece4a294ccfdb333a7b4e9fa4",
    "S27": "dbc0096b5a47579f4dbf10709b7ef9a6f0a5dd13153852f54f6b5a10f35b9781",
    "S28": "2c374774812ad6f203090dd6d1a544eb0b1195fade8faa6d08ea2d6090f2a3db",
    "S29": "31c54830d52fb73d697ec851907835dfdbc5e0b2aa167744b7afb67d97894ad9",
    "S30": "0613e2f5d21a736e98fb993db17e8db5c8e050b813c59035fb5bd4a696dd7ead",
    "S31": "795e766c3bf6a0fc624d2d385885023f8cdc5ef33c718b28fbb9ed7124f701f4",
    "S32": "ed82d76521ae1c675c1916dac39e649ba167c4df180412dd175c4703582e528b",
    "S33": "109d101fd7abad24c9630d68c7d75a41983ac596e52374c80df404a9f9e07073",
    "S34": "322b86c4d8c73da8b99d0858919777d5b855178ce72b7ad623e398d94d69a7ad",
    "S35": "9704625cb5668c19313cb4eb79c20fd8f726b5d949d52fc5bfc3d47feb92852e",
    "S36": "f08896d71b530e32ec8e932b5906fd2265c9ca2a8054d1a42640e83858709c9a",
    "S37": "219be1efff8dd8f860d4ade221f2cbd61b541d921ea4bcb6796511ae023b72d2",
    "S38": "bcb28fbedd784a467e0a7b1f737692b04809ea977042caff73e09bccb9cc2c86",
    "S39": "7c59d4229cd6508f53fe98a77bfab8b85f1f756bba2420cd13bab7d7450888ea",
    "S40": "584182e70e42568d8bb9a44b15481c8732f0372bce810c462c94deebfc2613a5",
    "S41": "5b396ed9fec9056a7b5ec2f58c38f66b3f8116d1c105c962117d008f9eb111e2",
    "S42": "2240b1cc1b0f5b037284d51d8329aee10f107d21c0915f7c3e4ac1abf3f4c5b9",
    "S43": "70a358244087f051441cd74ea5c9062551ec447d1eed8617a6ba9a73d3ee474a",
    "S44": "1b19ffc958dcb53028e804a3d31d924ba113eb2805d8118b5d30970390980f1e",
    "S45": "916b6e0671bcb00013421693531de82f2f17df700417336d0c2818002dff430b",
    "S46": "42f358d199a615e62d8c66bda9321d629311303d7082bd6dd7ed0b1ca4263329",
    "S47": "128ab694b76f23c4e2e4715f9cac3703263df07ef96c0bf4ef9f8f9a75da95c4",
    "S48": "a96d522a62c14a3771ecdf2ef3717c56289ba0fa3831b6c89243e938f8e1f74b",
    "S49": "0dd3cc99a3803077dd765e859b31dee44959f48788b934b8556b3199def2979d",
    "S50": "a1d7f995a4c490295adbc2a6189f0be46b4aff529badfb89f07244e4c0b76e64",
    "S51": "2c26e67751f939dfb21ff6221884280ae84a2a94a54de4468fb9dc8746130d6d",
    "S52": "1b2e85b88162d9aae424afea2bfbdde73a88a0d990e74241815dc8800e4518e7",
    "S53": "f65165f6c487af3d04387b9a2184f1f0022cdfb8aa10909bae565db2754ea742",
    "S54": "fed9e169e0043b4ebc9d8fdcda54cf4bb0daa73c97928b850059085a383f7f74",
    "S55": "e0af3d4dce2dc2b2a64eb9c932b6c9e3a5fdb384cdfd60439cde8c17b5b5f4ae",
}

SOURCE_ROOT_FILES = {
    "S05": "arch/arm64/kernel/smp.c",
    "S06": "arch/arm64/kernel/cpufeature.c",
    "S07": "arch/arm64/kernel/cpu_errata.c",
    "S08": "arch/arm64/kernel/proton-pack.c",
    "S09": "arch/arm64/kernel/head.S",
    "S10": "arch/arm64/kernel/cpu_ops.c",
    "S11": "arch/arm64/kernel/psci.c",
    "S12": "kernel/cpu.c",
    "S13": "include/linux/cpuhotplug.h",
    "S18": "arch/arm64/include/asm/smp.h",
    "S19": "arch/arm64/mm/context.c",
    "S20": "arch/arm64/mm/mmu.c",
    "S21": "arch/arm64/tools/cpucaps",
    "S26": "io_uring/io-wq.c",
    "S27": "drivers/firmware/arm_sdei.c",
    "S28": "drivers/irqchip/irq-gic-v3.c",
    "S29": "arch/arm64/kernel/debug-monitors.c",
    "S30": "drivers/clocksource/arm_arch_timer.c",
    "S31": "drivers/clocksource/dummy_timer.c",
    "S32": "kernel/time/hrtimer.c",
    "S33": "kernel/sched/core.c",
    "S34": "kernel/smpboot.c",
    "S35": "kernel/irq/cpuhotplug.c",
    "S36": "block/blk-mq.c",
    "S37": "kernel/events/core.c",
    "S38": "kernel/time/timer_migration.c",
    "S39": "kernel/workqueue.c",
    "S40": "drivers/char/random.c",
    "S41": "kernel/rcu/tree.c",
    "S42": "kernel/kthread.c",
    "S43": "drivers/base/cacheinfo.c",
    "S44": "arch/arm64/kernel/cacheinfo.c",
    "S45": "mm/page-writeback.c",
    "S46": "mm/vmstat.c",
    "S47": "kernel/padata.c",
    "S48": "arch/arm64/kernel/topology.c",
    "S49": "drivers/base/topology.c",
    "S50": "arch/arm64/kernel/cpuinfo.c",
    "S51": "lib/percpu_counter.c",
    "S52": "drivers/leds/trigger/ledtrig-cpu.c",
    "S53": "kernel/printk/printk.c",
    "S54": "arch/arm64/kernel/paravirt.c",
    "S55": "drivers/irqchip/irq-gic-v3-its.c",
}

PREPARED_ROOT_FILES = {
    **{identifier: relative for identifier, relative in SOURCE_ROOT_FILES.items()
       if identifier != "S10"},
    "S14": "arch/arm64/kernel/mt6797_psci.c",
    "S22": "arch/arm64/kernel/cpu_ops.c",
    "S23": "arch/arm64/kernel/Makefile",
    "S24": "arch/arm64/boot/dts/mediatek/mt6797.dtsi",
    "S25": "Documentation/devicetree/bindings/arm/cpus.yaml",
}

CONFIG_ABSENT = "absent (n)"

EXPECTED_CONFIG = {
    "CONFIG_SMP": "y",
    "CONFIG_HOTPLUG_CPU": "y",
    "CONFIG_HOTPLUG_CORE_SYNC": "y",
    "CONFIG_HOTPLUG_CORE_SYNC_DEAD": "y",
    "CONFIG_HOTPLUG_CORE_SYNC_FULL": CONFIG_ABSENT,
    "CONFIG_PADATA": "y",
    "CONFIG_LEDS_TRIGGER_CPU": "y",
    "CONFIG_ARM_ARCH_TIMER": "y",
    "CONFIG_ARM64_ERRATUM_1742098": "y",
    "CONFIG_ARM64_WORKAROUND_SPECULATIVE_AT": "y",
    "CONFIG_ARM64_ERRATUM_1319367": "y",
    "CONFIG_ARM64_4K_PAGES": "y",
    "CONFIG_ARM64_VA_BITS_52": "y",
    "CONFIG_ARM64_LPA2": "y",
    "CONFIG_UNMAP_KERNEL_AT_EL0": "y",
    "CONFIG_MITIGATE_SPECTRE_BRANCH_HISTORY": "y",
    "CONFIG_COMPAT": "y",
    "CONFIG_RANDOMIZE_BASE": "n",
    "CONFIG_SUSPEND": "n",
    "CONFIG_CPU_IDLE": "n",
    "CONFIG_CPU_FREQ": "n",
    "CONFIG_VIRTUALIZATION": "n",
    "CONFIG_PERF_EVENTS": "n",
    "CONFIG_SOFTLOCKUP_DETECTOR": "n",
    "CONFIG_HARDLOCKUP_DETECTOR": "n",
    "CONFIG_IO_URING": "y",
    "CONFIG_ARM_SDE_INTERFACE": "y",
    "CONFIG_ARM64_SVE": "y",
    "CONFIG_ARM64_SME": "y",
    "CONFIG_ARM64_MPAM": "n",
    "CONFIG_ARM64_PSEUDO_NMI": "n",
    "CONFIG_ARM_GIC_V3": "y",
    "CONFIG_ARM64_PTR_AUTH": "y",
    "CONFIG_ARM64_PTR_AUTH_KERNEL": "y",
    "CONFIG_ARM64_MTE": "y",
    "CONFIG_ARM64_BTI": "y",
    "CONFIG_ARM64_RAS_EXTN": "y",
    "CONFIG_EFI": "n",
    "CONFIG_CMDLINE_FORCE": "y",
    "CONFIG_NO_HZ_COMMON": "y",
    "CONFIG_PARAVIRT": "y",
    "CONFIG_ARM_GIC_V3_ITS": "y",
    "CONFIG_BLOCK": "y",
    "CONFIG_IO_WQ": "y",
    "CONFIG_PRINTK": "y",
    "CONFIG_SYSFS": "y",
    "CONFIG_NUMA": "y",
}

# Every tuple is independently mutation-tested by test_contract.py.
SEMANTIC_TOKENS = (
    ("source", "S02", "observation", "all 136 ordered patch path and content hashes"),
    ("source", "S03", "observation", "No selected patch changes"),
    ("source", "S04", "observation", "returns -EAGAIN before CPU_ON"),
    ("source", "S04", "decision", "Keep the A26 boot veto closed"),
    ("source", "S05", "observation", "single global secondary_data and cpu_running completion"),
    ("source", "S06", "observation", "rejected through cpu_die_early"),
    ("source", "S08", "decision", "BHB state parameters and alternatives before finalization"),
    ("source", "S10", "observation", "Official archive input before canonical patch application"),
    ("source", "S11", "observation", "CPU_OFF and generic kill performs active affinity"),
    ("source", "S12", "decision", "P32 must publish before outer rollback"),
    ("source", "S20", "decision", "zero or inherited status"),
    ("source", "S21", "decision", "exhaustive required set"),
    ("source", "S22", "observation", "register mt6797_psci_ops"),
    ("source", "S26", "decision", "possible partial multi-instance prefix"),
    ("source", "S27", "observation", "conditionally registers a dynamic state"),
    ("source", "S45", "observation", "first mandatory dynamic ONLINE state"),
    ("source", "S47", "observation", "fallible multi-instance state after vmstat"),
    ("source", "S49", "observation", "after io-wq"),
    ("source", "S54", "decision", "same-boot registration proof"),
    ("source", "S55", "decision", "Selected EFI=n excludes it"),
    ("config", "C02", "closure_effect", "P32 automatic rollback is reachable after CPU_ON"),
    ("config", "C04", "closure_effect", "kill guards remain required"),
    ("config", "C05", "closure_effect", "ENOMEM"),
    ("config", "C08", "closure_effect", "suppress compat AES"),
    ("config", "C10", "closure_effect", "deterministic required capability"),
    ("config", "C12", "closure_effect", "boot alternatives actually selected 52-bit VA"),
    ("config", "C15", "closure_effect", "k=8"),
    ("config", "C16", "closure_effect", "COMPAT_HWCAP2_AES"),
    ("config", "C17", "closure_effect", "reopens the capability inventory"),
    ("config", "C21", "closure_effect", "Speculative-AT still remains"),
    ("config", "C25", "closure_effect", "even when no io-wq instance is live"),
    ("config", "C26", "closure_effect", "fallible up/down callbacks conditionally"),
    ("config", "C27", "closure_effect", "Dynamically absent is not configuration-excluded"),
    ("config", "C29", "closure_effect", "Dynamically absent is not configuration-excluded"),
    ("config", "C31", "closure_effect", "SRE-usability proof remains open"),
    ("config", "C37", "closure_effect", "insert and shift a state"),
    ("config", "C38", "reachability", "lacks allow_mismatched_32bit_el0"),
    ("config", "C39", "closure_effect", "EINVAL invariant path"),
    ("config", "C40", "reachability", "paravirtual-time CPUHP code is linked"),
    ("config", "C41", "closure_effect", "CONFIG_EFI=n is the selected exclusion"),
    ("config", "C42", "closure_effect", "block-MQ instance and rollback effects"),
    ("config", "C43", "closure_effect", "H07 always reserves its state"),
    ("config", "C44", "closure_effect", "final mandatory dynamic state"),
    ("config", "C45", "closure_effect", "errors remain reachable P32 triggers"),
    ("config", "C46", "closure_effect", "NUMA removal as a real selected effect"),
    ("config", "C47", "closure_effect", "full ALIVE and ONLINE synchronization waits are not selected"),
    ("capability", "K01", "required_side_effect", "max_bhb_k=8"),
    ("capability", "K01", "required_side_effect", "apply_alternatives_all"),
    ("capability", "K02", "required_side_effect", "COMPAT_HWCAP2_AES"),
    ("capability", "K03", "required_side_effect", "before alternatives finalization"),
    ("capability", "K04", "detection_basis", "SMCCC workaround-1"),
    ("capability", "K05", "detection_basis", "SMCCC workaround-2"),
    ("capability", "K06", "detection_basis", "CTR_EL0"),
    ("capability", "K07", "detection_basis", "CONFIG_RANDOMIZE_BASE=n"),
    ("capability", "K08", "failure", "P30P"),
    ("capability", "K09", "failure", "P30E"),
    ("capability", "K10", "required_side_effect", "do not equate VA_BITS_52=y"),
    ("capability", "K11", "required_side_effect", "setup_system_capabilities"),
    ("capability", "K11", "required_side_effect", "setup_user_features"),
    ("capability", "K12", "required_side_effect", "GICv3 CPU-interface usability"),
    ("capability", "K12", "required_side_effect", "dynamically absent A53-finalized SVE SME MPAM"),
    ("capability", "K12", "acceptance", "configuration-excluded"),
    ("capability", "K13", "required_side_effect", "all enable fixup parameter alternative vector and HWCAP effects"),
    ("capability", "K13", "acceptance", "K01-K12 closed"),
    ("capability", "K13", "failure", "no CPU_ON patch build candidate or device action"),
    ("early", "P30K", "publisher", "target ARMED-to-FAILING"),
    ("early", "P30K", "chronology", "refine the final branch to P30C"),
    ("early", "P30K", "closure", "PARKED acknowledgement carrying the final reason"),
    ("early", "P30K", "closure", "cpu_kill returns nonzero"),
    ("early", "P30C", "publisher", "target remains FAILING through final PARKED"),
    ("early", "P30C", "race_or_uncertainty", "bare-STUCK value alone proves neither generation nor park commitment"),
    ("early", "P30C", "closure", "K-to-C refinement records the bounded non-SMC guard"),
    ("early", "P30C", "closure", "missing or mismatched acknowledgement globally quarantines CPU-up"),
    ("early", "P30C", "terminal_result", "missing acknowledgement has no ordinary return"),
    ("early", "P30P", "closure", "stuck/kexec interlock"),
    ("early", "P30P", "closure", "FAILING to PANICKED"),
    ("early", "P30P", "terminal_result", "no normal return"),
    ("early", "P30E", "publisher", "assembly ARMED-to-FAILING reason and PARKED"),
    ("early", "P30E", "chronology", "MMU-off-visible memory"),
    ("early", "P30E", "chronology", "PoC cache and barrier ordering"),
    ("early", "P30E", "chronology", "same exact-target generation cookie and atomic state used by all arbitration"),
    ("early", "P30E", "chronology", "On CAS loss to CANCELLED or FAULTED"),
    ("early", "P30E", "chronology", "writes no reason or status"),
    ("early", "P30E", "closure", "Acquire and validate the same authoritative state target generation cookie reason FAILING ownership and PARKED"),
    ("early", "P30E", "closure", "routes P30U"),
    ("early", "P30E", "forbidden", "target ledger access"),
    ("early", "P30E", "forbidden", "second arbitration state"),
    ("early", "P30U", "publisher", "ARMED-to-CANCELLED"),
    ("early", "P30U", "publisher", "FAILING-to-PARKED"),
    ("early", "P30U", "closure", "ARMED to PUBLISHING immediately before the booted pr_info and first CPU_BOOT_SUCCESS write"),
    ("early", "P30U", "closure", "cancellation CAS only from ARMED to CANCELLED"),
    ("early", "P30U", "closure", "target-side no-fail violation latch wins ARMED to FAILING"),
    ("early", "P30U", "closure", "acquire-observing PUBLISHED consuming that completion"),
    ("early", "P30U", "closure", "even if online was already true"),
    ("early", "P30U", "closure", "exact possible MM RCU GIC cpuinfo topology STARTING IPI NUMA and other prepublication effect prefix"),
    ("early", "P30U", "closure", "stuck accounting and status side effects occur only after a terminal PARKED outcome"),
    ("early", "P30U", "terminal_result", "P13/A34 reset only"),
    ("early", "P30U", "terminal_result", "stalled publication or missing acknowledgement"),
    ("early", "P30U", "forbidden", "cancellation after PUBLISHING"),
    ("early", "P30U", "forbidden", "accepted partial publication"),
    ("callbacks", "H01", "up_result", "atomic no-fail"),
    ("callbacks", "H01", "callback_set", "scheduler then GICv3 then debug-monitor then arm-arch-timer then event-stream then dummy-timer then hrtimer"),
    ("callbacks", "H01", "closure_effect", "ARMED-to-FAILING before publication"),
    ("callbacks", "H01", "closure_effect", "not a P32 trigger"),
    ("callbacks", "H02", "callback_set", "booted pr_info then CPU_BOOT_SUCCESS then cpu_online then generation PUBLISHED then exact completion"),
    ("callbacks", "H02", "closure_effect", "consumes PUBLISHED plus exact completion"),
    ("callbacks", "H03", "callback_set", "AP_SCHED_WAIT_EMPTY marker has no startup callback then smpboot then irq-affinity then block-mq then selected perf stub"),
    ("callbacks", "H04", "up_result", "kthreads may ENOMEM or EINVAL"),
    ("callbacks", "H05", "up_result", "sysfs errors"),
    ("callbacks", "H06", "callback_set", "writeback then vmstat then padata multi-instance"),
    ("callbacks", "H06", "closure_effect", "numeric slots remain unclaimed"),
    ("callbacks", "H07", "callback_set", "arm64 topology then io-wq multi-instance then cpu-capacity"),
    ("callbacks", "H07", "closure_effect", "io-wq always reserves a state"),
    ("callbacks", "H08", "callback_set", "arm64 cpuinfo then percpu-counter then CPU LED then printk"),
    ("callbacks", "H09", "callback_set", "GICv3 ITS memreserve"),
    ("callbacks", "H09", "selected_reachability", "CONFIG_EFI=n"),
    ("callbacks", "H10", "selected_reachability", "same-boot absence is unproven"),
    ("callbacks", "H10", "closure_effect", "No absolute slot may be assigned"),
    ("callbacks", "H11", "order_or_scope", "after arm64 topology and before io-wq"),
    ("callbacks", "H11", "selected_reachability", "no arm,sdei-1.0 node"),
    ("callbacks", "H12", "order_or_scope", "after cpu-capacity and before cpuinfo"),
    ("callbacks", "H12", "selected_reachability", "lacks allow_mismatched_32bit_el0"),
    ("callbacks", "H13", "closure_effect", "A25 remains incomplete"),
    ("callbacks", "H13", "closure_effect", "no DYN+N identity is claimed"),
    ("callbacks", "H14", "rollback_or_down_result", "deadline-bandwidth deactivation error"),
    ("callbacks", "H15", "up_result", "original startup callback error"),
    ("callbacks", "H15", "closure_effect", "P32 side channel is mandatory"),
    ("p32", "P32A", "publication_point", "before cpuhp_reset_state"),
    ("p32", "P32A", "guard_or_action", "nested cpuhp_kick_ap rollback"),
    ("p32", "P32D", "publication_point", "before arch teardown effects"),
    ("p32", "P32D", "guard_or_action", "return error without topology NUMA online-mask IPI or IRQ mutation"),
    ("p32", "P32D", "recovery", "Fail-stop panic or reset"),
    ("p32", "P32F", "publication_point", "after DEAD"),
    ("p32", "P32F", "guard_or_action", "parks without CPU_OFF"),
    ("p32", "P32F", "guard_or_action", "no affinity and returns nonzero"),
    ("p32", "P32X", "retained_state", "Never infer clean rollback"),
    ("p32", "P32X", "recovery", "global CPU-up quarantine"),
    ("p32", "P32R", "publication_point", "before HPS or membership completion"),
    ("p32", "P32R", "result_semantics", "No generic return alone is success"),
    ("p32", "P32R", "forbidden", "provider release"),
)

EXPECTED_NEGATIVE_MUTATIONS = 441


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_tokens(text: str, tokens: Iterable[str], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} missing token: {token}")


def parse_tsv_text(text: str, fields: tuple[str, ...], label: str) -> list[dict[str, str]]:
    require("\r" not in text, f"{label}: CRLF is not canonical")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    require(reader.fieldnames == list(fields), f"{label}: schema changed")
    rows = list(reader)
    require(bool(rows), f"{label}: empty table")
    for index, row in enumerate(rows, start=2):
        require(None not in row, f"{label}:{index}: extra column")
        for field in fields:
            value = row.get(field)
            require(value is not None and value == value.strip() and value != "",
                    f"{label}:{index}: invalid {field}")
            require("\n" not in value and "\t" not in value,
                    f"{label}:{index}: control character in {field}")
            require(not any(private in value for private in
                            ("/Users/", "/private/tmp/", "/workspace/")),
                    f"{label}:{index}: private absolute path")
    return rows


def load_tables(check_identity: bool = True) -> dict[str, list[dict[str, str]]]:
    loaded: dict[str, list[dict[str, str]]] = {}
    for name, spec in TABLES.items():
        path = spec["path"]
        require(path.is_file() and not path.is_symlink(), f"missing table: {path.name}")
        raw = path.read_bytes()
        loaded[name] = validate_table_bytes(name, raw, check_identity)
    return loaded


def validate_table_bytes(name: str, raw: bytes, check_identity: bool = True) -> list[dict[str, str]]:
    require(name in TABLES, f"unknown table: {name}")
    spec = TABLES[name]
    if check_identity:
        require(hashlib.sha256(raw).hexdigest() == spec["sha256"],
                f"{name}: table identity changed")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{name}: table is not UTF-8") from error
    return parse_tsv_text(text, spec["fields"], name)


def index_rows(rows: list[dict[str, str]], expected_ids: tuple[str, ...],
               label: str) -> dict[str, dict[str, str]]:
    ids = tuple(row["id"] for row in rows)
    require(ids == expected_ids, f"{label}: row order or membership changed")
    require(len(set(ids)) == len(ids), f"{label}: duplicate id")
    return {row["id"]: row for row in rows}


def validate_tables(tables: dict[str, list[dict[str, str]]]) -> None:
    indexed = {
        name: index_rows(tables[name], TABLES[name]["ids"], name)
        for name in TABLES
    }

    for identifier, expected in EXPECTED_SOURCE_HASHES.items():
        require(indexed["source"][identifier]["sha256"] == expected,
                f"source/{identifier}: hash changed")

    config = indexed["config"]
    observed_config = {row["option"]: row["selected_value"] for row in config.values()}
    require(observed_config == EXPECTED_CONFIG, "selected configuration inventory changed")

    for table, identifier, field, token in SEMANTIC_TOKENS:
        require(token in indexed[table][identifier][field],
                f"{table}/{identifier}.{field} missing semantic token: {token}")

    deterministic = {"K01", "K02", "K03"}
    require(all("deterministic" in indexed["capability"][item]["detection_basis"]
                for item in deterministic), "deterministic capability set changed")
    require(all("A26" in indexed["capability"][item]["failure"]
                for item in ("K01", "K02", "K03", "K13")),
            "capability failure no longer keeps A26 closed")

    for identifier, row in indexed["early"].items():
        require("P30" in row["terminal_result"], f"{identifier}: not a P30 terminal")
        require("reset only" in row["terminal_result"],
                f"{identifier}: reset-only recovery lost")
        for token in ("CPU_OFF", "affinity", "query", "inverse", "retry",
                      "provider release", "membership commit"):
            require(token in row["forbidden"],
                    f"{identifier}: forbidden token lost: {token}")
    for identifier in ("P30K", "P30C", "P30E", "P30U"):
        require("PARKED" in indexed["early"][identifier]["closure"],
                f"{identifier}: exact park acknowledgement lost")
    for identifier in ("P30K", "P30C", "P30P", "P30E", "P30U"):
        require("FAILING" in indexed["early"][identifier]["publisher"],
                f"{identifier}: target failure ownership lost")
    require("no ordinary return" in indexed["early"]["P30C"]["terminal_result"],
            "P30C: missing acknowledgement can return")
    require("no ordinary return" in indexed["early"]["P30U"]["terminal_result"],
            "P30U: stalled publication can return")
    require("ARMED-to-CANCELLED" in indexed["early"]["P30U"]["publisher"],
            "P30U: controller cancellation ownership changed")

    for identifier, row in indexed["p32"].items():
        require("reset" in row["recovery"].lower(), f"{identifier}: reset-only lost")
        for token in ("CPU_OFF", "affinity", "query", "inverse", "retry",
                      "provider release", "membership commit", "HPS success",
                      "normal runtime continuation"):
            require(token in row["forbidden"],
                    f"{identifier}: forbidden token lost: {token}")

    require(indexed["callbacks"]["H15"]["selected_reachability"].endswith("=y"),
            "automatic rollback config guard changed")
    require("fallible" in indexed["callbacks"]["H04"]["closure_effect"],
            "fallible fixed callback classification changed")
    require("fallible" in indexed["callbacks"]["H05"]["closure_effect"],
            "cacheinfo fallibility changed")
    require(all("DYN+" not in indexed["callbacks"][identifier]["order_or_scope"]
                for identifier in ("H06", "H07", "H08", "H09", "H10", "H11", "H12")),
            "unsupported absolute dynamic slot claim")


def validate_evidence(source_root: Path | None = None,
                      prepared_source_root: Path | None = None,
                      config_path: Path | None = None) -> None:
    manifest_path = ROOT / "kernel/manifest.json"
    series_path = ROOT / "patches/series"
    patch_path = ROOT / PATCH_0092
    require(sha256(manifest_path) == MANIFEST_SHA256, "manifest identity changed")
    require(sha256(series_path) == SERIES_SHA256, "canonical series identity changed")
    require(sha256(patch_path) == PATCH_0092_SHA256, "patch 0092 identity changed")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    kernel = manifest.get("kernel", {})
    require(kernel.get("version") == "7.1.3", "manifest version changed")
    require(kernel.get("source_url") ==
            "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz",
            "manifest source URL changed")
    require(kernel.get("sha256") == SOURCE_SHA256, "manifest source hash changed")

    validate_patchset()
    validate_source_state()
    validate_official_file_composition()

    series_entries = [line.strip() for line in series_path.read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.lstrip().startswith("#")]
    require("v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch" in series_entries,
            "patch 0092 left canonical series")
    require(not any("0093" in entry or "0111" in entry for entry in series_entries),
            "rejected experimental A72 patch entered canonical series")

    patch = patch_path.read_text(encoding="utf-8")
    require_tokens(patch, ("static int mt6797_psci_cpu_boot", "return -EAGAIN;",
                           ".cpu_boot", ".cpu_can_disable"), "patch 0092")
    require("+\t.cpu_disable" not in patch and "+\t.cpu_die" not in patch and
            "+\t.cpu_kill" not in patch, "patch 0092 unexpectedly adds off callbacks")

    if source_root is not None:
        validate_source_root(source_root)
    if prepared_source_root is not None:
        validate_prepared_source_root(prepared_source_root)
    if config_path is not None:
        validate_config(config_path)


def computed_source_state(version: str = "7.1.3",
                          source_sha: str = SOURCE_SHA256,
                          patchset_sha: str = PATCHSET_SHA256) -> str:
    payload = f"{version}\n{source_sha}\n{patchset_sha}\n".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_source_state(version: str = "7.1.3",
                          source_sha: str = SOURCE_SHA256,
                          patchset_sha: str = PATCHSET_SHA256) -> None:
    require(computed_source_state(version, source_sha, patchset_sha) ==
            SOURCE_STATE_SHA256, "prepared source-state identity changed")


def canonical_patchset_hash(overrides: dict[str, bytes] | None = None) -> tuple[str, int]:
    overrides = {} if overrides is None else overrides
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    relative_series = manifest.get("patch_series")
    require(relative_series == "patches/series", "top-level patch series changed")
    series = ROOT / relative_series
    require(series.is_file() and not series.is_symlink(), "unsafe canonical series")
    series_bytes = overrides.get(relative_series, series.read_bytes())
    digest_lines = [f"{hashlib.sha256(series_bytes).hexdigest()}  {relative_series}\n"]
    entries = []
    for line_number, line in enumerate(series_bytes.decode("utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        require(line == line.strip() and not any(char.isspace() for char in line),
                f"unsafe series entry at line {line_number}")
        require(not line.startswith("/") and "//" not in line and
                "/../" not in f"/{line}/" and "/./" not in f"/{line}/",
                f"series path escapes patches: {line}")
        patch = series.parent / line
        require(patch.is_file() and not patch.is_symlink(), f"unsafe listed patch: {line}")
        resolved = patch.resolve(strict=True)
        try:
            resolved.relative_to(series.parent.resolve(strict=True))
        except ValueError as error:
            raise ContractError(f"listed patch escapes patches: {line}") from error
        relative_patch = f"patches/{line}"
        data = overrides.get(relative_patch, patch.read_bytes())
        digest_lines.append(f"{hashlib.sha256(data).hexdigest()}  {line}\n")
        entries.append(relative_patch)
    unknown = set(overrides) - {relative_series, *entries}
    if unknown:
        raise ContractError(f"unknown patchset override: {sorted(unknown)[0]}")
    return hashlib.sha256("".join(digest_lines).encode("utf-8")).hexdigest(), len(entries)


def validate_patchset(overrides: dict[str, bytes] | None = None) -> None:
    observed, count = canonical_patchset_hash(overrides)
    require(count == 136, "canonical patch count changed")
    require(observed == PATCHSET_SHA256, "canonical patchset content identity changed")


def validate_official_file_composition(modified_override: set[str] | None = None) -> None:
    if modified_override is None:
        series = ROOT / "patches/series"
        entries = [line for line in series.read_text(encoding="utf-8").splitlines()
                   if line and not line.startswith("#")]
        audited = set(SOURCE_ROOT_FILES.values())
        modified: set[str] = set()
        for entry in entries:
            text = (series.parent / entry).read_text(encoding="utf-8")
            for relative in audited:
                if f"+++ b/{relative}\n" in text:
                    modified.add(relative)
    else:
        modified = set(modified_override)
    require(modified == {"arch/arm64/kernel/cpu_ops.c"},
            "audited official/prepared file composition changed")


def validate_root_files(source_root: Path, files: dict[str, str], label: str) -> Path:
    require(source_root.is_absolute(), f"{label} root must be absolute")
    require(source_root.is_dir() and not source_root.is_symlink(), f"invalid {label} root")
    root = source_root.resolve(strict=True)
    for identifier, relative in files.items():
        candidate = root / relative
        require(candidate.is_file() and not candidate.is_symlink(),
                f"{label} root missing regular file: {relative}")
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ContractError(f"{label} path escapes root: {relative}") from error
        require(sha256(resolved) == EXPECTED_SOURCE_HASHES[identifier],
                f"{label} hash changed: {relative}")
    return root


def validate_source_root(source_root: Path) -> None:
    validate_root_files(source_root, SOURCE_ROOT_FILES, "source")


def validate_prepared_source_root(source_root: Path) -> None:
    root = validate_root_files(source_root, PREPARED_ROOT_FILES, "prepared source")
    marker = root / ".gemini-source-state"
    require(marker.is_file() and not marker.is_symlink(),
            "prepared source marker missing or unsafe")
    require(marker.read_text(encoding="utf-8") == SOURCE_STATE_SHA256 + "\n",
            "prepared source marker identity changed")


def parse_config(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            name, value = line.split("=", 1)
            values[name] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2:-11]] = "n"
    return values


def validate_config(config_path: Path) -> None:
    require(config_path.is_absolute(), "config path must be absolute")
    require(config_path.is_file() and not config_path.is_symlink(), "invalid config path")
    require(sha256(config_path) == CONFIG_SHA256, "selected config identity changed")
    values = parse_config(config_path.read_text(encoding="utf-8"))
    for option, expected in EXPECTED_CONFIG.items():
        if expected == CONFIG_ABSENT:
            require(option not in values, f"selected config changed: {option}")
        else:
            require(values.get(option) == expected,
                    f"selected config changed: {option}")
    require("allow_mismatched_32bit_el0" not in values.get("CONFIG_CMDLINE", ""),
            "selected command line enables mismatched 32-bit EL0")


MARKERS = (
    "implementation_authorized=no",
    "cpu_on_authorized=no",
    "cpu_off_authorized=no",
    "build_authorized=no",
    "device_action_authorized=no",
    "device_action=none",
    "current_cpu_boot_veto=REQUIRED",
)

FORBIDDEN_AUTHORIZATION_PROSE = (
    "implementation is authorized",
    "cpu_on is authorized",
    "cpu_off is authorized",
    "kernel build is authorized",
    "building a kernel is authorized",
    "device action is authorized",
)

MEMBERSHIP_README_TOKENS = (
    "../2026-08-05-a72-cpu-up-source-closure/README.md",
    "current design authority for implementation review of A41",
    "chronological inputs rather than a sufficient implementation design",
    "P30K/C/P/E/U",
    "P32A/D/F/X/R",
    "Exact `.cpu_disable` is the primary target guard",
    "P14/P15 must be published immediately after successful `__cpu_up()`",
    "neither document",
    "authorizes a build or device action",
)

MEMBERSHIP_DESIGN_TOKENS = (
    "../2026-08-05-a72-cpu-up-source-closure/DESIGN.md",
    "supersedes this design's detailed A37/A39 implementation mechanism",
    "preserving P30 and P32 as the only phase edges",
    "P30K/C/P/E/U",
    "post-C bare-STUCK branch",
    "P32A/D/F/X/R",
    "`.cpu_disable` the first guard before topology/NUMA",
    "`.cpu_die` and controller `.cpu_kill` remain mandatory defense",
    "P14/P15 publication moves",
    "phase, membership/provider, admission, and reset-only ownership frozen here",
)


def validate_documents(readme: str | None = None, design: str | None = None,
                       membership_readme: str | None = None,
                       membership_design: str | None = None,
                       experiment_index: str | None = None,
                       roadmap: str | None = None) -> None:
    readme = README.read_text(encoding="utf-8") if readme is None else readme
    design = DESIGN.read_text(encoding="utf-8") if design is None else design
    membership_readme_path = ROOT / "experiments/2026-08-05-a72-membership-admission-contract/README.md"
    membership_design_path = ROOT / "experiments/2026-08-05-a72-membership-admission-contract/DESIGN.md"
    membership_readme = (membership_readme_path.read_text(encoding="utf-8")
                         if membership_readme is None else membership_readme)
    membership_design = (membership_design_path.read_text(encoding="utf-8")
                         if membership_design is None else membership_design)
    experiment_index = ((ROOT / "experiments/README.md").read_text(encoding="utf-8")
                        if experiment_index is None else experiment_index)
    roadmap = ((ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
               if roadmap is None else roadmap)

    for label, text in (("README", readme), ("DESIGN", design)):
        for marker in MARKERS:
            require(text.count(marker) == 1, f"{label}: marker count changed: {marker}")
        require(not any(bad in text for bad in
                        ("implementation_authorized=yes", "cpu_on_authorized=yes",
                         "cpu_off_authorized=yes", "build_authorized=yes",
                         "device_action_authorized=yes")),
                f"{label}: authorization enabled")
        lowered = text.lower()
        require(not any(phrase in lowered for phrase in FORBIDDEN_AUTHORIZATION_PROSE),
                f"{label}: contradictory authorization prose")
        require(not any(ordering in text for ordering in
                        ("The next implementation milestone", "The next ordered work",
                         "The next ordered action", "Next, implement")),
                f"{label}: duplicates ROADMAP ordering")

    require_tokens(readme, (
        "completed-blocking-contract", SOURCE_SHA256, PATCHSET_SHA256,
        SOURCE_STATE_SHA256, CONFIG_SHA256, "A41", "P30K/C/P/E/U",
        "P32A/D/F/X/R", "No kernel was built", "no runtime claim",
        "A26 CPU-up veto remains required",
    ), "README")
    require_tokens(design, (
        "current design authority for implementation review", "P30 and P32 remain the only phase transitions",
        "setup_system_capabilities()", "apply_alternatives_all()",
        "COMPAT_HWCAP2_AES", "P14/P15 publication point",
        "PREPARED", "ABORTED", "ARMED->PUBLISHING", "ARMED -> FAILING",
        "ARMED -> FAULTED",
        "cancellation-versus-publication", "P32D: primary `.cpu_disable` guard",
        "No generic return alone", "A25 completion requirement",
        "same-boot hotplug-state", "Absolute `DYN+N` identities are deliberately not claimed",
    ), "DESIGN")

    correction = "Source-closure correction (2026-08-05)"
    require(correction in membership_readme, "membership README lacks source-closure correction")
    require(correction in membership_design, "membership DESIGN lacks source-closure correction")
    require_tokens(membership_readme, MEMBERSHIP_README_TOKENS,
                   "membership README correction")
    require_tokens(membership_design, MEMBERSHIP_DESIGN_TOKENS,
                   "membership DESIGN correction")
    readme_notice = membership_readme.find("Current mechanism notice")
    design_notice = membership_design.find("Current mechanism notice")
    require(0 <= readme_notice < membership_readme.find("## Question or hypothesis"),
            "membership README current-authority notice is not near the top")
    require(0 <= design_notice < membership_design.find("## Separate ledgers and identities"),
            "membership DESIGN current-authority notice is not near the top")
    require("2026-08-05-a72-cpu-up-source-closure" in experiment_index,
            "experiment index lacks source-closure entry")
    require_tokens(roadmap, ("A72 CPU-up source closure", "A41", "P30K/C/P/E/U",
                             "P32A/D/F/X/R", "source-only implementation"),
                   "ROADMAP")
    roadmap_order = (
        "1. Implement and mutation-test A41's pre-finalization profile owner",
        "2. Implement and mutation-test P30K/C/P/E/U",
        "3. Complete A25 and implement P32A/D/F/X/R",
        "4. Revalidate every applicable A26 CPU-up gate",
        "5. Close the M02 delayed-work scheduler/observer owner",
        "then close A40 private-ledger writer/caller freshness",
        "6. Only after those CPU-up and branch-selection gates pass",
        "A14 off-completion owner",
    )
    positions = [roadmap.find(marker) for marker in roadmap_order]
    require(all(position >= 0 for position in positions), "ROADMAP ordered block changed")
    require(positions == sorted(positions) and len(set(positions)) == len(positions),
            "ROADMAP source work reordered")
    require_tokens(roadmap, (
        "must keep the current CPU boot veto",
        "passing source tests alone does not\n   authorize a build",
        "do not generate a CPU_ON/CPU_OFF\ncandidate, build a kernel, or use the device",
    ), "ROADMAP safety boundary")


def validation_report(tables: dict[str, list[dict[str, str]]]) -> list[str]:
    return [
        "experiment=2026-08-05-a72-cpu-up-source-closure",
        f"source_rows={len(tables['source'])}",
        f"config_rows={len(tables['config'])}",
        f"capability_rows={len(tables['capability'])}",
        f"early_status_rows={len(tables['early'])}",
        f"cpuhp_rows={len(tables['callbacks'])}",
        f"p32_rows={len(tables['p32'])}",
        f"source_sha256={SOURCE_SHA256}",
        f"patchset_sha256={PATCHSET_SHA256}",
        f"source_state_sha256={SOURCE_STATE_SHA256}",
        f"config_sha256={CONFIG_SHA256}",
        "deterministic_late_capabilities=3",
        "p30_branches=5",
        "p32_branches=5",
        "implementation=BLOCKED",
        "implementation_authorized=no",
        "cpu_on_authorized=no",
        "cpu_off_authorized=no",
        "build_authorized=no",
        "device_action_authorized=no",
        "device_action=none",
        "current_cpu_boot_veto=REQUIRED",
        "result=pass",
    ]


def mutation_report() -> list[str]:
    return [
        f"negative_mutations={EXPECTED_NEGATIVE_MUTATIONS}",
        "mutation_result=pass",
    ]


def validate_authorization(report: list[str]) -> None:
    pairs: dict[str, str] = {}
    for line in report:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        require(key not in pairs, f"duplicate report key: {key}")
        pairs[key] = value
    expected = {
        "implementation": "BLOCKED",
        "implementation_authorized": "no",
        "cpu_on_authorized": "no",
        "cpu_off_authorized": "no",
        "build_authorized": "no",
        "device_action_authorized": "no",
        "device_action": "none",
        "current_cpu_boot_veto": "REQUIRED",
        "result": "pass",
    }
    for key, value in expected.items():
        require(pairs.get(key) == value, f"unsafe report value: {key}")


def expected_transcript(report: list[str]) -> str:
    return "\n".join(report + mutation_report()) + "\n"


def validate_transcript(report: list[str], transcript: str | None = None) -> None:
    transcript = TRANSCRIPT.read_text(encoding="utf-8") if transcript is None else transcript
    require(transcript == expected_transcript(report), "frozen transcript is stale")


def validate_optional_transcript(transcript: str | None = None) -> None:
    transcript = (OPTIONAL_TRANSCRIPT.read_text(encoding="utf-8")
                  if transcript is None else transcript)
    expected = "\n".join((
        "experiment=2026-08-05-a72-cpu-up-source-closure",
        "official_source_root_recheck=pass",
        "official_source_file_hashes=43",
        "selected_config_recheck=pass",
        "selected_config_values=47",
        "forced_cmdline_mismatched_32bit_el0=absent",
        "official_source_corruption=reject",
        "selected_config_corruption=reject",
        f"base_negative_mutations={EXPECTED_NEGATIVE_MUTATIONS}",
        "optional_evidence_mutations=2",
        "prepared_source_root_recheck=not_run",
        "result=pass",
        "",
    ))
    require(transcript == expected, "optional evidence transcript is stale")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path,
                        help="optional absolute expanded official Linux 7.1.3 source root")
    parser.add_argument("--prepared-source-root", type=Path,
                        help="optional absolute managed canonical prepared source root")
    parser.add_argument("--config", type=Path,
                        help="optional absolute retained kernel.config to recheck")
    parser.add_argument("--report-only", action="store_true",
                        help="print the expected transcript without checking its frozen copy")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    tables = load_tables()
    validate_tables(tables)
    validate_evidence(args.source_root, args.prepared_source_root, args.config)
    validate_documents()
    report = validation_report(tables)
    validate_authorization(report)
    if args.report_only:
        print(expected_transcript(report), end="")
    else:
        validate_transcript(report)
        validate_optional_transcript()
        print("\n".join(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
