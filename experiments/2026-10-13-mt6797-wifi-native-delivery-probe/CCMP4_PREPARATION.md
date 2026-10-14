# CCMP4 — approved failure-only staged word, no transport repair

ROOT materially approved exact [0194](../../patches/proposals/0194-wifi-mt6797-retain-failure-only-staged-type-word.patch),
SHA256 `96443818f38fb74e5f09362d7216c9b42f09a349beb23cd06cb3e442fe968701`,
body `ea1cf2930372c8dc26b1531b44ac7f0b50541d0d9ad52438b36791423c28c9db`,
source `b5969e62f02486f70fec2f202e21ec3e724286d9`, parente1ecfcd9.
Child HIF cfe0e113/header68c2a242/MACe3ee7a91. Exact12 additions/2 deletions,
only refused_type_valid/untrusted16-bit refused_type_word from already-staged
offset2 on existing complete/header-valid/length-refusal, one owned-lifetime
report followed by unchanged immediate poison/fail-stop. No successful packet
publication, caller copy, new read, parser, tail/boundary word, scratch dump,
WHCR write, aggregation acceptance or new radio/resource effect.

[Body/tests/protocol](REFUSED_TYPE_REVIEW.md) and [CCMP3 outcome](CCMP3_RESULT.md)
own the detailed contract and need. ROOT independently verified parent/child,
surrounding guards/locks and actual-source sanitizer/absence/privacy/one-shot
tests. Checkpatch has only missing truthful DCO, zero warnings/checks; internal
synthetic non-certifying archive, not upstream-ready. All existing radio/frame/
byte/wall/grant/drain/key/PN/cleanup/evidence/one-return limits remain unchanged.

## Preserving selection and build admission

Fresh profile `mt6797-a53-wifi-ccmp-refused-type` selects
`patches/series-a53-wifi-ccmp-refused-type`: exact CCMP3 ordered688 plus0194=689.
Series SHA256 `1516a2dcefdf29e6f60bc7b55971320eed74fcfa2bba646fc581a5fe2c0576c6`.
Same26 ordered fragments/release. All26 previous profiles,20 existing named
series and48 config/DT paths remain unchanged. Canonical only appends0194;
historical implicit full/handoff/usbdiag/usbdiag-clkignore inherit it, not a new
build admission. Completed CCMP3 inputs/tooling/receipt/logs remain immutable.

Ordinary clean pushed BB1 only,32jobs/modulesfalse/experimentselectorunset. Actual
preflight:48CPU quota/128GiB memory limit/about10GiB use,418GiB workspace free,
managed lock available/no heavy build processes, all57 retained jobs validated;
doctor/toolchain/repository access pass. Recheck before submission. Validated
real package/fetch pins feed a fresh compositor, then ROOT private64 composition
returns only its real receipt. Fresh capture-ccmp4/session-ccmp4/runtime-ccmp4 and
guarded installer bind that receipt; expected predecessor CCMP3 full4e3c requires
ROOT fresh OS/boot/GPT/root/power verification. No private image/RAM/key transfer,
assembly permission turn, binding-only rebuild or worker device access.

## Short source/retained consolidation (no additional candidate effect)

[Corrected retained scalars](results/retained-source-scalars.json), SHA256
`5cc840041f8d7c2523ad60e7c9eaa96ebdb4f6c4fb0d0dccff9636a33a61a2b5`,
are supplied/independently raw-hash-verified by ROOT, not new hardware samples.

- M3: e1ec mac2311–2339 uses join_event/mt6797_join_tx_done, software-defined
  class7/typeword0xe000/eventID0x0f/**24 total bytes**, expectedPID and WLANindex1.
  Only matching owned internal deauth plus status0 sets join_deauth_done. WTQCR
  page reconciliation is separate; page return cannot complete deauth. An
  event-like hint cannot identify that exact event/pid, especially header28/32.
- WHCR logicalF1offset0x0c is encoded as setup0x10001804 at physical bridge
  0x180f0000 and read via data0x180f1000, **not** direct MMIO0x180f000c. Actual
  hif.c393 reads it in baseline/post-record **and runtime** status reconciliation;
  runtime scan/join guards discard the local value. Audited explicit host paths
  do not write WHCR. No current fault-time value or reset default follows.
- Eight historical retained one-shot snapshots (1/1/3/3 across four experiments)
  had WHCR0: named maxlen[13:8]/enhance16/reportown3 allzero then, not anomaly,
  aggregation proof or current CCMP3 state. Vendor enhance/aggregate AHB routing
  and len-num0 versus single-path1 convention are source-supported; WRPLR total
  semantics, epoch state and safe write ownership remain unproved. No historical
  maxlen1 could rule out a later-state hypothesis. No WHCR access or aggregation
  parser is added by this candidate; a future register test needs its own protocol.
- N1: ND6's one descriptor recorder is admitted-ACTIVE/phase1-only; its retained
  groupsf cannot provide pre-arm coverage. CCMP3's checked branch bypasses that
  recorder and legacy Group1 counters; seven pending type2 entries have no group
  metadata and occur after enable submission. Allzero ordinary footer is not
  normal-mode absence. Same-session before/after Group1 comparison is unavailable;
  no new machinery will be authored to manufacture missing historical observations.

No speculative producer/PN/epoch/IRQ/DMA repair or new RE scan is admitted. See
[retained R32/key/submission audit](R32_CCMP3_SOURCE_AUDIT.md). Normal Group1/PN,
firmware integrity, GTK/rekey/retirement/reuse/lifetime and clean-profile ten-
minute support remain unresolved prerequisites; no pre-arm check substitutes.

## Future single-run decisions

The new observation is only the untrusted staged hint on an existing refusal.
Control-like/data-like/zero/unrecognizable/absent branches narrow a retained-
source question, never certify an event/producer/boundary or change acceptance.
No hint/refusal means honest absence, not an induced fault/retry. CLOSED is not
assumed the first RX (12 type2 preceded CCMP3 refusal), and missing ND6 sanitized
deauth is omission, not evidence of no deauth or a cause.

Retain one finite initial WPA/CCMP/normalDHCP/ping3/ACTIVE SSH trial and complete
leaf/process/cycle/ACK/healthy-cleanup/seal/A53/one-return proof; partial remains
partial. Any fault preserves available evidence, quiesces children and uses the
unchanged identity/tool-bound return, no extra read/sample/alternate recovery.
Full maintained driver goal remains active; this is a diagnostic, not a repair.
