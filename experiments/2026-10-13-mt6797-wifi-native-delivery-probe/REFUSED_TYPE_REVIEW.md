# Failure-only staged type-word hint — exact body for review, not selected

ROOT admitted authoring only. No kernel selection/build, composition or device
test is authorized by this archive. [Patch0194](review/0194-ccmp-refused-type-word.patch)
SHA256 `96443818f38fb74e5f09362d7216c9b42f09a349beb23cd06cb3e442fe968701`;
source `b5969e62f02486f70fec2f202e21ec3e724286d9`, parent
`e1ecfcd967a246ad72627b9fd2d92caaa31c59a0`. Only12 additions/2 deletions across
three files:

The canonical `git diff` of those three paths, parent-to-source (default unified
context, no email header/trailer), body SHA256:
`ea1cf2930372c8dc26b1531b44ac7f0b50541d0d9ad52438b36791423c28c9db`.

| Child file | SHA256 |
|---|---|
| hif.c | cfe0e11348fefecad039a605402a9b93ab70c312cf91ccf12e2e7d521f292f76 |
| hif.h | 68c2a2428c44db91b8a76e6f238f84b9f1dbf72ddf0951291a628fbc2f7238da |
| mac.c | e3ee7a910491673b8b61d444199622120c1a4ce33623b28d267372e680bf11ba |

## Concrete need and exact fields

[CCMP3](CCMP3_RESULT.md) demonstrated finite WPA2/CCMP-IP behavior but ended with
post-CLOSED header-length refusal76/28, resembling ND6's80/32. Both consumed
successful CLOSED-phase traffic before refusal; neither proves a refused packet
family or producer cause. The header-length branch deliberately exits before
post-WRPLR read, successful packet-type assignment or caller copy. Retaining one
already-staged metadata word is smaller than adding I/O or interpreting payload.

- Add `u16 refused_type_word` and `bool refused_type_valid` to the existing result.
  Result initialization still zeroes them on every call; zero/false is absence.
- Inside **only** the existing header-length mismatch branch, after header_valid
  is set, require rx_setup/rx_complete/header_valid and staging_bytes>=4. Read the
  little-endian16 bits at scratch+2 into the separate field and set valid=true.
  This is a CPU load from already-filled scratch, not MMIO/FIFO or a new sample.
- Append `refused_type_valid=%u refused_type_word=0x%04x` to the existing scalar
  refusal line. On WRPLR-range refusal those fields are false/zero, not a type
  observation. Successful/empty/I/O-error paths emit no new hint/report.
- Keep the same immediate `error=-EPROTO; goto poison`, HIF/transaction abort,
  locks, caller-buffer nonpublication and unchanged successful `packet_type`/
  `logical_bytes` fields. Do not assign the hint to the valid packet-type field.

The **valid bit certifies staging/span only**, not a valid descriptor, packet,
event, framing family, producer or boundary. No parser consumes the word.

## One-shot and privacy/absence contracts

The owned serialized worker reaches its existing fail-stop immediately after
the one refusal line, latches closing/join_retired and stops that lifetime. HIF
normal/transaction poison also makes a subsequent call refuse before any I/O.
No new counter/rearm/retry mechanism is added. At most one such report per owned
lifetime; the existing CCMP profile permits no reuse/rearm. No report does not
mean a zero-valued word was observed. A valid zero word is still an untrusted
staged value, not absence or an empty FIFO.

Only those two scalar fields are added. No tail/boundary word, event byte,
sequence, scratch dump, MAC/IP/AP/key, payload or new retained raw packet crosses
the interface. No post-WRPLR/FIFO/register read, reset/flush, induced fault or
accepted packet is added. Caller resources, exclusive ownership, IRQ/reset
exclusion, radio commands, frame/byte/wall/grant/drain/key/PN/cleanup budgets,
predicate/equality/poison/no-copy and evidence/recovery rules remain unchanged.

## Actual-source tests and limits

[Focused runner](tests/ccmp-refused-type-test.py) reuses the existing
`run-native-metadata-test.py` compiler and `native-metadata-hif-test.c` transport/
lifetime fixture, not a new I/O model. It compiles actual parent/child hif.c and
extracts their actual MAC refusal log blocks, with pinned parent hashes.

ASan/UBSan PASS:76/28 and80/32 mismatch,76/76 and80/80 positive cases, both ports,
WRPLR-range/empty cases, and every existing I/O fault ordinal. Result/call tables
are identical; no new transfer/post-read, caller copy or packet publication.
Check16-bit field width and valid/absent conditions; parent/child log delta is
exactly the two fields, no other text or payload. A synthetic call on the poisoned
context refuses-EIO without another I/O or report; no radio retry occurs.
The staged fixture word0xe000 is **synthetic**, not an observed runtime event.

Exact three-file delta reversal and all other driver-file equality pass. Existing
original metadata fixture also still passes. Apply-check at immutable parent
passes. Strict checkpatch: missing truthful DCO only, zero warnings/checks;
synthetic non-certifying internal archive, not upstream-ready. No kernel compile,
hardware one-shot execution, valid runtime packet family or producer explanation
is claimed by the host tests. Material review must precede selection/build.

## Hypothesis, unique observation and branches for a future reviewed candidate

**Hypothesis:** the previously unreported offset2 word on the existing refusal
distinguishes framing hypotheses enough to target the next retained-source
question. It does not itself explain the48-byte gap. The new observation is
only the staging-valid bit/untrusted word alongside existing selected/header/
port/staging/state chronology; no post-register observation or first-state4-RX
assumption. ND6 chronology omission is not absence of deauth or a causal test.

- Existing header refusal + valid control-like word: preserve fault and review
  the corresponding event/framing hypothesis narrowly; do not accept an event.
- Valid data/management-like word: preserve fault and narrow pending producer/
  monitor-transition review; do not certify its packet family or strip48 bytes.
- Valid zero/unrecognizable/inconsistent word: preserve uncertainty, no further
  word/tail/boundary read, induced fault, second sample or retry.
- No header refusal, absent hint or earlier failure: record the branch honestly;
  no type/producer inference. If no fault, apply unchanged complete finite
  DHCP/lease/ping3/SSH/consumed-ACK/cleanup/seal/regression/return criteria.

All fault branches preserve unique available evidence, child quiescence and the
one reviewed identity/tool-bound recovery. A fresh candidate would add this
decision-changing observation, not repeat CCMP3 unchanged. Source/body approval
is still required; usual clean BB1/real package/composition/receipt/install flow
would follow without a separate assembly approval. No budget increase, normal-
mode shortcut, firmware search or speculative framing/IRQ/DMA/lifecycle repair.
Full maintained Wi-Fi remains the goal, with production prerequisites unresolved.
