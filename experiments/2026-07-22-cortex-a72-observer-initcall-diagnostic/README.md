# Experiment: isolate the MT6797 A72 observer initcall

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-cortex-a72-observer-initcall-diagnostic` |
| Status | `attempt 1 inconclusive after grey display and owner-forced return` |
| Subsystem | MT6797 Cortex-A72 observer registration, I2C6, DA9214, boot-time SMP |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Investigator(s) | Project maintainers |
| Candidate | `AF` |

## Question or hypothesis

Does Candidate AF, retaining exact Candidate AE except for one resolved
configuration change, reach a stable eight-Cortex-A53 USB runtime when that
change prevents
`mt6797_a72_power_driver_init` from registering and probing the read-only A72
observer, while leaving the AE patchset, final DTB, I2C6/DA9214 description,
DA9211 regulator driver, rejecting CPU8/9 enable method, and byte-exact
Candidate AD initramfs in place?

Exact AE had been installed and read back on logical `boot2`, and the owner
selected that boot entry. LK was the last visible screen: no mainline console
appeared before the device went directly into an automatic reboot and returned
to Gemian. The immediate private post-return capture had a stable Gemian boot
ID but an empty pstore archive. This is a failed but causally inconclusive AE
cycle: it supplies no post-LK kernel identity, observer, fault, or reset
boundary. Do not repeat exact AE. AF is a new kernel/configuration derivative
with a decision-changing live observation path.

AF tests only observer registration/probe as a possible boundary. It does not
enable a Cortex-A72 power sequence, request CPU8 or CPU9 online, or claim that
an AF pass alone proves the cause of the inconclusive AE return.

## Provenance and environment

- Kernel release: pinned Linux `7.1.3` from `kernel/manifest.json`.
- Patchset: byte-exact Candidate AE, expected SHA-256
  `7e675c84798314651c46109e5161cf62190445acaa9272502edf094523245e67`.
- Baseline resolved AE configuration SHA-256:
  `bdece76d4b23bfe2e14cc01dc0981b0123109bd206f1016bb4d73fe37c7de9bb`.
- Baseline AE `Image.gz` SHA-256:
  `4c04a781080fc2dbb8557e967fd0d4e8e198bcd6a7c4982f38a20aa3e191b96f`.
- Exact AE final DTB SHA-256:
  `3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b`.
- Exact AD initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Exact normalized AE source-build provenance SHA-256:
  `b61e539bf4d67710f3ef5557055a878b49e6f099477f3e0e508dfc153b052c1e`.
- Kernel profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist`.
- Boot path for a later authorized runtime: LK Android-v0 logical `boot2`.
- Build environment: the repository recovery VM and pinned compiler/linker
  recorded in package provenance.

The AF profile is exact AE plus
`configs/gemini-a72-observer-initcall-blacklist.fragment`. That final-wins
fragment changes only `CONFIG_CMDLINE`, appending exactly one token:

```text
initcall_blacklist=mt6797_a72_power_driver_init
```

The name is not guessed: exact AE's `System.map` exposes the built-in initcall
function and its level-6 initcall entry under that symbol.

## Safety assessment

The configuration keeps `maxcpus=8`; CPU0--7 are the already hardware-passed
Cortex-A53s and CPU8/9 remain offline behind AE's rejecting
`mediatek,mt6797-psci` method. AF adds no CPU-online request, active A72 power
operation, regulator voltage/enable operation, reset operation, SMC,
raw-memory access, storage driver, or userspace watchdog owner. It does retain
AE's normal DA9211 probe, whose paged regmap access can write a selector
register, and normal platform initialization can gate unused SCPSYS clocks.
Those inherited boot-time operations are not claimed to be read-only. The
exact AD initramfs has no normal-path automatic reboot. Runtime state is
observed read-only for at least 45 seconds and twice across a further
five-second interval.

