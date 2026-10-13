# ND3 result — command-credit progress, no eligible native delivery

One completed negative/inconclusive native-delivery run; preserved evidence,
service regression and exactly one reviewed recovery passed. This is not a
firmware-mode acceptance, authentication/replay or maintained Wi-Fi result.
The sole laptop custodian performed all device operations. No unchanged retry.

## Exact identities

- Kernel input `985744adb169ea543d5a8963cf710878c4dc9125`, profile
  `mt6797-a53-wifi-native-delivery-diag`.
- Package `fd232eaf39f501db4e6c6c81c40953acfce95dadded1dd3f29275c5ef994d4a2`;
  Image.gz `dd56fddd5d5647d0439f79725d8176a63238d82db7d8af76265809111595bcc0`.
- Frozen runtime `d37d1e2af23f32e54016aa518fdd914644f648ce`.
- [Real candidate receipt](results/native-delivery-candidate-3.json)
  `f00de1e3bcc40e912ba65f7ebbe3ad15bbc159b230f3e84af3b45dd8cebe7e10`;
  raw boot `e25c1fa387f2be84908363a4e65f7e4b70ffea541684bccd991a4736f44980a6`,
  full boot2 `7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`.
- Mainline boot `b650f5bb-8704-4969-8269-76bb8217f088`.
- Exact native source mac.c
  `c794cd5bcebd90f21f29f2a1bae4792f1e00c3160c22680e031f7b714b6aaa23`,
  hif.c `73f6c0b5182b61953e223e331cc13b64327a784ebbf98977b8a50b7bada9e01c`,
  data-rx.h `e465bd1ee3a8c16474bfdcc3d909f6ce7349840d4c7fb6160bdcffada54ea2e8`.
  This is ND3, not the later phase-b 0184/0186 source.
- Complete sealed log `b7e1d741b6385931e3643d473cd4d079fc8b0da0be14b7d4a2551da5903ea73b`,
  157453 bytes / 2046 records; sequence-zero-through-explicit-seal coverage.

## Observed sequence and outcome

Phase A passed all 285 common-init steps with `ready_for_scan=true`.

```text
one-shot WLAN native-diag: state=1 act=1 total=0 native=0 bytes=0
one-shot WLAN native-diag: state=2 act=0 total=1 native=0 bytes=442
one-shot WLAN native-diag: state=3 act=2 total=200 native=0 bytes=40338
one-shot WLAN native-diag: state=4 act=0 total=200 native=0 bytes=40338
one-shot WLAN join stopped: status=-71 first=0 submitted=0x1801 debt=1 cleanup=0 branch=4
```

The IDLE/enable-pending/ACTIVE/disable-pending/CLOSED command-credit progression
overcame ND1/ND2's deterministic local refusals. Its quiescent transitions attest
to transport-ledger progress, not the requested firmware mode's acceptance or
semantics. Total RX200/40338 bytes includes all counted classes, not 200 eligible
protected frames. Native delivery was zero; there is no first-native flag/MPDU
sample. Classifier `native_delivery_pass=false`, sequence valid, fault present.
Absent samples do not establish that actual delivered frames had bypass flags.

No post-ACTIVE READY marker or Wi-Fi SSH attempt occurred. The helper reported
`ready_seen=false`, `ssh_attempted=false`, reason `a named join fault was recorded`.
ACTIVE alone does not create READY: the actual leaf first needs a DHCP lease,
validated/live listener and open window, as well as the ACTIVE record. Supplied
aggregate evidence does not yet identify which leaf prerequisite prevented it.

## Source diagnosis and unresolved discriminators

The terminal branch4 is the HIF receive boundary, before native/frame/control
class dispatch. With status `-EPROTO`, the actual HIF has two protocol refusals:
selected WRPLR length outside4..2352 or staged packet header length differing
from that selected length. Supplied evidence does not distinguish these gates.
The generic packet cap has a different zero-status/E2BIG failure path; native
decoder false returns silently withhold and cannot themselves cause branch4.

The footer prints MAC `first_error` before latching the current failure;
`first=0` is therefore not proof of a healthy/unpoisoned HIF after failure.
CLOSED follows quiescent disable credit retirement. The later submitted mask
adds management subtype12 (deauthentication), with debt1 consistent with that
newly submitted frame rather than an unretired disable command; exact final
TX/credit chronology remains to be confirmed from sanitized numeric records.

Post-window CLOSED runs inherited bounded cleanup reception, not the earlier
ACTIVE-ending finite owed-completion gate. No bound is widened by noting this.
Inside the sampling window, native decoder failures have no rejection histogram
or header-shape record in the supplied evidence. Existing totals cannot separate
no protected traffic, translated/plain traffic or rejected native shapes. No
decoder relaxation, guessed firmware correction or capability rejection follows.

## Hardware-free validation and next decision

The existing classifier, replayed on the supplied terminal records and SSH
receipt, returns a valid sequence, fault, zero native delivery and no PASS.
Existing PIO RX tests against the exact ND3 hif.c pass (including invalid length
and header mismatch, without copying refused data). Existing native-loop and
native-RX tests against that same prepared source pass under ASan/UBSan. These
are synthetic contract checks, not a reproduction of the unknown live RX shape.
No new kernel build or device operation was performed for this reassessment.

The smallest next step is the already requested sanitized chronology: leaf DHCP/
listener/window outcomes, final subtype12 submission/completion/credit records,
and any existing HIF refusal or descriptor metadata. If the two HIF gates remain
indistinguishable, the narrow next code proposal is failure-only numeric metadata
at those existing refusal sites, with tests for both gates and unchanged refusal,
poisoning and copy behavior. It must not add RX reads, payload output, retries or
budget changes. Decoder-shape instrumentation is a separate decision only if
existing records cannot discriminate it. No material implementation or build is
admitted here; source changes require coordinator review first.

## Evidence integrity and recovery

All 63 pre-recovery seal hashes independently matched; seal manifest
`4cb8bc6b4fdd5f3bc7640f82cd04e75b4e63d4a925f9a35641c21f9b5f5498d7`.
Log/preservation complete; helper group quiescent/safe; device quiesced with empty
faults. Service regression passed. Exactly one reviewed recovery completed;
strict independent Gemian verification confirmed kernel `3.18.41+`, changed boot
`701e7d15-50bc-43e2-b94e-3134bbc71de0`.

This record uses checksum-verified sanitized custodian metadata/extracts. Raw
captures, AP/own identity, credentials and payloads remain private. Boot IDs and
deployment/evidence digests are retained under the publication policy. Historical
[ND1](ND1_RESULT.md), [ND2](ND2_RESULT.md), installation and frozen runtime remain
unchanged. C34/R35 and C35/R36 remain independently prepared but not installed;
no candidate substitution or unchanged ND3 retry is authorized by this result.
Full maintained station/crypto/replay/IRQ/DMA/rekey/clean-profile goal remains open.

The subsequently supplied numeric chronology and source-review-only diagnostic
proposal are recorded in [ND4_SOURCE_REVIEW](ND4_SOURCE_REVIEW.md). This adds
missing observations without changing the frozen ND3 inputs or result.
