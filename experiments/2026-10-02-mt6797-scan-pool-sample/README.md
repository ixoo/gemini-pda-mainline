# Native receive object availability during one passive scan

Status: Buildbox package and offline candidate validated; runtime tools bound.
No installation or hardware lifetime yet.

The consumed [mode sample](../2026-10-02-mt6797-scan-mode-sample/README.md)
observed mode 5 twice, with zero dispatcher/probe statistics and no BSS.
The earlier [receive admission analysis](../2026-10-02-mt6797-scan-mode-sample/results/receive-admission-analysis.json)
places native object allocation before that gate. This experiment measures
that prerequisite with the existing finite read-only sampler.

The [ownership analysis](results/pool-ownership-analysis.json) selects the
initializer's mode-2 branch and distinguishes command-input pools from native
RX. It does not prove live initialization or exclude ROM/aliased effects.

## Hypothesis and unique observation

A missing or depleted native receive free list may bypass processing before
the observed mode gate. Read exactly the native free-list head at `0xf0073680`
and its free-object count at `0xf0073688`, twice, during one channel-40 passive
scan. No prior candidate sampled these words. Mode and old statistic queries
are replaced, not added. Firmware RAM identity remains pinned in the analysis.

A head equal to `0xf0073680` is the selected getter's empty sentinel. The
32 initialized object addresses are `0xf007368c + n * 88`, for `0 <= n < 32`;
the last is `0xf0074134`. An in-range count is 0 through 32. Retain unexpected
values as valid diagnostic observations rather than rejecting a well-formed
reply. Separate reads cannot form an atomic list snapshot.

## Decision branches

- Valid member head and positive count at both pairs: availability was observed
  at separate instants; prioritize descriptor arrival/enabling and filtering.
- Sentinel head and zero count: investigate initialization, allocation and
  shared users; this does not prove continuous exhaustion or its cause.
- Head/count disagreement, unknown head or count above 32: retain exact values
  and investigate ownership/timing; do not force initialization or repair RAM.
- Missing, mismatched, late or post-DONE replies: no before-DONE availability
  conclusion. Preserve evidence and perform the reviewed recovery once.
- A validated beacon/BSS would change the receive result independently of
  pool values; association and working traffic still require later proof.

Do not convert count changes into packet counts. Successful command replies
use other selected pools, but indirect query effects remain unresolved.

## Source and bounded protocol

Profile `mt6797-a53-wifi-scan-pool-sample` adds only canonical proposal `0084`
to the mode parent; the [source review](results/source-review.json) pins six
resulting source files. The default-off symbol is `MT6797_SCAN_POOL_SAMPLE`.
`hif.c`, `hif.h` and `mac.c` equal their parent after sampler name reversal
and whitespace normalization. The normal command helper admits only the two
aligned ordinary RAM addresses, CID `0xc0`, query flag zero, exact address,
sequence, event ID and reply length. No arbitrary or special-prefix read.

Retain one WMT/START and one 500 ms passive single-channel scan per lifetime.
At 100 and 300 ms, submit head then count with one outstanding query, fresh
shared sequences, a 100 ms response deadline and at most four submissions.
Debit TC4 before submission; no refund. Keep the 5 s scan deadline, 256 polls,
16 packets per tick and 4096 total packets. DONE never extends polling. Retire
once and reject reuse after completion/abort. No active probe, association,
keys, data TX, IRQ enable, packet DMA, calibration, list/count/mode write or
callback-table write is admitted. Stop and preserve evidence on unexpected
identity, corruption, heat or recovery behavior under the safety policy.

Before a physical test, validate the clean pushed Buildbox package, pinned
source/config/DT/root/container and installer, exact predecessor checksum,
live GPT guard, stable power and full readback. Use the existing private
firmware/calibration/auth root and reviewed recovery tools. Boot2 physical
selection remains an owner action. No candidate is admitted by this source
record alone. The mode lifetime is consumed and must not be repeated.

## Focused checks

The C wire test checks exact query bytes, credit/sequence retirement, address
and malformed-reply rejection. The Python classifier retains the parent
four-response/timing validation and tests pool membership boundaries,
non-atomic disagreement, unexpected values and post-DONE handling. Strict
Checkpatch excludes only the explicit non-certifying archive sign-off and
Kconfig diff-description artifact; full resulting Kconfig passes without
exclusions. This patch is an internal archive, not an upstream submission.

## Validated candidate and runtime binding

[Build validation](results/build-validation.json) records the clean pushed
input, validated package inventory and matching six compiled-source hashes.
The [candidate receipt](results/candidate.json) pins the exact kernel, config,
proven booted DT, private root, boot container and full 16 MiB padding. The
root has the same 59 members as the mode parent, with only its init release
gate changed. Firmware, private storage record and userspace remain unchanged.

`build-candidate.py` validates and composes that package and root;
`retarget-initramfs.py` reuses the pinned original RAM-root transform.
`install-passive.py`, `capture-private.py`, `passive-session.py` and
`passive-host.py` bind the exact receipt, predecessor, release and classifier.
The generated installer is operationally identical to its reviewed parent
under the recorded binding substitutions. It resolves logical boot2 from live
GPT, enforces the device guard and stable power, requires full independent
readback and clean shutdown, and never selects boot2 automatically.

Candidate preparation performs no device action. Capture and host offline
preparation require the real verified deployment receipt; do not fabricate a
receipt to pass that gate. Installation, real-receipt preparation, physical
selection and the single hardware lifetime remain outstanding at this record.