The artifact builder and validators perform no device access. Any later
installation remains outside this scaffold and must use the repository's
guarded logical-`boot2` workflow, full backup/readback, exact inactive-target
checks, and separately pinned final hashes. The runtime collector verifies the
dedicated USB MAC/address and performs only procfs, sysfs, DT, and dmesg reads.
The collector itself never opens `/dev/watchdog0` or writes CPU, regulator,
reset, I2C, memory, or storage interfaces; this narrow statement does not erase
normal boot-time writes by retained kernel drivers.

Stop after one attributable AF cycle. If exact AF cannot be identified, if the
USB service does not survive to 45 seconds, or if a fault/reset occurs, return
to known-good Gemian and preserve new evidence. Do not retry an identical AF
artifact without adding an independent observation that can distinguish the
failure.

## Associated code

- `configs/gemini-a72-observer-initcall-blacklist.fragment`: sole AF resolved
  configuration delta.
- `kernel/manifest.json`: exact AE-plus-one-fragment profile boundary.
- `scripts/validate-package.py`: exact AE baseline and normalized toolchain
  provenance, unchanged patch/DT, one-line resolved-config delta, initcall
  symbol, and two-build gates. Relevant manifest contracts are semantic so
  unrelated later profiles or patch-series growth do not invalidate this
  historical AF package.
- `scripts/build-candidate-af.sh`: deterministic Android-v0 construction from
  an AF package plus exact AE/AD inherited payloads; no device action.
- `scripts/validate-boot.py`: canonical container, exact AE DT, exact AD
  initramfs, and blacklist-marker validation.
- `scripts/validate-artifact-reproduction.py`: byte-and-mode comparison for
  two independent AF artifact trees.
- `scripts/normalize-build-json.py`: removes only `generated_utc` from package
  provenance before deterministic artifact comparison.
- `scripts/collect-runtime.sh`: bounded read-only USB collection at and after
  the 45-second stability boundary.
- `scripts/collect-cycle.sh`: once-only host watcher that discovers the exact
  dynamic USB interface, rejects MAC/address/route ambiguity, preserves every
  phase, and invokes `collect-runtime.sh` exactly once when packet-ready.
- `scripts/validate-runtime.py`: exact AF identity, blacklist effect,
  I2C6/DA9214 survival, CPU masks, watchdog-owner absence, and fault oracle.
- `scripts/derive-installer.py`: exact narrow derivation from the validated AE
  installer with source-pinned AF and predecessor identities.
- `scripts/test-installer-derivation.py`: storage-safety, lineage, and exclusive
  publication rejection suite for the generated installer.

## Procedure

1. Build the named AF profile twice in independent VM build and artifact
   roots. Validate each package against an exact validated AE package, then run
   package reproduction mode.
2. Run `build-candidate-af.sh` independently for both packages using the exact
   AE artifact `candidate-AE-a72-observer-d9895f61`. Require both output trees
   to pass `validate-artifact-reproduction.py`.
3. Record the final package, resolved config, `Image.gz`, exact AE DTB, exact AD
   initramfs, raw Android-v0 image, and exact-size padded `boot2` hashes before
   any future installation. Add a guarded installer only after those values
   are pinned and its static safety tests pass.
4. Before a future device boot, restate this hypothesis and the exact installed
   full-partition identity. Select only logical `boot2`; do not request CPU8/9
   or touch regulator, reset, watchdog, memory, or storage interfaces.
5. Before reboot, arm the independent post-return pstore collector. Also arm
   the once-only USB watcher; it can add only the exact direct-link host
   address when local passwordless sudo has already been authenticated:

   ```sh
   experiments/2026-07-22-cortex-a72-observer-initcall-diagnostic/scripts/collect-cycle.sh \
     --output artifacts/runtime-captures/NEW_PRIVATE_CAPTURE \
     --wait-seconds 600 --configure-address
   ```

   The watcher discovers the interface by exact fixed MAC, requires a unique
   `10.15.19.1/24` and exact route to `10.15.19.82`, persists pre-connection
   failures, and makes no TCP readiness probe. It invokes the following
   collector exactly once so the validation session is the sole connection:

   ```sh
   experiments/2026-07-22-cortex-a72-observer-initcall-diagnostic/scripts/collect-runtime.sh \
     --interface IFACE --output NEW_PRIVATE_CAPTURE
   ```

   The collector waits until uptime 45 seconds when necessary, takes two
   read-only state and raw per-CPU `/proc/stat` samples five seconds apart,
   captures dmesg, and immediately runs the runtime validator.
