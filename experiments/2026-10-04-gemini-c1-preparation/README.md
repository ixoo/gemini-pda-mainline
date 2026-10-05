# Gemini C1 PMIC, RTC and lid preparation

Initial offline integration audit, 2026-10-04, followed by the selected key
and RTC/lid compile integrations below. No boot candidate or device operation is admitted
by this record. The [roadmap](../../docs/ROADMAP.md)
owns priorities. The [source audit](results/source-audit.json) pins the selected
prepared driver files and the proposed baseline inventory.

## Selected foundation needs the reviewed key fixes

The `mt6797-a53-service-facilities` profile selects the Linux 7.1.3 service
foundation. It includes MT6351 key data and MFD resources, but not the separate
[seven-patch key correction topic](../2026-09-08-mt6351-keys-preparation/README.md).
Inspection of the exact `fcca630d` prepared source confirms three gaps:

- The IRQ handler ignores `regmap_read()` failure before reporting a key.
- Reset setup returns void, ignores `regmap_update_bits()` failure, and runs
  after input registration.
- `power-off-time-sec` is shifted directly into the timeout field. An eleven
  second property would select 3 (documented five seconds), rather than 1.

Integrate the already reviewed error and seconds-conversion changes onto this
selected foundation before enabling a key child. Do not append the independent
MT6351 data/MFD patches blindly: the selected tree already carries those data
and resources. Reuse the actual-function regression and its 94 duration/error
cases, then compile the integrated profile and check the relevant bindings.
The [reset-policy record](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md)
owns the mapping and the live policy admission gate.

