# Post-C9 source review: control boundaries and a read-query question

Incomplete, 2026-10-18 UTC. [C9](CCMP9_RESULT.md) remains the latest consumed
device trial. This review made no device query, radio action, firmware change,
kernel change or new candidate. Ordinary secure Wi-Fi and its full acceptance
gates remain unimplemented.

## What changed the next action

The previous bounded monitor-handler review stopped at a register-indirect
call. Its adjacent constant-construction instructions provide a specific
in-image target; resolving that one call needs no image-wide or pointer-slot
scan. A fresh, explicitly bounded VM investigation verified that call site,
then decoded a 64-byte target window. All 63 retained handler instructions and
23 retained caller instructions reproduced exactly. The new window contains
21 instructions and leads to another constant call.

Before interpreting its arguments, three previously unvalidated store shapes
and one load shape were independently derived from pinned
[GNU binutils field encodings](https://github.com/RTEMS/sourceware-mirror-binutils-gdb/blob/506d153ed46c3b5ffe9041647a9d57faae8ec22c/opcodes/nds32-asm.c#L702-L710) and checked with the existing decoder validator. The first test
passed the stores but rejected an expectation for an explicit zero displacement
where the load operand contains only a base register. The corrected exact-base
expectation passed all 50 vectors; the failed check remains preserved. Frozen
decoder sources and earlier results were unchanged.

The handler's argument setup correlates with the public SET_MONITOR payload's
frequency/channel/SCO/width/channel-segment fields. This channel-control call
occurs before the enable/disable test. The separately specified 256-byte
continuation supplied 82 instructions and reproduced the 21-instruction anchor.
It contains an unresolved callback and conditional peripheral writes; the
function continues outside the window. Four NI16 records remain outside the
frozen validator's accounting. This is neither a pure scheduling conclusion
nor proof of an RX queue conversion, reset, drain or length publication.

The original opaque monitor callback slots remain unresolved. No callback or
constant scan was repeated; neither continuation establishes the missing
producer relationship between FIFO length, final RXD groups and mode change.
The repeated delta48 remains a refusal, not a framing rule.

## A concrete alternative to more callback scanning

The pinned public gen3
[read OID](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_oid.c#L4423-L4493)
uses CMD_ID_ACCESS_REG as a query with a response for firmware-domain addresses,
with separate special-address handling. Its
[private OID dispatch](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/gl_wext_priv.c#L1454-L1482)
and [ABI definitions](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/include/gl_wext_priv.h)
provide source to review; they do not authorize arbitrary queries, an unlock,
a write path or bypassing a disabled interface. This is investigation of the
existing stock implementation, not a new maintained userspace API.

A VM-only lookup of that one command's existing dispatch row found a unique
in-image handler. Its initial 256-byte window supplied 82 instructions and
reproduced the 63-instruction monitor anchor. The read arm lies outside that
window; write-arm behavior was not treated as query behavior. One additional
GNU-derived branch vector passed with the prior 50 before examining the
explicit 224-byte read branch.

The first read-arm invocation correctly refused because the regression window
split a four-byte instruction. That authoring error and its output are retained.
Correcting only the anchor to a known instruction boundary produced seven exact
entry matches and 70 non-gap read-arm instructions. Five trailing gaps and ten
NI16 records outside the frozen accounting remain labeled. No live query ran.

The read arm has special-address dispatch, a default address guard, a load and
response construction. Exact operand shapes, branch predicates, reply identity
and the live stock ABI still need review before admitting any word observation.
For signedness, independent
[GCC machine descriptions](https://gnu.googlesource.com/gcc/+/2b0e81d5cc2f7e1d773f6c502bd65b097f392675/gcc/config/nds32/nds32.md#1427)
map `slti` to unsigned comparison with a signed immediate operand. Treating the
printed negative immediate as a signed comparison would misclassify the guard.
That source fact does not by itself validate the remaining firmware path.

## Subsequent observation

The [pointer result](POST_C9_POINTER_RESULT.md) records the later admitted
read-only queries and one fixed callback capture. The admission question below
was resolved for those exact reads only; it does not authorize a control write.

## Original next bounded decision

Review whether the stock read query can safely retain exactly the already
identified monitor pointer words, without changing radio configuration,
unlocking a disabled path or reading an arbitrary register range. Require
verified live Gemian/boot and firmware identity, an exact source-supported ABI,
read-only effect proof, response address/length checks, finite one-shot limits,
private preservation and stop-on-mismatch. Do not issue queries to discover
which addresses work. If this contract cannot be established, preserve the
precise limit and select another source question before device effects.

A supported observation could distinguish in-image targets from an unavailable
ROM implementation and replace blind scanning with exact target review. This
is a hypothesis and admission question, not an executed test or permission to
follow returned pointers automatically. No C10 boot, deadline extension,
credit adjustment, equality relaxation, PN bypass or key reuse is selected.

All firmware decoding ran in the existing RE VM. Fresh outputs, exact tool/module/input
pins, synthetic checks and real-byte regression anchors were retained. Process
quiescence was checked independently. Private records include unsuccessful
checks as well as completed windows; no firmware binary section, decoded
instruction listing, network identifier or credential is published here.