6. Preserve the validated evidence before using the already-proven native
   reboot path. Reboot behavior is inherited and is not AF's causal result.

The decision oracle is predeclared:

| Result | Decision |
| --- | --- |
| Exact AF survives beyond 45 seconds and both samples share one boot ID; `/proc/cmdline` has the exact blacklist token; dmesg has exactly one `initcall mt6797_a72_power_driver_init blacklisted`; CPUs 0--7 remain online, are the exact per-CPU `/proc/stat` IDs, and every counter sum advances; CPU8/9 remain offline; the observer device is unbound and its driver/sysfs ABI is absent; the independent DA9211 initcall returns success and I2C6 plus DA9214/BUCKA/BUCKB remain bound, with each regulator class device linked to the exact DA9214 I2C client; no watchdog fd or fault appears | `PASS`: observer initcall removal is sufficient to recover this one AF runtime while prerequisites remain. Keep CPU8/9 blocked, preserve AF evidence, and audit AE observer registration/probe before any active A72 work. Because AE lacked exact post-LK runtime attribution, record this as strong isolation evidence, not sole proof that the observer caused the earlier return. |
| Exact AF is captured, the blacklist token is live, observer sysfs is absent, but AF faults or resets before the stability boundary | `FAIL`: observer registration/probe is not sufficient to explain the failure. Investigate the shared AE patch/DT/regulator foundation; do not request CPU8/9. |
| Observer sysfs or a successful observer probe appears despite the token | `INVALID`: blacklist isolation failed; correct the exact initcall name/configuration before another device cycle. |
| I2C6, DA9214, or either regulator child is absent/unbound | `INVALID`: AF did not retain the intended AE prerequisite foundation, so the result cannot isolate the observer. |
| No exact AF USB identity or durable AF evidence is obtained | `INCONCLUSIVE`: selection, early boot, and observation failure remain conflated. Do not infer observer causality or repeat unchanged AF. |

## Observations

Two independent AF kernel packages passed the exact AE baseline validator and
matched in every non-timestamp byte and every file mode after normalizing only
`generated_utc`. The resolved config SHA-256 is
`bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63`;
`Image.gz` is
`b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912`;
and the DTB remains byte-exact AE at
`3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b`.

Two independent Android-v0 constructions contain 17 byte- and mode-identical
members. The 7,385,088-byte raw image is SHA-256
`fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3`;
its exact 16 MiB zero-padded form is
`832965fbf6c9c056d7bcace238e3895dd206fa7e21e0d3bb2636466a6d073588`.
The artifact manifest is
`77e311af022e067185b9c9462137cfb73bb639ef0f29d9eb946d326097636e22`.
See the [build reproduction record](results/build-reproduction-af-20260722.txt).

The scaffold passed Bash syntax, Python AST/help, JSON, diff-whitespace, and
recovery-VM ShellCheck validation. Synthetic runtime tests accepted the exact
pass fixture and rejected duplicate/out-of-order markers, a stalled CPU,
cross-parent regulator attribution, and provenance mutations.

The exact AE-derived AF installer is mode `0700`, SHA-256
`d37b0744020320ea95636fb32beff421a05ae79cd6bf2016ec179bfb1d2253a5`,
and passed all 64 storage-safety, lineage, and publication rejection scenarios
plus an independent read-only storage-safety review. Of those scenarios, 57
change possible runtime behavior, five are comment-only exactness tests, one
rejects a symlink foundation, and one proves exclusive publication. See the
[installer validation record](results/installer-validation-af-20260722.txt).