Neither the retained configuration nor a successful `pmic_access` store/show
pair proves current reset fields. The [binary audit](../2026-09-08-mt6351-keys-preparation/RESET_BINARY.md#why-the-existing-debug-read-is-insufficient)
shows ignored transport errors and a shared cached result. Alternating reads
alone cannot turn that interface into attributable transport success. Keep the
key child disabled until the reviewed live observation resolves the policy.
No long press is part of the initial short-key event test.

## Baseline inventory and observation boundary

The PMIC H8 prose calls its subset nine registers, but enumerates ten:
`TOP_RST_MISC`, `STRUP_CON15`, three `TOP_CKPDN_CON` words,
`BUCK_VCORE_CON0`, `LDO_VDRAM_CON0`, and three `CHR_CON` words. The exact ten
addresses are in the audit. They come from the existing
[decoded source table](../2026-10-04-gemini-pmic-basics-re/results/pmic-init-setting-decoded.tsv)
and selected register header. This is an inventory, not read-safety proof.

Before implementing the probe-time observation, review read side effects and
regmap policy for each address. Define its position before child drivers can
change these settings, record each transport return alongside its value, and
stop on the first failure. Label the result loader-inherited state after the
wrapper's setup, rather than raw kernel-entry state. Exclude interrupt-status,
clear/set aliases, RTC mailbox and calibration windows. No vendor init-table
writes follow merely because a value differs.

## RTC and lid integration

The RTC child already exists in SoC DT through patch 0013; do not duplicate it.
The service foundation starts from a handoff fragment that disables RTC_CLASS.
A C1 fragment must explicitly enable RTC_CLASS and RTC_DRV_MT6397, and select
the relevant reviewed RTC alarm/error corrections. Audit the selected MFD IRQ
error handling against the independent MFD topic before claiming alarm delivery.
RTC access includes driver transactions; it is not a raw passive snapshot.

The disabled [hall candidate](../../patches/v7.1.3/0074-arm64-dts-mediatek-gemini-add-disabled-hall-gpio-keys-candidate.patch)
already describes GPIO66, active-low SW_LID and 64 ms debounce without a wake
source. A C1 profile can enable this existing node and build KEYBOARD_GPIO in;
keep event consumption separate from any userspace suspend-on-close policy.
The [lid record](../2026-10-04-gemini-lid-microsd-usb-re/README.md) owns polarity
and IRQ hypotheses. One close/open measures events, not suspend or wake support.

## Future attended packet

After consuming the installed version candidate and the reviewed Gemian
baseline, construct one explicitly validated C1 candidate. Preserve the current
PSCI power-off path and regulator/clock ignore flags. Capture the bounded PMIC
baseline, bindings and interrupt counts; then one short power-key press, lid
close/open, and a ten-second RTC alarm with the system awake. Suspend/wake is a
separate gate. Use the existing PSCI power-off with the charger detached before
considering a PMIC replacement.

C2a may share that boot only after its separate I2C/register-read review: no
charger driver bound, finite REG00–REG14 observation, and no boost or charge
policy writes. No automatic poweroff, recovery or other device command is
provided by this preparation record.

## Validation

The audit checked selected manifest/series membership and actual prepared key
functions/MFD resources, and parsed a ten-entry unique-address inventory.
Historical Buildbox receipts are evidence for their exact original inputs only.
The initial audit performed no build, schema test or hardware measurement.
The subsequent key integration results below are separate from that audit.

## Selected key integration

The four existing key error/duration patches apply unchanged to the selected
Linux 7.1.3 driver and binding. The new
[original compile series](https://github.com/ixoo/gemini-pda-mainline/blob/052f59375abca9ce0abd927d553e89f94b50a003/patches/series-a53-pmic-keys-compile) extends the service
foundation with only those four patches in canonical order. It omits the
independent topic's duplicate chip data and MFD additions. All 94 actual-function
regression cases pass against this integrated source; source hashes and limits
are in the [integration receipt](results/key-integration.json).

`mt6797-a53-pmic-keys-compile` adds only input/key compilation settings and a
release suffix to the service profile. DT is unchanged, with no enabled PMIC
key child; this does not select a hardware long-press policy. Buildbox
compilation, package validation and focused binding checks pass for input
`052f5937`. The existing patches retain their
synthetic non-certifying authorship and do not become submission-ready by
integration. Their upstream destination and deletion condition remain those
of the independent key topic.

```sh
KERNEL_PROFILE=mt6797-a53-pmic-keys-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-pmic-keys-compile ./scripts/buildbox fetch-package
```

The [receipt](results/key-integration.json) pins the compiled key object,
configuration, Image.gz, build log and validated package inventory. The driver
and binding in the exact prepared source match the host-tested hashes. Fetch
verification and local inventory/Image.gz rehashes pass. Input, keyboard and the
PMIC key driver are built in. DT and the installed candidate remain unchanged.
Only the inherited patch-0261 whitespace and unused CPU rollback callback
warnings appear; there is no new key-driver warning.

Focused kernel `dt_binding_check` passes with dtschema 2026.9 and separate
managed temporary output, which was removed afterward. The local binding
meta-schema and eight dtc-compiled fixture cases pass with dtschema 2026.6:
four MT6351 durations accepted, duration 1 rejected, legacy MT6331 duration 1
accepted, mode 3 rejected, and absent duration accepted. These schema fixtures
are offline descriptions, not admitted Gemini key nodes. No board DT changed,
so no new board `dtbs_check` was run. The Linux-only repository provenance
fixture is skipped on macOS; the actual package passed the remote Linux
validator. No boot image, installation, register access or physical reset was
performed. The live policy observation still gates key-node admission.

## RTC and lid compilation

The narrower key profile above is retired in favor of
`mt6797-a53-c1-compile`; its commands and receipt retain their original commit
identities. The current [series](../../patches/series-a53-c1-compile) selects the
same four key fixes and two existing RTC fixes in canonical order. Both RTC
patches apply unchanged; the actual alarm handler passes 160 cases and the
wake callbacks pass 16 cases. The [RTC receipt](results/rtc-integration.json)
pins the integrated source. The initial build `9e2f9277` stopped before
compilation: RTC_NVMEM defaults on with RTC_CLASS and selected NVMEM despite
the foundation exclusion. The fragment now disables RTC_NVMEM; the time/alarm
packet needs no RTC storage window. Corrected input `fcd8c161` passes Buildbox
compilation and remote Linux package validation. Fetch and all local package
checksums pass; all 123 DTBs match the earlier key-only package. The compiled
RTC source matches the 176-case host-tested source, including suspend/resume
callbacks, and gpio-keys compiles. Only the inherited unused CPU rollback
callback warning remains. No DT or binding changed, so no new schema check
was run.

The current [fragment](../../configs/gemini-a53-c1-compile.fragment) builds
RTC and gpio-keys in and compiles the PM callbacks. It disables automatic RTC
system-clock synchronization so that a future test can classify the RTC first.
Suspend compilation is not suspend admission. DT remains unchanged: no key
child, disabled lid candidate, and the existing RTC child. This is a compile
checkpoint, not a deployable C1 packet. MFD IRQ/error integration was still
missing at this input; the later section records its compiled successor.
The bounded PMIC observation and runtime protocols remain incomplete.

```sh
KERNEL_PROFILE=mt6797-a53-c1-compile ./scripts/build-kernel --backend buildbox
KERNEL_PROFILE=mt6797-a53-c1-compile ./scripts/buildbox fetch-package
```

## Selected MFD integration gap

The selected IRQ driver checks status-read failures but ignores initial/normal
mask and acknowledgement write failures. Its PM notifier also ignores wake-mask
and parent IRQ wake errors, and lifetime handling lacks the independent topic's
corrections. The [RTC receipt](results/rtc-integration.json) records the source
identity and bounded private replay. Initial-mask fix 0006 applies unchanged;
lifetime fix 0007 fails against the selected IRQ-domain context, so replay stopped.
The selected tree uses `chip->num_irq_regs * 16` for the domain span; the
independent patch expects a different local variable. Integration must preserve
that span, then replay and test the remaining error, wake recovery and cleanup
changes. No MFD patch was selected by this audit.

## MFD corrections selected for C1 compilation

The [MFD integration receipt](results/mfd-integration.json) pins seven selected
corrections and all four tested driver/header files. Two format patches adapt
the domain-lifetime and child-suspend ordering drafts to the selected foundation;
the bank-derived domain size remains unchanged. The other five existing patches
apply unchanged: initial mask failure, notifier lifetime, modern-family parent
wake ownership, legacy suspend recovery and runtime transport diagnostics.
The ordering successor removes the intermediate notifier, retaining device PM
callbacks that run after child suspend and before child resume.

Exact replay passes. The existing actual-function fixtures pass 58 lifetime,
77 suspend/recovery and 21 runtime-error cases, plus late-child wake ordering
for two, three and four banks. The lifetime fixture now checks domain size for
each legacy chip; an injected wrong size is rejected. Strict checkpatch passes
for both adaptations with only `MISSING_SIGN_OFF` excluded: these remain
unsigned internal drafts, with the original synthetic authorship retained.
The adaptations retain the independent topic's MFD subsystem destination and
deletion condition: remove them when the corresponding lifetime and PM-ordering
fixes are in the selected upstream baseline. No new contributor certification
is asserted. Buildbox compilation and Linux package validation pass for input
`c2eeeb8a`. Fetch and all local checksums pass; the four prepared source files
match the host-tested hashes. Both IRQ variants and the shared core compile,
including domain cleanup and device PM callbacks. All 123 DTBs are unchanged
from the prior C1 package. Only inherited patch-0261 whitespace and unused CPU
rollback callback warnings appear. No binding or DT
changes, enabled key/lid node, candidate, register access or physical PM test
are included. The earlier RTC build receipt retains its original inputs.

The superseded key-only prepared source and build outputs are removed after
integrity verification; its validated package and log remain retained. The
active C1 and STP source/build trees are kept.

## Observation protocol review

The [observation review](OBSERVATION_REVIEW.md) separates uncached wrapper
transport success from per-register read semantics and drafts the RTC/lid
packet. At the review's `c2eeeb8a` input, the RTC callback has no rollover-attempt
limit; a host
probe reaches a fourth attempt. Class registration can inherit existing alarms,
and that IRQ handler ignores alarm-disable/trigger failures. These
concrete gaps must be resolved before a bounded RTC packet is admitted. No
observer, tool, candidate or device access is added by this review.

## Bounded RTC reads and IRQ diagnostics

Two logical [C1 series](../../patches/series-a53-c1-compile) additions address
the observation review's driver gaps. Counter reads allow at most three
bulk/seconds pairs, returning `-EAGAIN` when all are inconsistent. A successful
third pair still returns normally; transport errors return immediately, and
month/weekday conversion occurs only after a coherent result. No RELOAD or
time-setting write is added.

The IRQ successor reports status-read, alarm-disable and trigger failures with
rate-limited messages. It retains the existing alarm-only mask update, event
delivery, IRQ returns and register-operation counts. It adds no transport retry
and does not label a failed alarm disable recovered. The trigger helper retains
its existing busy-poll diagnostic; that helper's earlier log is not made
rate-limited by this change.

The [follow-up receipt](results/rtc-followup.json) pins the exact parent/child
source and patches. Ten actual-function counter cases, 200 alarm cases with
`--require-reports`, and the existing 16 wake cases pass. The old unbounded
parent fails the counter fixture, and a removed status-error report fails the
alarm fixture. Exact replay and strict checkpatch pass with only the unsigned
archive's missing-sign-off exclusion. These internal drafts target the RTC
subsystem and are removed when equivalent fixes enter the pinned upstream
baseline; no certifying author or sign-off is invented.

Buildbox compilation, Linux package validation and fetch pass for input
`45143bfc`. The actual RTC source matches the host-tested hash; the object
contains all three IRQ error messages. All local package checksums pass. The
resolved configuration and all 123 DTBs match the prior C1 package. Only the
inherited patch-0261 whitespace and unused CPU callback warnings remain. No
DT or binding changed, so no new schema check was run. The previous
518-patch receipt remains evidence for its original inputs. RTC core timer
behavior, inherited alarms, the exact userspace tool, PMIC target read semantics
and live key policy remain gates before an attended candidate. No board node,
candidate or device operation is added.

## Standard RTC alarm cancellation

The [alarm-tool review](ALARM_TOOL_REVIEW.md) found that the selected driver
lacks `alarm_irq_enable`: class timer removal can be followed by `-EINVAL`
without a hardware disable, and file close leaves the alarm armed. The new
standard callback uses the existing alarm/one-shot mask and trigger, returns
transport errors and reports them when core cleanup discards the return.
The [receipt](results/rtc-alarm-enable.json) records 111 callback/class cases,
226 unchanged RTC regressions, exact replay and strict checkpatch. The single
timer-removal model reproduces the old failure and two possible callback
invocations per explicit disable. No physical cancellation is claimed.

Buildbox compilation, Linux package validation and fetch pass for input
`a7dba295`. The actual RTC source matches the host-tested hash and the callback
is present in the compiled object. All local package checksums pass; configuration
and all 123 DTBs match the prior C1 package. Only inherited patch-0261 whitespace
and unused CPU callback warnings appear. No DT or binding changed, so no new
schema check was run. The unsigned draft
targets the RTC subsystem and is removed when equivalent callback support
enters the pinned upstream baseline. Board nodes and configuration are unchanged.
BusyBox's reviewed source has an unbounded awake wait and cleanup paths that
can be skipped; the retained ram-root has no verified alarm executable. The
final tool, inherited-alarm admission and callback effect budget still gate
the candidate. No device operation was performed.

## Updated C1 order and PMIC field evidence

The roadmap review in `06769f76` removes Gemian session A as a prerequisite.
The [read-semantics review](PMIC_READ_REVIEW.md) records eight document-covered
words and the two source-only addresses that still need read-effects evidence.
C1's observer must precede key probe writes; explicit key reset policy and the
lid node are the next board settings. The historical reviews above retain
their original inputs and gaps rather than overriding the updated priority.

## Observer, power key and lid (2026-10-05)

Two experiment-only patches complete the C1 kernel side. Patch
[0006](../../patches/v7.1.3/c1/0006-mfd-mt6397-log-a-bounded-MT6351-baseline-before-IRQ-setup.patch)
adds the default-off `MFD_MT6351_BASELINE_OBSERVER`. After MT6351 chip
identification and before IRQ setup or child registration, it reads the ten
audited words once. It logs index, name, address, transport result and value,
stops at the first failed read, never retries or writes, and lets probe
continue. The C1 fragment enables it.

The two words without document coverage were checked against the public
Gemian source named in the [reset-policy record](../2026-09-08-mt6351-keys-preparation/RESET_POLICY.md).
Its MT6797 field table defines only control-enable fields in them:
power-off sequence and pre-off enables in `STRUP_CON15`, and VCORE enable and
selector ownership in `BUCK_VCORE_CON0`. No status, interrupt or clear field
is defined at either address. This is source evidence, not a measured read
effect.

Patch [0007](../../patches/v7.1.3/c1/0007-arm64-dts-mediatek-gemini-enable-C1-power-key-and-lid.patch)
adds the MT6351 key child with only the power key, one-key long-press mode and
an eleven-second duration, and enables the existing hall node without a wake
source. Both patches pass strict checkpatch with only the missing sign-off
excluded, and the board DT compiles. Only the C1 profile selects them.

Buildbox compilation on buildbox-2 and remote package validation pass for
input `300c4244`. Fetch and all local checksums pass.

| Item | SHA-256 |
| --- | --- |
| Package inventory | `5aa0594bb6c44f0d88b0aae7ddeb9c4974aff1c6171131db46c31d4996756cba` |
| Board DTB | `a3f612a797ee0d0d33061cbbb787ec22f0e0609c2f95d5b29553761b4424a11c` |

The configuration builds the observer, the PMIC key driver, gpio-keys and the
RTC driver in. The board DTB carries the key child and an enabled lid node.
Only the inherited patch-0261 whitespace and unused CPU rollback callback
warnings appear. `dt-validate` against the input and MT6397 MFD bindings
reports no key or lid error. Its one complaint is the existing MT6351 RTC child
from SoC patch 0013, which this change does not touch.

The [protocol draft](PROTOCOL.md) and the finite [RTC alarm script](rtc-alarm.sh)
cover the boot. The script uses the standard sysfs `wakealarm` file, so no new
binary is needed. Writing a relative time refuses an already enabled alarm
with `EBUSY`, and writing zero removes the class timer through the new
disable callback. It passes ShellCheck and a plain-file fixture of the refusal
and timeout paths; the fired path needs real sysfs.

Candidate composition is still open. It needs the private A53 RAM root and the
last booted parent candidate, which are not on the Buildboxes. C2a stays out
of this boot until its I2C transport review exists.

## Regulator flag correction (2026-10-05)

The attended-packet section above asks to preserve "regulator/clock ignore
flags". Only `clk_ignore_unused` exists. The C1 package, like the booted
WMT-versions parent and the STP package, forces a command line without
`regulator_ignore_unused`; the laptop-side candidate check found this. No
rebuild is needed. In pinned Linux 7.1.3, late cleanup only disables a rail
that has a DT node, is not `regulator-always-on` and has no enabled consumer.
Rails without a node get no status-change permission and are left alone. The
C1 board DT describes only VEMC, enabled by the eMMC, and always-on VIO18, so
no MT6351 rail is switched off at late init.

## First C1 boot (2026-10-06)

Status: partial pass. The laptop device custodian ran the boot. The figures
below are from its report; its runtime receipt, regulator inventory and sealed
kernel log stay private on the owner's machine.

| Item | Value |
| --- | --- |
| Candidate boot2 SHA-256 | `732e525ef99ffc5efb7c8b3922eeb7769495ed26328fccb27461bca879e2cff2` |
| Mainline boot ID | `bb7616e9-640e-40f4-9a2e-9c9adc85798d` |
| Release | `7.1.3-gemini-a53-c1-compile` |
| Sealed kernel log SHA-256 | `4902429496493970fadf98b8b8c41c6944ea5afbe527742c4690b118beb31f1b` |
| Gemian boot ID after recovery | `e67b8a0b-6838-431a-a991-d9f287bb8d30` |

Observations:

- **PMIC baseline.** All ten reads returned 0 and the completion line was
  logged. The values are in the private log.
- **Bindings.** The PMIC key, RTC and gpio-keys devices bound. Regulator
  names and states were recorded.
- **Power key.** One short press raised the PMIC parent interrupt count from
  0 to 2, and the key interrupt counts from 0 to 2 and 0 to 1. The PMIC
  interrupt path to the AP works.
- **Input events.** Both captured event files were empty after the timeout
  killed `hexdump`. Delivery to userspace is unproven; output buffering is the
  likely cause.
- **Lid.** One close/open left the Hall interrupt count at zero.
- **RTC alarm.** Not tested. The script refused before arming, because it
  required `rtc0/name` to be exactly `mt6397-rtc`, while the RTC core prints
  the driver and device name, `mt6397-rtc mt6351-rtc`.
- **Power-off.** A delayed `poweroff -f` with the cable detached powered the
  device off, as the owner observed. PSCI power-off is the working baseline.
- **Recovery.** The owner started Gemian normally; SSH confirmed a changed
  boot.

## Follow-up fixes (2026-10-06)

- [rtc-alarm.sh](rtc-alarm.sh) now checks the RTC's bound driver instead of
  the name string. ShellCheck and the fixture pass for the right and the
  wrong driver.
- The [protocol](PROTOCOL.md) captures events with `cat` and decodes them
  afterwards.
- **Lid.** The vendor kernel's active state for GPIO66 is GPIO mode with a
  pull-up, per the [lid recovery record](../2026-07-12-hall-lid-switch-recovery/README.md#live-observations).
  Mainline MT6797 pinctrl had no pull maps, so the pad kept whatever the loader
  left. Patch [0008](../../patches/v7.1.3/c1/0008-pinctrl-mediatek-mt6797-add-GPIO66-pull-and-input-fields.patch)
  maps GPIO66's pull-up, pull-down and input-enable bits from the public
  vendor GPIO table. They are bit 13 of IOCFG_R at `0xe0`, `0xc0` and `0x10`.
  Patch [0009](../../patches/v7.1.3/c1/0009-arm64-dts-mediatek-gemini-pull-up-the-lid-sensor-input.patch)
  sets `bias-pull-up` and `input-enable` on the lid pins. A missing pull-up is
  the leading hypothesis, not a measured cause.

Both patches pass strict checkpatch with only the missing sign-off excluded.
The pinctrl schema rejects every existing MT6797 pin group in the same way,
so it gives no signal on this change.

A short follow-up boot would test only the new measurements: event delivery,
the RTC alarm and the lid. It is worth running once this profile is rebuilt.

Buildbox compilation on buildbox-2 and remote package validation pass for
input `6bcff5a5`. Fetch and all local checksums pass. The configuration is
identical to the `300c4244` package; only the board DTB
and the pinctrl object change.

| Item | SHA-256 |
| --- | --- |
| Package inventory | `d697d6398d0fa1577a01d87f9eafa12577ad10ea0f37680ff2db85c11256b420` |
| Board DTB | `bb10a7daac6a27387eeddc4cef286e686d2ea8671221530ae49dd7f08c49f235` |

The lid pin group in the DTB carries `bias-pull-up` and `input-enable`. Only
the inherited unused CPU rollback callback warning appears. A follow-up
candidate needs the same private parent and the fixed `rtc-alarm.sh`.

## C1 follow-up boot (2026-10-06)

Status: complete. Power key, RTC alarm and PSCI power-off pass; the lid stays
negative. The laptop device custodian ran one attended boot with the follow-up
fixes. Figures are from its report; the sealed log and raw captures stay
private on the owner's machine.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `190fc7f270a31213cc2202eaa4495995dfdd1f47962fd16200726a1f406bc464` |
| Candidate receipt SHA-256 | `d66772be24567b4851abfd813a9ae64c0d442bed21afdc79711e837fc6a30329` |
| Package | commit `6bcff5a5`, inventory `d697d639…` |
| Mainline boot ID | `0b65772f-3bb9-4fa7-b477-b2e852a420e4` |
| Sealed log SHA-256 | `fdaa35d46b2a2a9d3d51bd0ab29290215c10500fb541f0eb249bd7935ccc7f1e` |
| Gemian boot ID after recovery | `267f40f2-9a9a-4f64-a072-653a350f8d13`, `3.18.41+`, Debian 9.13 |

Observations:

- **PMIC baseline.** All ten reads returned 0, with the completion line.
- **Power key.** The `cat` capture held 96 bytes: `KEY_POWER` (116) press and
  release with their sync events. The key interrupt counts rose to 2 and 1.
  Key events reach userspace.
- **RTC alarm.** The fixed script armed one ten-second alarm, which fired after
  10 s; the RTC interrupt count went from 0 to 1, cleanup passed and the
  script exited 0. Sysfs was mounted read-only in the RAM root, so the session
  remounted it read-write for the `wakealarm` write only, with a trap that
  restored read-only.
- **Lid.** The capture was empty and the Hall interrupt count stayed at zero
  across one close/open, despite the GPIO66 pull-up and input enable. There was
  no repeat.
- **Power-off.** After identity checks, one delayed power-off with the shared
  USB/charger cable detached turned the unit off, as the owner observed.
- **Recovery.** The owner started Gemian normally; a changed boot was
  independently confirmed.

## Lid diagnosis (offline)

The PMIC interrupt reaches the AP through the same EINT controller (EINT176)
and works, so the controller and its parent interrupt are sound. What is
specific to the lid is its pin, its line and the debounce:

1. **Hardware debounce on a dual-edge line.** gpio-keys sets the debounce
   before it requests the interrupt. Mainline `mtk_eint_can_en_debounce()`
   decides from the line's current sensitivity register, which at that moment
   still holds the loader's setting. If the loader left EINT5 level-sensitive,
   as the vendor configures it, hardware debounce is enabled and the line is
   then switched to dual edge. The vendor EINT driver
   (`irq-mt-eic.c`, `mt_can_en_debounce()`) never enables hardware debounce on
   an edge-sensitive line. This is a hypothesis.
2. **The pin level never changes.** A sensor supply, a stronger pull or a
   different magnet position could leave GPIO66 constant.

Neither C1 boot could separate these: the C1 kernel has no debugfs, so the
GPIO66 level was never read. The lid record's own branches need that level.

## C1-3 lid test (2026-10-06)

Status: consumed; the pin level changes but EINT5 never fires. The laptop
device custodian ran one boot under [LID_PROTOCOL.md](LID_PROTOCOL.md) with one
lid close/open. Figures are from its report; raw data stays private.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `8af1bfb5d37f74e0899a402021408911f146c6d3f4786522acbbcb17ed91ba74` |
| Candidate receipt SHA-256 | `3368f5e27fbf8a7c1b49a1e120569bace334adc9ec5b18b8c47ecee5443f61db` |
| Package | commit `668d1356`, inventory `0d01494f…` |
| Mainline boot ID | `fa3e393b-0758-4dae-865c-c6065fc49a5b` |
| Sealed log SHA-256 | `1ecca4974f9c3710446a83a106e33e7d9f58eefb75d391b5659c88736db88bdb` |
| Gemian boot ID after recovery | `bbc287f1-1538-48e3-9f58-bf9145b74054`, `3.18.41+`, Debian 9.13 |

- **GPIO66 level.** Read-only debugfs showed high with the lid open, low when
  closed, and high again when reopened. The sensor, pull-up and input enable
  work; low means closed, matching the `GPIO_ACTIVE_LOW` description.
- **Interrupt.** The Hall EINT5 count stayed 0 in every snapshot, and the
  event capture was empty when its 60 s timeout ended it. Disabling debounce did
  not restore the interrupt, which rules out the debounce hypothesis.
- **Recovery.** The reviewed native recovery request was sent once and the
  kernel logged its restart line. The host process then exited with status 255
  at the 19.0 s outer timeout. There was no second request. A changed Gemian
  boot was independently confirmed. The transport timeout is a limitation of
  the recovery tooling, recorded separately from the confirmed return.

## EINT5 analysis (offline, 2026-10-06)

- **Mapping.** GPIO66 is the only pin mapped to EINT5 in the MT6797 table;
  the table has no duplicate EINT numbers.
- **Controller.** The PMIC interrupt (EINT176) works through the same
  controller and parent GIC line, so the controller, its domain enables and the
  parent are sound.
- **What is different.** EINT176 belongs to a virtual GPIO. For virtual GPIOs,
  `mtk_xt_set_gpio_as_eint()` returns before touching the pad. For a real pad
  it sets the mode, the direction and then the Schmitt trigger (SMT), and
  upstream assumes every real GPIO supports SMT. MT6797 has no SMT map in
  mainline, so that write returns `-ENOTSUPP` and is ignored. No real-pad EINT
  has ever been shown working on mainline MT6797.
- **Leading hypothesis.** The EINT edge detector sees the pad without Schmitt
  conditioning; a slowly moving hall output never produces an edge it accepts,
  while the GPIO data register still reads the level. The vendor GPIO table
  places GPIO66's SMT bit in IOCFG_R at `0x30`, bit 27, shared with GPIO67.
- **Alternative.** EINT5's dual-edge emulation or its status path is wrong for
  real pads. A software-triggered EINT5 (the controller's `soft_set` register)
  would separate routing from pad detection, but that is a register write that
  needs its own review.
