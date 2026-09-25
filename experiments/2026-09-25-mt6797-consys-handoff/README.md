# Passive CONSYS shared-handoff snapshot

Status: validated offline boot image and guarded installer prepared; no device
installation or runtime result exists yet. The previous [authenticated status boot](../2026-09-25-mt6797-consys-status/README.md)
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
passed; no installer command has run on the PDA. The [session binding](session.py)
and [host runner](host.py) retain the authenticated USB observation, complete
log preservation and reviewed native Gemian return flow. Their one-shot live
session will require a fresh verified deployment receipt and a new mainline
boot identity; it is not armed yet.
