# MT6797 receive mode samples

Status: Buildbox compilation/package validation and offline candidate composition
passed; no installation or runtime claim yet. Mainline beacon reception, association and traffic remain
unproved.

The consumed [early receive experiment](../2026-10-02-mt6797-scan-rx-sample/README.md)
returned zero early statistic bytes and no BSS. Its retained dispatcher word
also contained zero in the earlier dispatcher byte. The
[receive-mode analysis](results/receive-mode-analysis.json) identifies a mode
predicate before the selected native management path. This supplies a distinct
measurement; do not repeat the consumed early-receive lifetime.

## Hypothesis and decision branches

Hypothesis: the selected firmware mode may bypass native management dispatch.
The unique observation is two mode-word samples paired with the existing packed
dispatcher/probe-response statistics during one 500 ms passive channel-40 scan.

- Both mode samples equal 5: the selected prerequisite holds at those instants.
  Inspect earlier queue/descriptor admission and receive enabling; this does
  not establish RF listening, mode continuity or management reception.
- Either sample differs from 5: a sampled software state would bypass this
  selected native management path. Inspect initialization/state transitions;
  do not force the mode word to 5.
- The mode changes between samples: retain timing and transition uncertainty.
- Nonzero or changed statistic bytes: inspect preceding/later processing while
  retaining wrap, reset, other-writer and attribution limits.
- Incomplete replies or ownership failure: preserve an inconclusive result and
  retire the lifetime without retry.

## Bounded protocol

Patch 0083 and profile `mt6797-a53-wifi-scan-mode-sample` retarget the parent
sampler. Role 0 reads the whole ordinary RAM word `0xf006bffc`. Role 1 reads
`0xf006bf38`: dispatcher byte at bits 7:0 and probe-response byte at bits 31:24.
No arbitrary address, target write, hardware-register query, special prefix,
mode write, filter change, active probe, association, key, data TX, IRQ enable,
packet DMA or calibration operation is added. Ordinary query buffer allocation,
reply queueing and TC4 debit effects remain admitted as in the parent.

Keep firmware, private record, board DT, broadcast filter and BSS setup unchanged.
The first pair starts no earlier than 100 ms and the second no earlier than
300 ms after scan submission. Retain at most four queries, one outstanding,
fresh shared sequence/history, exact address/sequence matching, a 100 ms reply
deadline and no reply credit refund. Retain the five-second scan deadline,
256 polls, sixteen packets per tick, 4096 total packets and retired lifetime.
DONE admits only the existing bounded RX tick; no later query or polling
extension is allowed. Pending, duplicate, missing, late, malformed or unmatched
replies make the diagnostic incomplete without extra cleanup I/O.

Pairs are non-atomic. The mode can change between observations. Eight-bit
statistics can wrap or reset and have no pre-scan baseline or complete writer
audit. Report byte changes modulo 256, never as an exact packet count. The
classifier always leaves RF receive proof false, including when mode equals 5.
A post-DONE observation is retained but cannot satisfy before-DONE acceptance.

Before physical admission, require clean pushed Buildbox provenance, exact
candidate/tool pins, offline preflight, guarded live-GPT boot2 installation and
matching full readback. The owner selects boot2 physically. Verify the exact
live release and changed boot identity before one START and one scan. Preserve
unique evidence before reviewed recovery and confirm changed-boot Gemian.
Neither the current Gemian boot nor a prior installation admits this candidate.

## Source validation and reproduction

The [source review](results/source-review.json) pins six resulting driver files,
the fixed whitelist, unchanged operational lifecycle and finite budgets. All
265 previous manifest profile objects remain unchanged. The new selected series
is the parent plus one canonical-order patch; the default-off addition changes
the canonical superset, so this is not a claim that every prior effective build
input is unchanged. Replaced historical diagnostic symbols are selected only
through their frozen profile subsequences.

Run `tests/mode-result-test.py` for mode values, transitions, wrapped statistics,
unrelated bytes, timing, malformed, duplicate and post-DONE fixtures. Compile
`tests/scan-mode-test.c` with C11, `-Wall -Wextra -Werror`, and the resulting
driver header include directory. It checks exact address encoding, rejects
retired/opposite-role addresses, malformed replies, sequence reuse, TC4 debit,
capacity refusal and failed transport. These are host fixtures, not RF evidence.

Strict patch checking passes with documented `CONFIG_DESCRIPTION` parser and
`MISSING_SIGN_OFF` archive exclusions. Strict complete Kconfig checking passes
without exclusions. The explicit synthetic archive author supplies no DCO
certification; this patch is not submission-ready. Build only with:

```sh
KERNEL_PROFILE=mt6797-a53-wifi-scan-mode-sample ./scripts/build-kernel --backend buildbox
```

After validated compilation, compose the exact candidate and retarget runtime
wrappers before admission. An upstream removal condition is replacement of this
isolated bring-up sampler with normal management reception/event handling.

## Build and candidate

The [build receipt](results/build.json) binds clean pushed commit, validated
package and six independently matched source hashes. The
[candidate receipt](results/candidate.json) binds the proven booted board DT,
unchanged private firmware/record/authenticated userspace and exact 16 MiB
padding. The release-only RAM-root transform reproduced byte-identical bytes
and independently matched the tested early-RX parent at all other members.
Runtime wrappers are pinned to this candidate and classifier. Complete offline
preflight and regenerate the guarded installer against fresh live Gemian
identity before deployment. Capture/host preparation additionally require a
real deployment receipt; do not supply a synthetic one.

The [offline preflight](results/preflight.json) validates source/private record,
authentication, native recovery and generated guarded installer syntax and
ShellCheck. Both full runners refuse without real deployment evidence. The
installer still needs regeneration against fresh live Gemian identity before
execution; neither firmware START nor scan has been consumed.
