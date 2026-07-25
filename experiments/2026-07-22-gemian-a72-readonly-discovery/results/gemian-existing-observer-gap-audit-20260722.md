# Existing Gemian A72 observer gap audit

Date: 2026-07-22

Decision: the unmodified Gemian 3.18 interfaces support a bounded partial
discovery capture, but they cannot satisfy the A72 firmware/power prerequisite
contract. The partial collector must not be treated as implementation-ready
evidence.

## Scope and method

This is an offline source audit of public Gemian kernel commit
`d388d350cb2dda8f23b99be6fa5db9628896e87f`. The audit searched the MediaTek
DA9214, iDVFS, CPUHVFS, cpufreq, clock manager, DCM, SPM, PSCI and watchdog
implementations for existing procfs, sysfs, debugfs and log callbacks. It then
followed every candidate read callback far enough to classify side effects and
the provenance of the returned value.

No device was contacted. Presence on the running unit remains a live-discovery
question. A previously retained same-image configuration has SHA-256
`231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`;
it reports `CONFIG_COMMON_CLK_MEDIATEK=y`,
`CONFIG_COMMON_CLK_MEDIATEK_V1=y`, and `# CONFIG_MTK_CLKMGR is not set`.

Classifications used below:

- **include**: the audited read callback does not intentionally change device
  configuration and returns useful partial evidence;
- **metadata only**: record node presence/mode without opening its callback;
- **exclude**: reading the node changes cached/device state, the value is only
  a stale selector cache, can enter the secure monitor outside this
  collector's exact no-SMC boundary, or the node offers dangerous writes with
  no useful read result;
- **gap**: no existing safe content interface was found.

## Prerequisite coverage matrix

