# Shared baseline verifier preparation evidence

Status: offline component implemented; dependent packets remain preparing.
This bounded item follows the validated baseline handoff at
`ecb3436c1fb0f471a10bc0d23318a6dea14ca7cf`. It changes no baseline target,
candidate, hardware protocol, physical admission or action budget. There was
no additional build, candidate retest, device connection or credential access.

## Dependency removed

The staged keyboard and eMMC launchers needed to verify the same completed
first-baseline/recovery prerequisite. Keyboard held a private archive verifier;
eMMC separately implemented final-confirmation verification and modeled the
baseline finishing preparation in its fixtures. The shared
[verifier contract](VERIFIED_BASELINE.md) provides one credential-free raw
archive verification interface. It returns snapshot-derived admission and
deployment hashes so a caller can compare its independently prepared inputs.

| Source | SHA-256 |
| --- | --- |
| `scripts/verified_baseline.py` | `ba70f6df476283c0113d433ae856940cc9c031f864019da95f014324e16c926e` |
| `scripts/test-verified-baseline.py` | `857b370594f9c82b983ceeb1f7e43a4d87f5c53946659a89e8f1c8b3f33888b3` |

The component pins its complete seven-file production source closure: the
baseline collector, finishing helper, session parsers, deployment adapter,
historical PWRAP observer/classifier and V4 deployment receipt parser.
It imports no keyboard implementation or fixture into production verification.

## Review and tests

Independent extraction review found a privacy race: an initial single-link
check was followed by the finishing helper's snapshot reader, which did not
check the link count. A deterministic mutation introduced an outside hardlink
between those operations and still obtained a verified result. The
implementation at `e9ad2eede401173a7609566dd32dfae637596d66` retained bytes read
through descriptors that enforce file type, owner, mode, single-link count and
size, and required those exact bytes to match
the manifest-verified snapshot. That earlier mutation refused, but a later
integration review found a narrower race within the bounded read itself.

The integration reviewer added an outside hardlink after the initial
descriptor metadata sample for the original attempt's `result.json`. The
unchanged captured bytes still passed verification while the link persisted.
A deterministic local regression reproduced that acceptance against `e9ad2eed`.
The correction samples the same still-open descriptor again after reading and
requires device/inode, type/mode, owner/group, link count and size to equal the
validated first sample, with captured length equal to both sampled sizes.
Existing manifest/digest and retained-snapshot comparisons remain in place.

Three new methods inject persistent hardlink, mode and size changes after the
actual stream read returns its unchanged bytes but before the bounded reader
returns. Each covers original, authentication and confirmation result files.
All nine cases now refuse immediately at the metadata comparison. Before this
correction, the original hardlink case was accepted; other cases could refuse
later inventory or checksum checks. The measured before/after checks do not
prove that all transient filesystem mutations are absent or that metadata
cannot change after verification.

All 24 shared-verifier methods passed in normal and optimized Python after the
correction. The original 21 methods had passed in both modes at `e9ad2eed`.
Independent correction review found no actionable defect and reran the positive
archive method plus the three new regression methods successfully.
The full positive archive test forbids credential/image reads, file writes,
sockets and subprocess creation during verification. Refusal cases include
external anchor mismatches, source drift before import, changed claims and
commands, forged stored passes, malformed process records, missing phases,
partial or late-terminal logs, emergency recovery, unchanged recovery IDs,
symlinks, hardlinks and evidence replacement races. Synthetic archives use the
actual baseline command generators, classifiers and receipt parsers.

The common repository gate passed with all 189 profiles in this worktree.
Its Linux-only provenance fixture was skipped on macOS. This host-only item
does not change build or artifact inputs and requires no new kernel build,
DT/schema test or hardware run. Actual baseline and recovery evidence remain
future prerequisites for either dependent packet.

## Private packet integration checkpoint

The following historical checkpoint used the initial `e9ad2eed` verifier
digest `dc60a0778c7fc1a937e880cf2c0c01fd218837728715dee69d419c7792741a86`.
Both ignored packet drafts pinned that source. Adoption of the corrected
digest requires updating and rechecking those draft pins; they remain disabled.
The keyboard draft replaced its duplicate archive parser with a 49-line pinned
adapter; 25 launcher and 19 archive methods passed normally and with Python
optimization enabled. No keyboard protocol or supervisor implementation changed.
Its private staging manifest is
`a93d6a7ac4956ec20b68e678c18877312705e8a4d84a0f48a36fe7e0aac32ec0`.

The eMMC draft removed its separate confirmation reader and modeled finishing
preparation. Its 17 launcher methods now exercise the actual shared verifier
against full synthetic raw archives. Only the separate collector preparation
boundary for candidate files and credentials is substituted in these fixtures.
The launcher compares snapshot-derived admission, deployment and candidate
hashes, original admission UUID and original known-good boot ID with that same
prepared context, then uses verifier-returned IDs directly. Substituting raw
inputs after preparation, altering confirmation evidence, or changing the
verifier source refuses. The tracked verifier path is preferred; a fixed
private fallback is allowed only inside the approved draft staging directory
and only with the same source digest.

All 17 launcher and 20 completion methods passed normally and with optimization
against the shared source at its intended repository path. Independent review
found no concrete join or source-resolution gap and reran all 17 launcher
methods successfully. The private staging manifest is
`95b80ccd83e9364a026693a8af1d22c4380d402ff237e13c5068406c816bfe92`.

These private integration checkpoints remain preparing with execution disabled
and runtime facts unset. Their source and receipts remain under ignored
`artifacts/a53-authenticated/development/`. Keyboard metadata, reader exclusion,
supervisor delivery and exact ARM64 supervision remain separate pending work;
the new eMMC launcher guards still need exact-shell integration checks. No
first-baseline prerequisite, candidate byte or device budget changed.
