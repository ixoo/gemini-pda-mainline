# Experiment: one-shot physical CPU8 admission candidate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-cpu8-admission-candidate` |
| Status | `running` |
| Subsystem | arm64 CPU hotplug, MediaTek MT6797 power sequencing, Device Tree |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |

## Question or hypothesis

Can the hardware-free-proven one-shot admission controller bring CPU8 online
on the named Gemini, or produce a retained stage that identifies the first
remaining physical failure, without touching CPU9 or retrying?

## Provenance and environment

- Parent patch tail: `0412`, exact hashes in `contract.json`.
- Prepared source: exact post-`0412` Buildbox state and integrity in the contract.
- Build backend: Buildbox only; no native VM build.
- Boot path: a separately validated Android boot-v0 image, logical `boot2` only.
- Candidate identity: exact Buildbox package and independently validated LK image
  are pinned in `contract.json` and the result records.

## Safety assessment

The current source-definition and generator phase is hardware-free. The later
one-boot phase uses the repository's standing boot2 procedure: resolve the
live GPT, require the inactive/unmounted exact partition and stable power,
verify full readback, then shut down. It never writes another partition and
does not create a redundant backup.

## Associated code

- `kernel/`: exact binding and DTS templates.
- `scripts/source_edits.py`: deterministic post-`0412` source edits.
- `scripts/validate_source.py`: graph and driver/binding contract checks.
- `scripts/generate-patches.py`: isolated two-commit format-patch generator.
- `scripts/generate-on-buildbox`: source-state and integrity-pinned Buildbox entry.
- `scripts/validate.py`: local definition validation.
- `scripts/build-candidate.sh`: hash-pinned deterministic LK assembly.
- `scripts/validate-candidate.py`: independent package, binary-DTB, and LK validator.
- `scripts/install-boot2.sh`: live-GPT/TEE/ledger/power/readback/shutdown gates.
- `scripts/initialize-transition-ledger.sh`: exact two-u32 logical-empty repair.
- `scripts/collect-runtime.sh`: pre-armed USB/netcat attempt-1 collector.
- `scripts/remote-live-probe.sh`: bounded read-only CPU and ledger probe.
- `scripts/validate-runtime.py`: exact success/rejection/failure decision map.

## Procedure

1. Validate, sign, and push this source definition with a clean worktree.
2. Generate the binding/DTS patch pair against the exact prepared Buildbox tree.
3. Review and integrate the patches, then add a production-only profile whose
   complete series is a canonical subsequence.
4. Commit and push cleanly; build the exact profile with `--backend buildbox`.
5. Fetch only the validated package and assemble one exact LK boot2 candidate.
6. If every package, DT, config, container, target, and power gate passes,
   install boot2, verify full readback, and shut down for physical selection.
7. Perform one boot and classify it only from runtime or retained evidence.

## Observations

The hardware-free controller has already passed two no-network KUnit suites,
10 tests total, with zero failures or skips. Buildbox generated the `0413/0414`
binding/DTS pair against the exact post-`0412` prepared source; strict
checkpatch, semantic validation, and fresh replay passed. The byte-reviewed
patches and production-only `a72-admission-candidate` profile are integrated.
The first production build stopped before compilation because the final config
did not retain two pure derived-admission prerequisites; enabling those exact
prerequisites produced a clean-source Buildbox package at commit `c5b5cd6e`.
All package hashes, production config gates, linked symbols, and the compiled
DT ownership graph passed independent checks. Deterministic assembly with the
runtime-proven serviceability ramdisk produced raw candidate `d52d3c4e...` and
16 MiB padded image `fde53dca...`; a separately implemented validator passed
all 32 LK gates and the binary-DTB graph. The guarded installer and bounded
runtime path are also materialized: transition-ledger preflight and all three
serviceable runtime outcomes passed self-tests, including rejection of CPU9
online. The first read-only live preflight found the known pstore signature
with stale `start=size=130`, which the transition ledger would reject before a
CPU request. The frozen initializer performed exactly two retained u32 writes,
changing only those words to zero; independent readback validated the ledger as
logical-empty. Every live GPT, inactive/unmounted target, TEE identity, power,
size, and ledger gate then passed. The installer wrote candidate `fde53dca...`
to live-resolved logical `boot2` (`/dev/mmcblk0p30`, with root on `p29`) and the
full-partition readback matched exactly. No fresh backup was created. Shutdown
was confirmed by SSH loss and three consecutive TCP/22 closures. No physical
boot of this candidate has occurred yet.

## Analysis

The exact package and LK candidate are validated, and the guarded deployment
has crossed the reproducibility boundary without crossing the physical-boot
boundary. The remaining boundary is one guarded physical boot. Success requires
the exact kernel identity, CPU online list `0-8`, CPU9 offline, and the
one-request admission record. A failure is useful only if the exact retained
transition ledger identifies the last complete stage; screen color or reboot
behavior alone is serviceability evidence.

## Conclusion

Inconclusive for hardware. The exact image remains `boot_candidate=true`, is
fully readback-verified on logical `boot2`, and the device is shut down awaiting
one physical selection; CPU8 support is not claimed.

## Follow-up

Pre-arm the bounded USB/netcat collector. Spend exactly one physical boot and
classify it from exact runtime or retained evidence; do not repeat an identical
image without a new independent observation path.
