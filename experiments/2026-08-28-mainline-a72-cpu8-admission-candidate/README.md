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
- Candidate identity: pending patch generation, integration, build, and LK validation.

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
10 tests total, with zero failures or skips. This experiment has made no device
request, build, installation, or boot yet.

## Analysis

The missing boundary is now narrow: a schema-validated candidate DT and a
production profile must connect already-proven suppliers to the controller.
Compile success will validate that graph but will not establish CPU8 support.

## Conclusion

Inconclusive for hardware. The definition is awaiting exact Buildbox patch
generation; `boot_candidate=false` until all later gates pass.

## Follow-up

Integrate only byte-reviewed generated patches, then perform the smallest exact
Buildbox device-profile build. Do not spend the one physical boot on a
configuration-identical or marker-only derivative.
