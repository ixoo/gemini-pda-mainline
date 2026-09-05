# Wi-Fi INIT and ownership follow-up

Parent milestone: `bbe78e38a3a089ec674a9106e2529ea20a14b04a`.
Topic: `codex/mt6797-wifi-contract`. This separate offline slice adds files
only; the first milestone's observation scripts, results and hashes remain
unchanged. The final Git handoff identifies the exact follow-up revision.

## Delivered contract

The [INIT reference model](INIT_PROTOCOL.md) checks one delimited 20-byte
DOWNLOAD_CONFIG command and a 28-byte MT6797 CMD_RESULT. It enforces the
expected sequence and classifies all nonzero statuses as firmware failure.
Conservative model policies are distinguished from the selected vendor
consumer's checks. Response diagnostic fields are uninterpreted. PDA queue
identification is covered by explicit refusal; PDA payload parsing, record
extraction and transport are not implemented.

The [ownership audit](OWNERSHIP.md) establishes a shared remap register at
`0x10001340`, separate WLAN/WMT memory extents and MPU policies, and the
selected Wi-Fi AP-DMA channel. Independent review corrected three source
claims: the loader's conditional copy is not overflow-safe refusal, remap
lower-half preservation depends on an aligned argument, and chip-ID
normalization applies only to the register's low 16-bit field. The source
facts and resulting provider requirements remain distinct.

There is no kernel, DT, configuration, manifest, series, candidate or device
state change. The physical session remains consumed and custody released;
this model neither reopens its action budget nor selects a boot candidate.

## Verification

The 36 new synthetic tests pass on host Python 3.14.6. They cover malformed
lengths and types, stale command/reply pairs, sequence boundaries, mode
construction, destination overflow policy, all 255 failure statuses and
suppression of raw or diagnostic data. The earlier 110 tests belong to the
unchanged first milestone; they were not rerun for this additive slice.

The local maintainer review cross-checked the model against SHA-256-verified
pinned source layouts, constructor, selected configuration, ACK consumer and
TX/RX logical-record boundaries. An independent ownership review completed;
the additional agent protocol review was interrupted and is not claimed as
completed. The common publication gate passed, including all 189 manifest
profiles with 37 unchanged grandfathered metadata-debt entries. New-file
syntax, links, license and bounded sensitive-data checks also passed.
[Validation receipt](results/init-ownership-validation.txt).

No kernel build, checkpatch, DT-schema validation, Linux-only artifact
provenance fixture or device test was performed. The Linux-only fixture
remains mandatory in CI. No hardware loading, association, traffic or
mainline Wi-Fi support is established by these host results.

## Integration boundary and remaining coverage

Project Planning owns shared roadmap, hardware-map and queue integration.
Its narrow correction to the first collector's Python 3.5 match handling
must be retained separately from immutable consumed-session hashes; no
rerun is admitted. Its calibration-scope correction distinguishes the
July 11 firmware inventory from the retained July 14 project-wide partition
backup. The backup includes calibration-bearing partitions; their presence
does not establish the WLAN record layout or applicability. Private offline
analysis may use verified retained identities under the owner's existing
authorization, without a new capture or redistribution.

Unimplemented interfaces include CONSYS power/reset/protection ownership,
PDA framing and finite transfer completion, logical RX record extraction,
firmware-session attribution, calibrated/regulatory operation and recovery.
The exact shared-memory and register requirements above constrain any future
driver implementation. One authenticated A53 serviceability pass with
independent recovery remains the baseline dependency for an active radio
experiment. Implementation order belongs solely to
[the roadmap](../../docs/ROADMAP.md); this packet changes no physical
readiness claim and needs no device slot.