| Required observation | Existing surface and audited behavior | Classification | What the scaffold does |
| --- | --- | --- | --- |
| DA9214 current page | No direct surface. `da9214_access` show returns only `g_reg_value_da9214`; selecting any register requires its store callback, which selects page 0/1 or 2/3, performs the access, and restores page 0/1 (`da9214.c:536-611`). | gap; `da9214_access` metadata only | Does not open the attribute. |
| DA9214 BUCKB enable `0x5e[0]` | No fixed-address show callback. `cpu_power_on_buck()` reads it internally but exports only AEE bookkeeping, not a synchronized current value. `dvt_test` does not report it. | gap | No value collected. |
| DA9214 BUCKB VSEL `0xd9[6:0]` | `/proc/idvfs/idvfs_debug` defaults its selector to `0xd9` and calls `da9214_read_interface(..., 0xff, 0)` (`mt_idvfs.c:67,1488-1495`). The DA9214 byte read is serialized by `da9214_i2c_access` (`da9214.c:130-164` or `206-242`). However, `dvt_test` write case 11 can change the global selector, the show ignores read failure, and no page value brackets the read. | include, partial only | Reads verbatim once per sample and marks it usable only when the callback itself reports `I2C_reg[0xd9]`; still labels the page unobserved. |
| SPM `0x10006218` and `0x10006290` | References are internal power-sequence accesses. No exact procfs/sysfs/debugfs show was found in the audited SPM and power code. | gap | No value collected. |
| TOPRGU `SWSYSRST[11]` | The watchdog driver owns a locked keyed RMW at offset `0x18` and reads the word internally (`mt_wdt.h:26,85-87`; `mtk_wdt.c:398-455`). It exports no exact read-only state callback. | gap | No value collected. |
| Eleven secure words in `0x102222b0..0x102224cc` | No generic read-only user interface for SMC `0xc200035f` exists. `dvt_test` reads only a subset such as `0x10222470`, `0x102224c8`, and SRAM values (`mt_idvfs.c:1597-1625`), not the required set. | gap; `dvt_test` excluded | Does not invoke an SMC or open `dvt_test`. No collected content callback enters the secure monitor. |
| Protected B PLL/mux/divider | B `/proc/cpufreq/.../cpufreq_freq` calls `idvfs_get_cur_phy_freq_b()`, which returns the cached OPP-table value (`mt_cpufreq.c:2827-2830,6122-6128`). It is not raw PLL, mux, divider, or semaphore-protected transaction state. | include only as reported rate | Samples the value with an explicit cached/non-raw label. |
| Protected CCI PLL/mux/divider/rate | CCI `cpufreq_freq` reads PLL CON1 and `ARMPLLDIV_CKDIV` and derives a rate (`mt_cpufreq.c:2864-2905,6122-6128`). The proc show calls the operation without the cpufreq software lock and without DVFSP semaphore 3, and it does not expose raw mux/divider fields. | include only as non-transactional reported rate | Samples the derived rate with an explicit no-DVFSP-semaphore label. |
| B voltage context | B `cpufreq_volt` holds the cpufreq software lock and calls the selected voltage/SRAM getters (`mt_cpufreq.c:6198-6214`). When CPU8/9 are online, that path can conditionally call fixed read-only SMC `0x8200035f`; other states can return firmware/current or fallback values. None is page-qualified DA9214 `0xd9` plus `0x5e` proof. | exclude from the no-SMC collector; metadata only | Records node metadata and a content-read tripwire. It never opens the callback. |
| MP2 DCM `0x10222274` | `/sys/power/dcm_state` has code to print `MCUCFG_SYNC_DCM_MP2_CONFIG`, but it is compiled only under `NON_AO_MP2_DCM_CONFIG` (`mt_dcm.c:1642-1645`). That macro is commented out (`mt_dcm.c:33`); the kernel-log dump is gated identically (`mt_dcm.c:1581-1583`). | gap; `dcm_state` metadata only | Does not open `dcm_state`. |
| B/CCI clock-manager diagnostic | `armbpll_fsel_read()` and `armccipll_fsel_read()` return no content (`mt_clkmgr.c:689-706`), although their proc nodes have state-changing write handlers. The saved configuration also selects common-clk rather than `CONFIG_MTK_CLKMGR`. | exclude/irrelevant; metadata only | Does not open either node. |
| CPUHVFS register context | `/sys/kernel/debug/cpuhvfs/dvfsp_reg` is mode 0444. Its complete show callback consists of `seq_*` output, `cspm_read(...)` calls, and one read of `dvfsp->hw_gov_en`, then returns zero (`mt_cpufreq_hybrid.c:2040-2089`); it contains no `cspm_write`, assignment to device/repository state, SMC, or control call. It does not include the required secure, SPM, TOPRGU, B/CCI mux/divider, or MP2 DCM words. | include as confirmed non-mutating context only | Dumps once if debugfs is already mounted; never mounts it. |
| CPUHVFS debug repository | `dbg_repo` is mode 0444, but its show writes three current latch values into the live repository before printing (`mt_cpufreq_hybrid.c:2092-2114`). Mode bits therefore do not make the callback observationally inert. | exclude; metadata only | Does not open it. |
| Existing transition timing/logs | `dmesg` has coarse PSCI, CPU8/9, HPS, iDVFS, DA9214, clock and DCM messages. It does not guarantee every required boundary or exact values. Function tracing would require trace-control writes and would alter this experiment's policy boundary. | include filtered dmesg; trace gap | Reads and filters the existing ring buffer after sampling; does not enable tracing. |

## Why `/proc/idvfs/dvt_test` is not a read-only observer

The mode and VFS operation are misleading. Its show callback calls
`BigiDVFSSWAvgStatus()` before it checks whether CPUs 8 and 9 are offline
(`mt_idvfs.c:1516-1567`); that status path updates cached frequency state. If
the B cluster is online, the same callback may invoke `BigOCPCapture()` and
updates OCP/OTP channel percentages under the iDVFS lock
(`mt_idvfs.c:1569-1595`). Only afterward does it issue a few secure reads and
DA9214/SRAM reads (`mt_idvfs.c:1597-1625`).

Thus `cat /proc/idvfs/dvt_test` is not observationally inert. It is excluded
even though some of its printed fields look relevant. Its write callback also
contains PLL, iDVFS, PMIC, secure-write, probe and deliberate `BUG_ON`
operations; no collector should use it as a register selector.

## Why `da9214_access` cannot fill the page/enable gap

The sysfs show callback prints a single cached byte. The store callback is what
parses an address, selects a page, performs the I2C transaction, updates the
cache, and restores page 0/1. Reading the cached byte without a preceding store
does not identify its register or sampling time. Performing the store would
violate this experiment's no-write contract and could race ownership despite
the per-byte I2C lock.

