# Experiment: minimal MT6797 TOPRGU restart diagnostic

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-06-mt6797-toprgu-minimal-restart` |
| Status | Candidate deployed and readback verified; waiting for owner physical boot2 selection |
| Subsystem | MediaTek watchdog system restart |
| Device variant | Existing named Gemini PDA; retail subvariant unconfirmed |
| Date | 2026-09-06 |

## Question

Can the single hardware-passed MT6797 ordinary-restart result be reproduced
with the narrowest policy delta: set the existing auto-start bit only in the
software-restart path and run TOPRGU at priority 130, while leaving watchdog
start and inherited-watchdog adoption behavior unchanged?

A pass would show that priority 255 and the additional lifecycle mutations in
historical patch 0081 are unnecessary for this ordinary-restart path. A failure
would be inconclusive and would not select either removed behavior for
promotion.

The frozen scope, validation boundary and executable future one-boot decision
table are in [the work item](WORK_ITEM.md). The policy applies SoC-wide to every
MT6797 watchdog match even though any future deployment is limited to the named
Gemini; one unit cannot establish generic upstream policy. Source replay and
Buildbox compilation are complete. Checkpatch reports only the deliberately
absent synthetic-author sign-off, so upstream authorship remains gated. No boot
candidate, device selection or runtime claim exists yet; device readiness and
hardware equivalence remain pending separate gates.

## Offline candidate record

The review artifact is [`0543-watchdog-mtk-minimal-MT6797-restart.patch`](../../patches/v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch).
Its experiment series is [`series-mt6797-toprgu-minimal-restart`](../../patches/series-mt6797-toprgu-minimal-restart),
the profile proposal is [`proposal.json`](proposal.json), and the only new
configuration is the local-version fragment
[`gemini-mt6797-toprgu-minimal-restart.fragment`](../../configs/gemini-mt6797-toprgu-minimal-restart.fragment).

Run `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py` for the static
manifest, canonical-order, patch-shape, inheritance, frozen-chain, and ten
targeted refusal-fixture checks. The result is recorded in
[`results/offline-validation-20260906.txt`](results/offline-validation-20260906.txt).
The validator intentionally checks the frozen parent patch for the retained
restart-path `WDT_MODE_AUTO_START`; it does not claim source replay, a build,
hardware support, or a boot candidate.

## Candidate preparation tooling

The public preparation packet is now frozen in [`session-packet.json`](session-packet.json).
`scripts/build-serviceability-dtb.sh` source-pins the current-tree transformer
and replays it with the new package DT identity; `scripts/validate-dtb.py`
independently checks the serviceability/resource and disabled-action closures.
`scripts/build-candidate.py` and `scripts/validate-candidate.py` compose and
audit the fetched authenticated userspace, fresh provisioned transport files,
and Android-v0/LK payload. Generated candidates remain private below ignored
`artifacts/` and are never installed by these tools.

`scripts/installer.py` source-pins the reviewed installer and derives a private,
candidate- and predecessor-bound guarded boot2 write/readback/shutdown
executable; its default mode only validates that derivation. The derived
installer refuses changed identity, active/mounted/held/swapped targets,
unstable power, size or predecessor mismatches, and retains exactly one write,
flush, independent full readback, then clean shutdown. The completed baseline
installer remains immutable. This active adapter may leave only the exact
observed zero-use, RAM-only zram0 enabled while staging; it rejects every other
swap layout or change, performs no swap operation, and preserves the separate
target/parent active-swap guard. The owner explicitly accepts possible
transient candidate-page residency in volatile zram.

`scripts/session.py` is the pure one-attempt classifier. It admits only the
candidate wrapper whose contract is `busybox reboot -n -f`, after at least 45
seconds of stable idle and a complete pre-action log seal. It requires one
ordered, input- and mainline-boot-bound ramoops marker chain, SSH disconnect
within five seconds, and changed-ID Gemian recovery. `scripts/run-session.py`
is the default-dry-run executable envelope: it source-pins the accepted SSH,
log-seal and recovery components, derives a strict-host recovery collector,
arms that collector before the interactive physical-selection checkpoint, and
owns the single request and final classification. Every post-selection failure
consumes the attempt and permits preservation/recovery only. The offline tests
exercise these refusal and state-machine branches without device, network,
private-key, or boot-image access.

The exact preparation snapshot passed independent Sol Medium integration review
and Astra Medium action-boundary review. The final offline receipt is
[`results/candidate-offline-validation-20260906.txt`](results/candidate-offline-validation-20260906.txt).
This acceptance covers tooling only: private candidate construction, complete
validation against the pinned private inputs, guarded deployment, physical
selection, and runtime behavior remain separate gates.

The first private construction invocation refused a noncanonical supplied DT
identity before composition. The corrected invocation then refused because a
retained exact ELF member's `ioctl` symbol was conservatively mistaken for
effectful script text; no candidate was retained. The repaired classifier scans
executable non-ELF members while exact ELF members remain bound byte-for-byte to
the pinned foundation and userspace. Independent Sol and Astra review accepted
that repair; construction must rerun from its clean published revision.

Clean published revision `8b0e8ff73e8e55b8919a18ed6dd979cc07cb47b0`
then produced two byte-identical candidates and passed the independent validator.
The candidate and locally validated installer identities are recorded in
[`results/candidate-readiness-20260906.txt`](results/candidate-readiness-20260906.txt).
This is construction evidence only; boot2 has not been written and no physical
selection or runtime claim exists.

The first guarded TOPRGU deployment preflight refused before staging because
the then-current adapter required no active swap. A bounded reconciliation
confirmed that boot2 remained at its admitted predecessor, no staging residue
existed, and the sole active entry was unused zram with no persistent backing
or writeback interface. The owner replaced the no-spill requirement with the
RAM-only exception above and required that swap remain untouched. The previous
installer digest in the candidate-readiness record is therefore historical;
the revised policy and eventual clean-publication identity are tracked in
[`results/deployment-policy-20260906.txt`](results/deployment-policy-20260906.txt).
Publication `334c3d91c6659f75532ff66e354fc41d3dedd1f9` was then
revalidated from a clean origin-matching worktree and produced the exact
installer SHA-256
`3e1afaef7f5f839e7ae824243b7c73de5423872a0e1585402a172835ef7134db`.
This restores deployment readiness without changing the candidate bytes or
selecting the physical experiment.

The guarded deployment then resolved live logical `boot2` to
`/dev/mmcblk0p30`, verified the admitted predecessor, wrote the candidate once,
synced and flushed it, matched a full-partition readback, and confirmed the
known-good OS was unreachable after its clean shutdown request. The generated
installer's final local receipt check exposed a repository-root path defect only
after those device steps had completed. The write was not repeated. The parser
repair and regression fixture now accept the unchanged final private summary;
the sanitized [deployment receipt](results/deployment-20260906.txt) records the
exact identities and failure boundary. The candidate is installed and awaits
the owner's one physical `boot2` selection. No physical selection or runtime
TOPRGU result exists yet.

The prior Buildbox attempt at exact commit
`e70982c09a16a0bb8b152a0dfcada7db69d2a0bf` failed before applying 0543 because
its first hunk expected stale source context. The corrected patch was replayed
read-only against the effective single-file chain in a temporary Buildbox
directory, proving preimage `9ee35ef` and postimage `cf093ee`.

Buildbox then applied all 530 patches, compiled `mtk_wdt.o`, linked Linux, and
validated the package from exact repository commit `745ecaea21c004a377a01287bea8ac3b58c2d6e2`.
The immutable build facts are in
[`results/buildbox-745ecaea.txt`](results/buildbox-745ecaea.txt). The fetched
package inventory is `9b14f15515bb56ec19eb39611a1262edfe56d9df25d3ed69828c4318d76498ca`.
This is compile and provenance evidence only: no boot candidate has been
constructed or selected, and no device or hardware-support claim follows.
