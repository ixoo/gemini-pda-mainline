# Retained baseline acceptance verifier

[`scripts/verified_baseline.py`](scripts/verified_baseline.py) verifies the
retained first authenticated baseline and its changed-ID known-good recovery
as a prerequisite for a later packet. It is a read-only archive component.
Candidate/package validation, credential validation, current deployment and
physical admission remain separate caller responsibilities. A verified archive
does not grant another connection, device operation or observation budget.

## Inputs and trust boundary

The Python interface is `verify(evidence_root, bindings)`. The archive root
contains the original `attempts/<admission_id>` and `sessions/<admission_id>`
directories produced by the baseline tools. Private offline copies are allowed.
Required evidence consists of private, regular, single-link files and private
directories, with exact inventories and checksum manifests. Paths through
symlinks, extra files, missing phases and incomplete captures refuse.

The caller supplies exactly these independently reviewed bindings:

| Binding | Meaning |
| --- | --- |
| `admission_id` | Original baseline admission UUID |
| `candidate_sha256` | Raw Android-v0 `boot.img` digest, not the padded partition digest |
| `candidate_manifest_sha256` | Digest of the validated candidate manifest |
| `baseline_manifest_sha256` | Digest of the original observation's `SHA256SUMS` |
| `confirmation_manifest_sha256` | Digest of the final known-good confirmation's `SHA256SUMS` |

These values must come from the caller's reviewed admission or evidence record.
Taking them from the same unverified archive would establish internal
consistency without establishing the intended experiment's identity.

The verifier checks the archived candidate manifest against those bindings and
uses the existing deployment receipt parser. It opens neither a boot image nor
a credential. Before dispatch, a packet launcher separately validates its
candidate/credential inputs and compares their candidate manifest, original
admission and deployment receipt digests with the snapshot-derived verifier
result. This cross-check prevents a separately prepared context from silently
referring to different inputs.

## Required evidence chain

Acceptance requires the exact original observation, both authentication
refusals and fresh authenticated probe, complete healthy log preservation,
ordinary native recovery request, owner console acceptance and a successful
known-good probe with an attributable changed boot ID. Every phase must match
its admitted source identities, custody, fixed action budget, consumed claim,
generated command, bounded process record, raw capture and stored result.

The final confirmation manifest binds the three prior phase manifests.
The original, mainline and recovered boot IDs must satisfy the existing
baseline recovery rules. Rejected authentication, failed or incomplete logs,
missing proof, emergency recovery and unchanged IDs cannot establish the
accepted prerequisite. The ten-cold-boot release gate remains separate.

The component reuses the baseline collector, finishing parsers, deployment
receipt adapter and their pinned historical sources. It verifies that source
closure before loading the contracts and again before returning. Evidence
classification uses retained bytes individually verified against the admitted
manifests; it does not classify a later reopening of a checked path. Returned
result hashes also derive from those verified snapshots.

## Output and integration

A passing result identifies the accepted baseline/recovery classification,
candidate and archive bindings, original admission and deployment receipt
digests, all three boot IDs, prior phase manifest digests and the exact original
and recovered result digests. `dependent_admission` remains false and
`network_access` is `none`. This result is evidence for a separately reviewed
packet admission, not an executable action.

Both keyboard and eMMC can consume this same prerequisite. Their later boot,
metadata, action budget, capture, preservation and recovery remain governed by
their own protocols. No new first-baseline collection or candidate revision is
required to introduce this host-side verifier.

## Offline validation

[`scripts/test-verified-baseline.py`](scripts/test-verified-baseline.py) builds
synthetic retained archives from the actual baseline generators and parsers.
It checks the complete evidence chain and refusals for changed bindings,
commands, claims, summaries, process records, phase inventories, source bytes,
links and replacement races. Tests block credential/image access and process
creation. Synthetic fixture receipts do not establish any runtime result.

Exact test counts and implementation identities belong in
[VERIFIED_BASELINE_RESULTS.md](VERIFIED_BASELINE_RESULTS.md). The follow-on packet drafts
remain preparing until their own remaining integration and admission gates
are satisfied.
