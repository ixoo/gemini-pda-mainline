# One predecessor trace from the NVRAM reference

The [subsequent target trace](FIRMWARE_NVRAM_CALL_TARGET.md) resolves the
computed-call destination on one conditional path to an immediate-derived
plaintext-code candidate. It supersedes the numeric-target uncertainty below;
the target's contract and incoming entry remain unproved.

A bounded static trace now connects a plausible local entry boundary to the
first instruction-aligned NVRAM reference candidate. The referenced address
remains in the default NDS32 ABI's first argument register until an indirect
call three following instructions later. This is decoded argument-flow
evidence, not identification of an NVRAM handler, logging routine, or record
application. The incoming caller and the indirect callee are unresolved.

## Premises and predecessor method

This slice reuses the same immutable firmware identity, plaintext mappings and
NDS32 instruction premises from [the mapping investigation](FIRMWARE_EXECUTABLE_MAPPING.md).
It follows the same first NVRAM-containing-span reference, without changing
anchors after an unfavorable result. The default little-endian data ABI
remains provisional; the relevant instructions are decoded big-endian.

The graph was reconstructed from decoded section-2 instruction boundaries
for predecessor analysis, not to repeat broad statistical measurements.
Each ordinary direct branch and fallthrough contributed a predecessor edge
only when its destination was an established instruction boundary. Direct
call targets were collected separately as candidate entries; callees were
not traversed as ordinary intraprocedural edges. Unknown computed targets were
not invented. The reverse walk from the reference had a 16384-node limit.

The reverse queue exhausted after 17 nodes. None was a collected direct-call
destination. There was exactly one root with no predecessor in that graph.
It is not the section start. Its decoded instruction both reads and writes
the stack pointer; the preceding linear instruction is terminal, is not a call,
and has no fallthrough. These facts support a local function-entry hypothesis,
but do not prove a complete function boundary or reachable runtime entry.
Unlike the earlier nearest-call-target heuristic, this root is selected from
actual predecessor connectivity to the anchor.

## Forward check and decoded argument flow

A forward walk from that root followed ordinary direct branches and
fallthrough, without entering callees. Its 4096-node budget was not consumed:
the queue exhausted after 44 nodes and reached the anchor. It encountered one
terminal instruction, two calls and two computed transfers; no visited node
was outside the established section-2 boundaries. The computed-transfer and
call counts are separate categories, not four distinct operations. The walk
does not resolve computed destinations, prove a direct jump is not a tail
call, or establish the return behavior of a skipped callee. It demonstrates
reachability in this bounded static model.

The anchor's same-register split-immediate pair constructs an address in the
previously bounded NVRAM-containing span. The destination register is `a0`.
The installed Ghidra NDS32 compiler specification places the first ordinary
argument in `a0`; applying that convention to this firmware is an explicit ABI
hypothesis, not independent firmware ABI attribution.

Starting immediately after the pair, a bounded fallthrough inspection reached
a computed call at the third following instruction. No intervening instruction
reported a write to that register, and no branch was crossed. Consequently the
decoded value reaches that call unchanged under the instruction model. The
callee has not been identified. Passing a text-associated address is compatible
with diagnostics, among other uses, but does not prove a formatter, successful
NVRAM application or calibration-source selection. No private text, address,
instruction listing, record bytes or calibration values are published.

## Exact remaining control-flow premise

No collected direct call in the plaintext section targets the reverse path.
An indirect dispatch, a reference from unavailable/encrypted code, a different
entry convention or an unmodeled control transfer could account for entry;
this trace does not select between them. The immediate missing premises are
an attributable incoming transfer to this path and the target/contract of the
computed call carrying the reference. Without those, the path cannot be named
as command `0x48` handling or interpreted as an EFUSE/default precedence rule.
This is the end of the requested bounded slice, not a new hardware gate.

## Private state retention and validation

The authorized private guest analysis project is retained to avoid rebuilding
useful state. It occupies approximately 1.6 MiB in a mode-0700 guest-owned
managed work directory outside the immutable evidence tree. Its retention
record contains the existing firmware filename, previously recorded SHA-256
and size, Ghidra 12.1.2 identity, provisional ISA/ABI settings, reconstruction
scripts and cleanup condition. The program stores the candidate entry and
anchor privately and labels the candidate function as an analysis hypothesis.
No project, log, firmware, address or database is exported or committed.

The directory was created with restrictive permissions and an immediate
cleanup trap for an unsuccessful initial construction. A successful retention
marker preserves the project; the directory is to be removed when its owning
investigation closes. Host and guest free space were checked before creation
(approximately 86 and 87 GiB). The source identity was reused without another
hash computation. The RE shell was closed. There was no decryption, emulation,
device/radio access, kernel build or runtime validation.

The source record policy and normal-command submission boundary are unchanged.
[CALIBRATION_APPLICABILITY.md](CALIBRATION_APPLICABILITY.md) and
[NORMAL_COMMAND.md](NORMAL_COMMAND.md) retain those conclusions; ordered work
remains in the roadmap.

## Coordinator review

The coordinator reviewed both analysis records and independently checked the
pinned public loader's masked section placement and WMT remap programming.
The private decoder runs and graph counts were not independently repeated.
Their retained method and explicit ISA/ABI, entry and computed-target assumptions
support publication as bounded investigation evidence; they do not establish
runtime reachability, calibration precedence or firmware/record applicability.
Host implementation and shared-resource ownership work continue independently.
