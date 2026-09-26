# Passive CONSYS shared-handoff snapshot

Status: one guarded boot2 installation and clean shutdown, an authenticated
mainline observation with a complete log, and a verified changed-boot Gemian
return. The shared handoff was unprotected and the common remap was disabled;
Wi-Fi remains unimplemented. The previous [authenticated status boot](../2026-09-25-mt6797-consys-status/README.md)
found CONN off in both SPM status registers and logged the boot's allocated
2 MiB no-map CONSYS reservation. It did not show the shared remap, EMI
selector or CONN bus-protection state. That image's boot budget is consumed.

## One-boot hypothesis and decision

In a new, exact validated A53 RAM image, the already-present infracfg syscon
can report the CONN bus-protection status at `+0x228`, common/WLAN remap at
`+0x340`, and EMI translation selector at `+0xf00` without changing the
hardware. The [observer source](mt6797-consys-handoff.c) reads each register
twice during late init, resolves that same boot's no-map CONSYS reservation
through `of_reserved_mem_lookup()`, and compares only the shared remap's
common low field to the reservation base. It logs the raw remap field,
selector bit 13, protection bits 17/18, six read completions and zero effect
calls. It never reads a powered-off CONSYS IP window, changes a register,
loads firmware or activates radio/DMA.

The unique observation is one `mt6797-consys-handoff` record in a complete,
authenticated kernel log, bound to the new image checksum and boot ID. Pair
it with that boot's `mt6797-consys-status` record and OF reservation line.

- A stable matching enabled remap and both protection bits set, with CONN off,
  support construction of the next separately reviewed shared-owner binding.
  They do not prove exclusive control or authorize a firmware load.
- A stable disabled remap with both protection bits set identifies a different
  cold handoff: the eventual owner must install the mapping under common
  serialization and prove no competing writer before loading firmware.
- An enabled mapping to another base, missing protection, or movement across
  the two reads refuses adoption; investigate the retained handoff before any
  active CONSYS transition.
- An unavailable reservation, syscon or read, a missing status record, or an
  unverified boot identity is inconclusive. Diagnose the path; do not repeat
  an identical image without a decision-changing independent measurement.

The selector value determines which address translation the eventual region-18
secure call would require. A stable selector does not identify its owner or
prove the secure lock and AP/CONSYS domain policy. The gate deliberately leaves
external-writer exclusion, reset attribution, firmware execution, calibration,
station association and traffic unproved.

The named profile `mt6797-a53-consys-handoff-snapshot` retains the tested A53
service and previously built CONN status observer. Only the new read-only
observer is added. Before any boot, Buildbox must compile the exact clean,
pushed inputs; the package and board-tree delta must be checked against the
accepted A53 parent. Installation must use the reviewed live-GPT boot2 guard,
full-partition checksum/readback and clean shutdown. The owner selects boot2
physically; preserve the complete log before reviewed return to Gemian.

## Offline result

Buildbox built and validated commit `2adf4c8df863870e3110590b6b8a35b14babd17e`
for this profile against pinned Linux 7.1.3. The fetched immutable package has
inventory SHA-256 `3f5e1c51069bcd74f5e89529f55ed55e486eff6f1b4d8e7a39d75d33aa273697`
and release `7.1.3-gemini-consys-handoff-snapshot`. Both observer symbols are
linked; `MTK_SCPSYS` remains disabled. The new observer has no compiler warning
in the final Buildbox log. Strict pinned Checkpatch reports zero code findings,
excluding only the internal patch's intentionally absent DCO sign-off and
new-file notice. No Device Tree patch was added.

The [composition recipe](build-candidate.py) verified the package inventory,
decompressed kernel, configuration, required symbols, accepted A53 parent,
47-member RAM archive, LK container, one-property SPM syscon tree delta and
exact 16 MiB partition padding. The board tree is byte-identical to the tested
CONN status candidate; the kernel, init release gate, configuration receipt
and resulting boot image differ. The private boot image has SHA-256
`afc225184c22707de23f8c71c629779724c3fac77ef7c72414bcdfded2ea4412`;
the padded boot2 image has SHA-256
`991144187d3aaed6cdccef8fe890fafa52b80cfb635fe95adc4dcf04025f5333`.
The [sanitized receipt](results/candidate.json) contains hashes and structure
only. The private image contains authentication material and remains ignored
under `artifacts/`.

