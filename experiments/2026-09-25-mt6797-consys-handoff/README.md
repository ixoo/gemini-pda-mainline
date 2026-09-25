# Passive CONSYS shared-handoff snapshot

Status: source candidate only. No package, boot image, device installation or
runtime result exists yet. The previous [authenticated status boot](../2026-09-25-mt6797-consys-status/README.md)
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