The fixed `idvfs_debug` callback is narrower and therefore acceptable for
discovery, but it still cannot prove the page. Its result must be rejected when
the printed selector is not exactly `0xd9`, and even a matching selector is only
an address read under the current unobserved page map.

## Collector evidence boundary

Before opening any vendor callback, the production probe requires exact Gemian
`3.18.41+`, `aarch64`, `findmnt -n -o SOURCE /` output
`/dev/mmcblk0p29`, an independent `/proc/mounts` root source of `rootfs`,
possible/present masks `0-9`, a stable UUID-form boot ID, stable AC/USB
external power, and a battery that is present, `Full`, 100%, and `Good`. Both
root representations fail closed on absence, read failure, or mismatch. The
fixture supplies both values directly and never invokes host `findmnt`. The
host wrapper fixes the known target and
repository key, requires strict existing-host-key validation, constrains output
to the Git-ignored mode-0700 private runtime-capture root, and preserves failed
mode-0600 partial evidence. It configures 5-second server-alive probes with a
three-miss limit and applies a monotonic hard wall bound equal to inter-sample
sleep time plus 60 seconds. Its helper kills only the exact unreaped SSH child
on timeout and propagates all other child statuses.

The safe CPUHVFS context dump and every vendor sample are bracketed by exact
unchanged healthy-power reads. Power drift/unhealthy state and every observable
exact `read-failed` fail immediately, with a sanitized `failure=` marker in the
preserved stdout partial. Required uptime and online-mask bracket reads also
fail if absent; optional safe vendor surfaces may be absent. The vendor
sampling contract explicitly ends after a final stable-power gate and before
filtered dmesg and boot-ID finalization. The scaffold has no independent
thermal stop surface, and `idvfs_debug` hides its DA9214 driver return status,
so it makes no I2C-error detection claim.

The scaffold records:

1. redacted command line, kernel/root/boot identity, CPU masks, monotonic uptime
   and power/battery state;
2. one safe CPUHVFS register-context dump when already available;
3. metadata, never contents, for explicitly excluded nodes;
4. 180 default one-second natural samples of online-mask brackets, DA9214
   `idvfs_debug`, B reported rate, CCI reported rate and before/after power
   state;
5. filtered existing kernel messages.

The B `cpufreq_volt` node is item 3, not item 4. This makes the collector's
no-SMC claim exact: none of its opened content callbacks invokes an SMC.

Every sample is sequential userspace I/O. `changed-torn` means the online mask
changed inside the bracket. `stable-nonatomic` means only that the two mask
strings match; voltage, clock, rail or firmware state may still have changed
between reads. The SSH session and repeated proc/I2C reads also add some load,
so natural means no requested workload or policy transition, not zero observer
effect.

The scaffold cannot establish any of the following:

- BUCKB page, enable ownership, or a synchronized `0x5e`/`0xd9` pair;
- B voltage/SRAM context from the excluded `cpufreq_volt` callback;
- exact pre/post SPM, TOPRGU or secure-register state;
- the DVFSP semaphore-protected raw B/CCI mux/divider snapshot;
- MP2 DCM state;
- 240-us boundary timing, PSCI return ordering, or an inverse power sequence.

It therefore cannot authorize an A72 power-provider patch, CPU8 request, CPU9
request, hotplug-off implementation, or rollback.

## Minimum missing observer

A complete natural-transition capture needs a separate, reviewed in-kernel
observer rather than a more privileged shell script:

- add an owning-DA9214 snapshot operation that holds the driver's mutex across
  page-selector, `0x5e`, and `0xd9` reads; fail closed rather than change the
  page when the expected page is not already selected;
- expose SPM `0x218`/`0x290` through the existing SPM owner and TOPRGU bit 11
  through the watchdog/reset owner, using their synchronization domains;
- invoke only secure `REG_READ` (`0xc200035f`) for the required whitelist words,
  preserving each result as `u32`; do not expose an address or FID chosen by
  userspace;
- snapshot raw B/CCI PLL, mux and divider through the existing DVFSP semaphore
  ownership path, with bounded acquisition and no clock write;