The [installer adapter](installer.py) generated a candidate-bound script using
the established live-GPT boot2 guard, inactive/root separation, power gate,
full predecessor/readback hashes and clean shutdown. Bash syntax and ShellCheck
passed. The [session binding](session.py) and [host runner](host.py) retain the
authenticated USB observation, complete log preservation and reviewed native
Gemian return flow.

## Guarded installation and attempted observation

In Gemian boot `abf9441d-0903-4e9f-8a67-f5063e85ee7a`, the live GPT selected
inactive boot2, distinct from the root partition. The reviewed block-device
guard passed; external power was present, the battery was 100% and healthy,
and the full predecessor checksum matched the consumed status candidate.
The installer wrote the new padded image once, synced/flushed it, and matched
the complete independent readback to SHA-256
`991144187d3aaed6cdccef8fe890fafa52b80cfb635fe95adc4dcf04025f5333`.
Clean shutdown was requested and the host confirmed Gemian unreachable. The
[sanitized deployment receipt](results/deployment.json) omits device paths and
private raw evidence. The owner had not confirmed physical boot2 selection
for this image during the first bounded 900-second local USB-route watcher, which
[expired without a route](results/collector-window-1.json). It made no device
claim or SSH connection; the private session directory then contained only its
deployment receipt. A subsequent pinned-key Gemian LAN check timed out,
consistent with a powered-off PDA but not proof of its screen state.

The owner then reported selecting boot2. A [second 600-second local watcher](results/collector-window-2.json)
was armed shortly afterward and expired without the `10.15.19.1/24` USB route.
The Mac saw a stable USB device with vendor/product `0x0e8d:0x20ff` and product
string `Unknown`, rather than the candidate's configured
`Gemini-L-Observability` gadget. It exposed no macOS network interface. The
known-good Gemian LAN endpoint also timed out. This host-side observation does
not identify the boot stage or establish that the kernel never started. No
device SSH attempt, authenticated claim or CONSYS runtime result occurred; the
session remained unconsumed. That window began after the owner had selected
boot2, so it could not distinguish a missed early gadget interval from a boot
that never exposed the candidate gadget.

## Authenticated runtime result

For the next attended selection, a watcher began before the owner selected
boot2. The Mac first saw the `Unknown` USB identity, then no device, then the
candidate's `Gemini-L-Observability` gadget and its direct network route. The
authenticated session consumed its one claim, preserved the complete 127,086
byte kernel log through an explicit seal, and confirmed return to a new Gemian
boot. The [sanitized runtime result](results/runtime-20260926.json) binds the
candidate checksum, both boot IDs and the log digest; private raw captures
remain under ignored `artifacts/`.

The same mainline boot logged CONN power off in both SPM status registers and
resolved the 2 MiB no-map CONSYS reservation at `0xbfa00000`. Two stable
handoff samples read CONN bus-protection status bits 17/18 as clear, common
remap register `0x180e0000` with its common-enable bit clear, and EMI selector
bit 13 set. The reservation would require common remap field `0x1bfa` if
enabled. All power, reset, remap-write, protection-write, firmware, radio and
DMA counters stayed zero. The observer classified the state `unprotected`;
that classification takes precedence over the separately observed disabled
remap.

This is a refusal to adopt the handoff as an already owned/ready shared
resource. It does not prove that the two clear protection bits are erroneous
for a cold, powered-off CONN island. The next shared owner must establish the
actual writer exclusion and a safe serialized protection/remap/power sequence
before any firmware or radio effect. This exact candidate's observation budget
is consumed; repeating it would not answer those ownership questions.

## Later reported boot2 selection

On 2026-09-26 the owner again reported selecting boot2 while the same image
remained installed. A subsequent 18-sample host-only window from
`12:17:47Z` to `12:19:14Z` saw a stable macOS `Unknown` USB entry and no
mainline USB-network route. Six successful known-good Gemian LAN checks all
returned the same boot ID, `b79541db-5e95-4a02-a32f-87fa18474b38`, as
before the selection. The ignored 4,326-byte host record has SHA-256
`6ec8cd5bef6726bd1e6f95d2ba5d0a026ffb9ceebed5d6ff79df0db4f3b7af7f`.
The host window began after the reported selection, so it cannot establish
which boot stage ran. It yielded no new authenticated mainline log or CONSYS
measurement and does not change the earlier handoff result or justify another
selection of this image.
