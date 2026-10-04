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