- include `0x10222274` in the fixed secure-read set;
- timestamp all fields inside one kernel record and emit records around existing
  natural HPS/PSCI/secondary-completion hooks without changing HPS policy or CPU
  masks.

Even that observer needs a separate source and binary review before use. A
generic `/dev/mem`, raw I2C, arbitrary-register debugfs, or arbitrary-SMC tool
would expand the attack and mutation surface and is not an acceptable shortcut.

## Source pins

The recovery-VM checkout was clean at the audited commit. Relevant file hashes:

| Public source path | SHA-256 | Audit use |
| --- | --- | --- |
| `drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c` | `7232f5ba7347511d97da6947c6833811b439d3116f95a13e631be40d7033b2e7` | fixed DA9214 read; unsafe `dvt_test`; secure-read subset |
| `drivers/misc/mediatek/power/mt6797/da9214.c` | `32306d145361d5b3da8a024d0a495906ea275f71741cee39d1fc3dcaf7c096a3` | I2C mutex and cached sysfs selector behavior |
| `drivers/misc/mediatek/base/power/mt6797/mt_cpufreq.c` | `a420033f65c49bf509182388fcb803161e69e93cf7d334b723fe7a0c55b8c293` | B/CCI reported frequency and voltage semantics |
| `drivers/misc/mediatek/base/power/mt6797/mt_cpufreq_hybrid.c` | `6094e778fe3eb0f2c24ffb63bb404af2e40da519514ddbba608bea3b5500fb63` | safe `dvfsp_reg`; mutating `dbg_repo` show |
| `drivers/misc/mediatek/base/power/mt6797/mt_dcm.c` | `46304a982c544276ed9d75e4119617646b9e6c9ecc6ae997c8b43f41ea4029ad` | MP2 DCM diagnostic compiled out |
| `drivers/misc/mediatek/base/power/mt6797/mt_clkmgr.c` | `676965631144df839bdb2088413742ed3c5205fee4e8d6ea34ef0ba0e1014b5f` | empty B/CCI proc read handlers |
| `drivers/misc/mediatek/base/power/mt6797/mt_pm_init.c` | `09de968105a4ab975fd6adacff69ef3edcfe84d3619975fb66066c49d02ff8a4` | power debug registration audit |
| `drivers/misc/mediatek/base/power/spm_v2/mt_spm.c` | `b249d02cd449f953e1f8836d0e76c3ac9c80262cad8117a8d761d73f983e10de` | SPM surface audit |
| `drivers/misc/mediatek/base/power/include/spm_v2/mt_spm_reg_mt6797.h` | `a89a7b879f0b5ef8fd7d9625ff767741c6ad9e4f56a6bd82b52865cfd2d93c6b` | SPM names and masks |
| `drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c` | `31aa4fe4ce00125b4a09da75534cd840c9a962aaa33752aecfce96c10b3ef20a` | TOPRGU ownership and locking |
| `arch/arm64/kernel/psci.c` | `81c4c2851fef7dea691dbc7d1f9e54c6185e127f6b136b77a7d7711cf82b6fe4` | external preparation and internal-only observations |

## Validation

The scaffold was validated locally without device or VM mutation:

- `sh -n scripts/remote-probe.sh`: pass;
- `bash -n scripts/collect.sh`: pass;
- `perl -c scripts/bounded-exec.pl`: pass;
- `scripts/test-readonly-collector.py`: pass.

The fixture test verifies redaction, bounds, the expected/mismatched DA9214
selector labels, every exact identity/power/stability rejection, pre-gate and
mid-sample missing-power rejection, before/after power drift fail-stop,
required-bracket absence and exact `read-failed` fail-stop, safe-value capture,
mode-only excluded-node inventory, and tripwire non-disclosure for every
excluded callback including B `cpufreq_volt`. It also verifies both exact root
representations, their mismatch/unavailable failures, and that fixture mode
does not invoke host or mocked `findmnt`. A mocked SSH test verifies the
fixed target/key, server-alive options, private direct-child output rule,
absence of a target override, mode-0600 success output, and mode-0600 partial
preservation on remote failure and hard timeout. Direct bounded-helper tests
verify normal/signal status propagation, partial stdout on timeout, and that
an unrelated sentinel process survives. A live hardware capture and
ShellCheck remain outstanding at this revision.