On the named Gemini, the guarded workflow resolved logical `boot2` from the
live GPT as inactive, unmounted `/dev/mmcblk0p30`, preserved a private full
backup with exact AE SHA-256
`0e7cc17ce214f3904bae7172c81e50327ffda19fa46601c76bac36232b1079a9`,
wrote only the exact 16 MiB AF image, synced and flushed it, and required a
full byte-for-byte local readback at
`832965fbf6c9c056d7bcace238e3895dd206fa7e21e0d3bb2636466a6d073588`.
External power was online, the battery was present/full/healthy at 100%, the
root and boot IDs stayed fixed, remote staging was removed, and no reboot or
slot selection occurred. See the
[boot2 write record](results/boot2-write-candidate-af-20260722.txt). AF is
installed and its first runtime attempt is recorded below.

The owner selected logical `boot2` for AF attempt 1. After LK, the panel became
uniform grey but displayed no console text or shell. The dwell duration is
unknown, the keyboard could not be tested, and the owner forced a return to
Gemian; no automatic AF reset is claimed. Because the once-only USB collector
had not been armed, no exact AF USB identity was captured. A read-only
post-return collection found an available but empty pstore: no
`console-ramoops`, kernel identity, initramfs marker, or watchdog-pretimeout
record. The known-good return reports `boot_reason=4` and
`androidboot.bootreason=wdt_by_pass_pwk`, which is consistent with the stated
forced return but cannot attribute an AF kernel stage. Logical `boot2` still
has the exact AF full-partition SHA-256 after the cycle. See the
[attempt-1 runtime record](results/runtime-candidate-af-attempt-1-20260722.txt).

## Analysis

The reproducible build establishes the intended exact-AE-plus-blacklist input
and deterministic container, not a working AF boot. The blacklist string in an
image, an empty post-return pstore capture, or the mere absence of observer
sysfs does not establish a working AF boot.
The pass gate requires the exact live forced command line, the exact observer
initcall-blacklist dmesg line, stable USB sessions, unchanged eight-CPU
accounting IDs and advancing sums from `/proc/stat`, an independently
successful DA9211 initcall, exact regulator-to-DA9214 parent links, and retained
I2C6/DA9214 bindings, plus absence of fault and watchdog ownership together.

## Conclusion

`inconclusive`: Candidate AF was reproducibly built, installed, and selected,
but attempt 1 produced only a non-unique grey display before an owner-forced
return. There is no exact live AF identity or durable mainline log from which
to infer whether the observer blacklist succeeded or where boot stopped.

The post-attempt static DT audit found a concrete console-path regression.
Hardware-passed AD's final DTB, SHA-256
`bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`,
contains `/chosen/framebuffer@7dfb0000` with the proven 1080×2160,
4352-byte-stride, `a8r8g8b8` geometry and both retained clocks. AF's exact DTB,
SHA-256
`3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b`,
has no child under `/chosen`: the AE artifact builder selected the raw package
DTB and silently dropped AD's artifact-level simplefb transformation, which AF
then inherited. That omission explains the absent fbcon text without proving
that AF's kernel hung or failed to reach `/init`; the USB path was not observed.

## Follow-up

Do not repeat exact AF. The newly established missing-prerequisite fact
supersedes the earlier raw-beacon sketch: make AG byte-exact AF for kernel,
config, initramfs, command line, blacklist, CPU policy, and every non-display
DT property, while restoring only AD's exact proven `/chosen` simplefb
contract and its two path-resolved clocks. Never add LK's runtime framebuffer
reservation statically and perform no raw framebuffer write. Arm an AG-specific
once-only USB watcher and the independent post-return pstore collector before
that cycle. If the restored console and USB path still supply no attributable
evidence, then stop and choose early kernel or LK/UART instrumentation. Do not
proceed to an active Cortex-A72 power sequence until the boot boundary is
attributable.
