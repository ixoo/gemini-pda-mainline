# Guard the active TOPRGU subsystem-reset setter

The 53-patch [linked kernel](results/recovery-request-link.json) uses the
MT6797 watchdog implementation at the exact [source hash](results/recovery-subsystem-sources.json).
The source and configuration identify `mtk_wdt_swsysret_config()` as a
remaining active writer of TOPRGU `SWSYSRST` at offset `0x18`. Its CONSYS
caller asserts and deasserts the CONMCU reset bit during native connectivity
power transitions. Other in-tree call sites appear in watchdog, modem, GPU and
PSCI code. The setter already takes `rgu_reg_operation_spinlock`, but did not
check recovery ownership before reading and writing the register. A caller
waiting for the lock could therefore change subsystem reset state after timed
capture claims it. This is a pinned source finding, not an observed PDA race.

The [experiment patch](patches/recovery-subsystem/0001-watchdog-refuse-subsystem-reset-after-capture.patch)
checks ownership under the existing lock and returns `-EBUSY` before the
first register read. It preserves the original pre-takeover branch. Exact
patch replay and reversal pass. The [focused fixture](test-recovery-subsystem.py)
compiles the complete native setter in parent and child states, with the
experiment configuration both enabled and disabled. For each state it checks
six bit/set/order combinations, including a caller paused before acquiring
the lock. The child refuses after takeover without a register read or write;
pre-takeover and configuration-disabled calls retain the original write.
Strict Linux 7.1.3 Checkpatch reports zero findings except the intentionally
ignored synthetic sign-off requirement. The patch is the 54th
[compile-only input](full-kernel-inputs.json). The
[complete native Buildbox link](results/recovery-subsystem-link.json) passes
with an unchanged configuration and no unresolved symbols. In the linked
setter, the ownership branch unlocks and returns `-EBUSY` before the first
`SWSYSRST` read. The inherited build still reports 69 section mismatches.
This result is not a boot candidate or upstream submission.

## Request-route writer boundary

The same pinned source defines request-mode, request-IRQ and external-request
registers at TOPRGU offsets `0x30`, `0x34` and `0x38`. In the selected MT6797
watchdog file, the two [guarded setters](RECOVERY_REQUEST.md) are the active
request writers. The other direct writes sit under `CONFIG_KICK_SPM_WDT`,
which is absent from the verified configuration and has no definition in the
inspected source tree. `CONFIG_MTK_WATCHDOG_COMMON` and
`CONFIG_MEDIATEK_WATCHDOG` are also unselected; the build log compiles the
MT6797 watchdog object. The in-tree watchdog API and probe calls reach the
guarded setters. An exact physical-address source search found no literal
`0x10007030`, `0x10007034` or `0x10007038` writer. This is a bounded
source/configuration audit, not proof against computed aliases, firmware or
hardware agents.

## Remaining reset and resource ownership

The linked `mtk_wdt_set_c2k_sysrst()` also writes `SWSYSRST` without the
register lock. A whole-tree source-name search found only its MT6797
definition, dummy definition, a declaration with a different signature and
two messages inside the function. It found no caller or symbol export. The
exact configuration disables modules, so this entry is excluded from the
selected in-tree call graph; the linked symbol alone does not make it active.
This is a candidate-specific source/configuration exclusion, not a general
guard or a claim about future callers. The non-DT direct CONSYS writes are
excluded by `CONFIG_OF=y`, but other direct aliases and higher-level reset
paths need their own audit. This patch does not stop a worker that ignores
`-EBUSY`, prove shared CONSYS/EMI/AP-DMA ownership, or establish that the
12-second recovery budget is enough for the intended observation. No new
physical Wi-Fi test follows from it.
