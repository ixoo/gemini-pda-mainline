# Experiment: restore the proven simplefb observation path

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-22-simplefb-observation-restoration` |
| Status | `Candidate AG selected once; grey/no-text stall and owner-forced return; no attributable kernel stage` |
| Subsystem | LK-to-Linux display handoff, simple-framebuffer, fbcon, USB observability, boot-time SMP |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-22 |
| Investigator(s) | Project maintainers |
| Candidate | `AG` |

## Question or hypothesis

Will byte-exact Candidate AF reach an attributable, stable eight-Cortex-A53
runtime when its final DT is changed only to restore the exact simplefb
observation contract that already passed on Candidate AD?

AF attempt 1 reached a uniform grey panel after LK, but produced neither text
nor an exact USB session before the owner forced a return to Gemian. Its empty
post-return pstore cannot distinguish an early kernel failure from a working
but invisible shell. A later byte-level audit found a concrete prerequisite
regression: hardware-passed AD's final artifact DT contains
`/chosen/framebuffer@7dfb0000`; exact AF has no child below `/chosen` because
the AE/AF artifact lineage selected the raw package DT and omitted AD's
artifact-level transform.

AG isolates that omission. It retains AF's byte-exact `Image.gz`, resolved
configuration, `System.map`, initramfs, helpers, forced command line, A72
observer-initcall blacklist, and rejecting CPU8/9 enable method. It retains
every AF DT semantic except the following exact hardware-passed AD contract:

- `/chosen/#address-cells = <2>`;
- `/chosen/#size-cells = <2>`;
- an empty `/chosen/ranges`;
- one direct `/chosen/framebuffer@7dfb0000` child with only `compatible =
  "simple-framebuffer"`, `reg = <0 0x7dfb0000 0 0x01f90000>`, width 1080,
  height 2160, stride 4352, format `a8r8g8b8`, and the path-resolved AF
  infracfg clock 45 followed by topckgen clock 6.

This artifact-only branch supersedes the earlier raw-framebuffer-beacon sketch.
The missing DT prerequisite is a smaller and already hardware-passed change;
writing pixels from the kernel would add a new side effect without proving
that simplefb, fbcon, the initramfs shell, or USB reached their intended states.
AG contains no raw framebuffer write.

## Provenance and environment

- Kernel release and profile: byte-exact Candidate AF Linux `7.1.3`, profile
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist`.
- Exact AF Android-v0 SHA-256:
  `fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3`.
- Exact AF `Image.gz` SHA-256:
  `b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912`.
- Exact AF resolved configuration SHA-256:
  `bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63`.
- Exact AF `System.map` SHA-256:
  `a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d`.
- Exact AF DTB SHA-256:
  `3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b`.
- Exact AF/AD initramfs SHA-256:
  `166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
- Hardware-passed AD DT oracle SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`.
- Reproduced AG DTB SHA-256:
  `7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512`.
- Reproduced 7,387,136-byte raw AG Android-v0 SHA-256:
  `0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91`.
- Reproduced 18-member artifact manifest SHA-256:
  `e40e6c262a461b7514ea8a1388d3a544c6fa88a4bc0cbadf969e9da75facf95c`.
- Exact 16 MiB zero-padded AG SHA-256:
  `63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14`.
- Build environment: repository recovery VM. No kernel build was performed;
  the candidate is a deterministic artifact/DT transform from exact AF and AD
  evidence.

No kernel patch, configuration fragment, `patches/series` entry, or
`kernel/manifest.json` profile changes for AG. “Candidate AG” denotes the exact
validated artifact above, not a newest-by-timestamp file.

## Safety assessment

The builder and validators access no device. They reject all semantic DT
changes beyond the allowlist, phandle renumbering or duplication, extra
simplefb properties or children, a `memory-region` reference, and any static
`mediatek,framebuffer` node or reserved-memory overlap with
`[0x7dfb0000, 0x7ff40000)`. The visible 0x008f7000-byte span fits inside the
0x01f90000-byte resource, whose end remains immediately below the dynamic ATF
log boundary.

LK dynamically injects `/reserved-memory/mblock-3-framebuffer` into the live
tree. AG must not add that node statically: doing so would duplicate loader
ownership and would no longer be the proven AD artifact contract.

AG keeps `maxcpus=8`; CPUs 0--7 are the hardware-passed Cortex-A53s, while
CPU8/9 remain offline behind the rejecting `mediatek,mt6797-psci` method. It
adds no `CPU_ON`, regulator, reset, watchdog, raw-memory, or storage action.
Normal inherited kernel initialization is not claimed to be read-only.

Any later install is a separate, guarded operation under the standing logical
`boot2` authorization. It must resolve `boot2` from the live GPT, prove it is
inactive and unmounted, preserve a private full backup, pad to the exact target
size, sync and flush, and require a matching full-partition readback. The
runtime collector is read-only and never opens the watchdog or writes CPU,
clock, regulator, reset, framebuffer, memory, or storage interfaces.

## Associated code

- `scripts/build-simplefb-dtb.sh`: reconstructs the exact AF-plus-AD simplefb
  DT transform, resolving both clock providers by path.
- `scripts/validate-dtb-delta.py`: whole-FDT semantic allowlist, exact oracle,
  geometry, phandle, and static-reservation checks.
- `scripts/test-dtb-validator.py`: one positive fixture and 24 focused invalid
  DT mutations.
- `scripts/validate-lineage.py`: exact AF/AD artifact inventory, hash, mode,
  config, symbol, initramfs, and helper lineage.
- `scripts/build-candidate-ag.sh`: two-pass deterministic DT and Android-v0
  construction without a kernel build or device access.
- `scripts/validate-boot.py`: exact AF payload lineage, canonical Android-v0
  header, and trailing-FDT rejection.
- `scripts/validate-artifact-reproduction.py`: byte-and-mode identity for two
  independent 18-member AG artifacts.
- `scripts/collect-runtime.sh`: bounded read-only AG collection after 45
  seconds plus a five-second stability sample.
- `scripts/collect-cycle.sh`: once-only exact-USB host watcher.
- `scripts/validate-runtime.py`: exact live chosen/simplefb/LK reservation,
  framebuffer, USB, CPU, blacklist, retained DA9214, watchdog, and fault gates.
- `scripts/test-runtime-validator.py`: one exact synthetic runtime fixture and
  15 focused identity, DT, binding, clock, CPU, marker, and chronology rejects.
- `scripts/test-collect-cycle-no-interface.sh`: bounded mocked-host watcher
  check proving that an absent exact-MAC interface invokes the collector zero
  times, preserves a failed status record, and attributes an investigator TERM
  stop as exit 143 rather than a successful exit.
- `scripts/derive-installer.py`: source-pinned, narrow AF-installer derivation
  for the exact AG raw and padded identities; it produces no installer unless
  given an explicit output and performs no device action.
- `scripts/test-installer-derivation.py`: inherited AF storage-safety suite plus
  AG-specific lineage, hash, target, write-boundary, and publication rejects.

## Procedure

1. Validate two independent exact AF artifact roots and two independent exact
   AD oracle roots. Build AG once from each pair in separate output parents.
2. Require the two AG trees to be byte- and mode-identical. Require the DT
   positive fixture and all 24 focused negative mutations to pass.
3. Before any device cycle, record the exact raw and 16 MiB padded identities
   above. Arm the independent post-return pstore collector and the AG-specific
   once-only USB watcher. Supply the padded checksum only from the preceding
   guarded full-partition readback; the watcher records that host attestation
   and deliberately does not read a device partition:

   ```sh
   experiments/2026-07-22-simplefb-observation-restoration/scripts/collect-cycle.sh \
     --output artifacts/runtime-captures/NEW_PRIVATE_CAPTURE \
     --installed-full-sha256 \
       63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14 \
     --wait-seconds 600 --configure-address
   ```
4. The recorded guarded installation targeted only live-GPT logical `boot2`
   and did not reboot or select a boot entry. Any future reconstruction must
   repeat all predecessor, power, inactive-target, backup, flush, and full
   readback gates rather than relying on a fixed partition number.
5. Select logical `boot2` once. A visible console is useful independent
   evidence but is never sufficient for `PASS`. The USB collector must reach
   the exact AG service, wait until uptime 45 seconds, sample all state twice
   five seconds apart, and require the exact prior-readback hash attestation.
6. Preserve all evidence before issuing any manual reboot. Do not repeat an
   identical artifact if the first cycle lacks a decision-changing observation.

The predeclared decision oracle is:

| Result | Decision |
| --- | --- |
| Exact AG USB identity and exact prior-readback hash attestation pass; one boot ID survives the 45+5-second interval; the exact live chosen simplefb node, LK-injected no-map reservation, `simple-framebuffer` binding, fb0 geometry, AF blacklist/DA9214 foundation, eight advancing CPU0--7 counters, offline CPU8/9, and no simplefb clock error, fault, or watchdog owner all pass | `PASS`: the missing simplefb contract is restored and AF's otherwise exact runtime is attributable. Preserve the evidence before deciding whether observer isolation is sufficient for later A72 work. |
| The exact chosen node is absent or differs, or the prior-readback attestation/USB identity is not AG | `INVALID`: the intended candidate or loader contract was not observed. Correct lineage; do not interpret kernel behavior. |
| The chosen and LK reservation contracts are exact, but simplefb/fb0 does not bind or reports a clock/resource/probe error | `FAIL`: the restored DT description is insufficient for the display path. Preserve logs and stop; do not add a raw-write beacon as an unmeasured substitute. |
| The console becomes visible but exact USB validation is absent | `PARTIAL/INCONCLUSIVE`: this supports display restoration only; it does not establish the stability, CPU, blacklist, or watchdog gates. |
| No exact AG evidence is captured, or the device returns before the stability boundary without attributable logs | `INCONCLUSIVE`: boot selection, early failure, and observation failure remain conflated. Do not repeat unchanged AG. |

## Observations

Two independent recovery-VM constructions produced byte- and mode-identical
18-member artifacts. Both emitted the exact DTB and raw image identities above;
both manifests have the exact identity above, and the artifact reproduction
validator passed. Independently padded build outputs matched across the exact
9,390,080-byte zero tail. The DT validator accepted the single intended
transform and rejected all 24 focused mutations. No kernel was built and no
device was contacted. See the
[build reproduction record](results/build-reproduction-ag-20260722.txt).

The guarded installer later resolved live-GPT logical `boot2` as inactive,
unmounted `/dev/mmcblk0p30` while the known-good root was
`/dev/mmcblk0p29`. With AC online and a present, full, healthy battery at 100%,
it preserved a private exact-AF full backup, wrote only the exact 16 MiB padded
AG image, synced and flushed, and required three matching full-partition
checks: the device post-flush checksum, a 16,777,216-byte local readback, and an
independent remote checksum all equal
`63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14`.
Remote staging was removed. The installer did not reboot or select a boot
entry. See the [guarded write/readback record](results/boot2-write-candidate-ag-20260722.txt).

The static AF/AD comparison establishes that the simplefb description is
present in hardware-passed AD and absent from AF. It does not establish that
AG boots, binds simplefb, reaches `/init`, exposes USB, or remains stable.

A read-only preflight on the named device's known-good Gemian runtime confirmed
LK's dynamic reservation independently of AG: the live
`mblock-3-framebuffer` node contains exactly the direct entries `compatible`,
`name`, `no-map`, and `reg`; their values are the expected MediaTek framebuffer
string, node-name string, empty no-map property, and
`<0 0x7dfb0000 0 0x01f90000>`. This direct, high-confidence observation
calibrates the AG live-tree gate but does not test AG. See the
[LK reservation preflight](results/live-lk-framebuffer-reservation-preflight-20260722.txt).

The exact runtime synthetic fixture passed and 15 focused mutations were
rejected. The mocked no-interface watcher passed twice on the macOS host after
a two-second deterministic boundary, preserving failure status with zero
collector invocations. The watcher is intentionally macOS-specific
(`ioreg`, BSD `stat`, `ifconfig`, and `route` contracts), so it was not
functionally executed in the Linux recovery VM; recovery-VM validation used
ShellCheck, while the runtime and DT validators passed their 15/15 and 24/24
fixture suites there. These tests contacted no device.

The exact installer derivation passed all 64 inherited AF safety, lineage, and
publication rejects plus 42 AG-specific rejects, Bash syntax, and recovery-VM
ShellCheck. A mode-0700 production instance was generated only below the
Git-ignored private artifact tree and then performed the guarded write recorded
above; the derivation and test stages themselves contacted no device.

Attempt 1 was armed with both the exact-MAC USB watcher and the independent
wait-for-cycle pstore collector before the known-good OS was remotely rebooted.
The device remained disconnected and returned to known-good Linux `3.18.41+`
with a changed boot ID about 117 seconds later. No exact AG USB MAC appeared,
the USB collector was never invoked, and no runtime capture exists. Pstore
contained `console-ramoops` and `pmsg-ramoops-0`, but neither contained the AG
kernel identity, initramfs marker, observability marker, panic, fault, or
watchdog-pretimeout event; the console record contained only the orderly
pre-cycle Gemian shutdown. A private mode-0600 `last_kmsg` likewise contains no
AG or Linux 7.1.3 identity. Logical `boot2` still has the exact installed AG
checksum after the return. See the
[attempt 1 runtime record](results/runtime-candidate-ag-attempt-1-20260722.txt).

The owner subsequently confirmed selecting `boot2`. After LK, the display
became a grey console screen but contained no text, shell, or keyboard-testing
opportunity. The device did not reboot automatically; the owner forced the
return. This removes missed LK selection from the leading alternatives, but
the grey frame is not an attributable AG marker and still cannot distinguish a
stall before Linux entry from a stall before normal ramoops, console, or USB
became usable. The watcher was stopped after the known-good reconnect; that
exposed a bookkeeping bug which recorded exit zero for an investigator TERM.
Explicit INT/TERM traps and a mocked regression check now preserve exit
130/143. This does not upgrade the attempt to a kernel-stage observation.

## Analysis

AG is attributable because it changes the one missing observation prerequisite
while preserving AF's kernel behavior and CPU isolation byte-for-byte. A panel
change alone remains ambiguous: LK can alter the framebuffer before Linux, and
a simplefb node can exist without both clocks enabling or fb0 binding. The live
validator therefore requires the loader-injected reservation, platform-driver
binding, exact fb0 geometry, absence of clock/probe errors, USB stability, and
the inherited AF CPU/blacklist foundation together.

Attempt 1 did not cross that attribution boundary. Its reset-reason tokens are
also non-decisive because both the pre-cycle known-good restart path and the
owner-forced recovery can produce the same values. The owner confirmation now
establishes selection, but repeating the identical image would still reproduce
the same unlocated pre-console/pre-USB boundary without a new measurement.

## Conclusion

`runtime inconclusive`: the Candidate AG artifact boundary is reproducible, its
DT semantic delta is exact, and guarded logical-`boot2` installation plus full
readback passed. The owner confirmed one `boot2` selection, a grey/no-text
display state, and a forced return, but no attributable AG kernel or initramfs
stage was captured. No boot or hardware-support claim follows.

## Follow-up

Do not repeat unchanged AG. Move the next observation point earlier than
normal ramoops/console/USB, or use a component split against exact
hardware-passed AD whose result changes the next action even when the display
remains non-attributable. Update hardware support only after a named-device
pass; do not begin an active Cortex-A72 power sequence from this inconclusive
result.
