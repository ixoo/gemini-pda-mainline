# Work item: sparse deterministic firmware traversal tooling

- **Outcome:** implement and review a small, independently written, read-only
  Ghidra 12.1.2 traversal helper that removes the deterministic-tooling
  prerequisite recorded by the
  [stopped attribution experiment](../2026-09-06-mt6797-firmware-nvram-handler-attribution/README.md).
  Acceptance is synthetic and program-free. It does not resume either private
  branch or establish firmware semantics, record application, calibration
  precedence, policy, runtime behavior or hardware support.
- **Owner and reviewer:** Luna High owns only this experiment; `/root`
  integrates; Sol Medium reviews this contract and the complete handoff. The
  worker is not alone in the repository and must preserve concurrent and
  unrelated edits.
- **Scope:** add an MIT-licensed pure-Java core, one thin Ghidra script adapter,
  synthetic fixtures, static/refusal validators, README and sanitized result
  receipt under this experiment only. Do not edit the stopped experiment,
  shared manifests/series, roadmap, hardware/support documents, workflow
  ledger or agent settings. No source may contain firmware bytes, private
  addresses, artifact/database names, stored candidate values, instruction
  listings/strings, calibration data, personal paths, or copied vendor/private
  script content.

## Frozen operation contract

The closed phases are `target-cfg`, `target-references`, `incoming-direct` and
`incoming-predecessor`; one invocation selects exactly one. Their operational
caps are fixed, not caller-configurable:

| Phase | Work and cap |
| --- | --- |
| `target-cfg` | intraprocedural FIFO CFG, 4,096 first-dequeued nodes |
| `target-references` | reconstruct that same CFG, then classify 64 canonical unique one-level references without entering callees |
| `incoming-direct` | canonical direct references/call targets to committed caller and target |
| `incoming-predecessor` | FIFO predecessor discovery and sparse constant propagation, 16,384 first dequeues and 65,536 revisit dequeues |

Preflight refuses without a success measurement when the committed window is
larger than 16 MiB; it contains more than 1,048,576 established instruction
boundaries or 262,144 direct references; there are more than 16 roots, 65,536
distinct register-state keys, 4,194,304 P-code operations or 4,096 incident
edges on one node; or a required
candidate is absent, duplicated, ambiguous, outside the window or not an
established instruction when its role is `CALLER`, `TARGET` or
`DISPATCH_ROOT`. `WINDOW_START`/`WINDOW_END` must name the containing block's
exact inclusive bounds; `NVRAM_REFERENCE` may be a non-instruction address but
must lie in that window. Inventories must be streamed or bounded while counted,
never accumulated first in an unbounded collection. Cross-window flow is an
unknown terminal, not followed. Direct calls are recorded boundaries and their
callees are never entered.

Roots, instruction boundaries and unique neighbors use unsigned address order.
The queue is FIFO. A node is counted on first dequeue. The 4,096th target node
or 16,384th incoming node is recorded with its phase cap event but is not
evaluated or expanded; the corresponding cap flag is true. A revisit is
separately counted; revisit 65,536 is recorded but not evaluated. In
`target-references`, references 1 through 64 are classified and digested; a
canonical 65th is only detected, not digested, and sets the reference-cap flag.
References deduplicate by `(source,target,kind)` and sort by unsigned source,
unsigned target, then kind. `incoming-direct` has no operational worklist cap;
after admitted preflight it processes its bounded inventory completely.

Role behavior is exact. `WINDOW_START` and `WINDOW_END` select and commit the
single inclusive analysis window in every phase. `TARGET` is the sole CFG root
for `target-cfg` and `target-references`; the latter first runs the identical
CFG algorithm and then enumerates outgoing references whose source is a visited
node. `incoming-direct` scans established instructions in the window and keeps
only references whose destination equals `CALLER` or `TARGET`.
`incoming-predecessor` uses `DISPATCH_ROOT` as its sole reverse-discovery root;
`CALLER` and `TARGET` are the only concrete indirect-sink hits, and
`NVRAM_REFERENCE` is commitment-only context in all four phases. Commitment-
only roles still must exist and match the independently frozen digest, but
window endpoints are block bounds and `NVRAM_REFERENCE` need not be an
instruction. Only `CALLER`, `TARGET` and `DISPATCH_ROOT` require established
instruction boundaries, and those three plus `NVRAM_REFERENCE` must be
pairwise distinct. Window endpoints may equal an analysis-role address. These
roles never silently add a root or hit.

`incoming-predecessor` has two explicit stages. First, reverse FIFO discovery
starts at `DISPATCH_ROOT`, follows established within-window incoming flow
edges, emits first-dequeue `NODE` and predecessor-to-node `EDGE` events, and
freezes the discovered graph. The 16,384-node cap applies only here. If hit,
the graph is incomplete, no propagation runs and the non-exhaustive record is
returned. Otherwise, forward sparse propagation uses only that frozen graph.
Its initial FIFO is every discovered node with no discovered predecessor,
sorted canonically; if a cycle leaves no such node, `DISPATCH_ROOT` is the
initial FIFO entry with unknown input state. Every propagation dequeue emits
`NODE(first_dequeue=false,expanded=...)` and increments `revisit_dequeues`,
including the first evaluation of a discovered node. The 65,536 revisit cap
applies to this propagation FIFO. Edge events are emitted only during frozen-
graph discovery, never duplicated during propagation. These stage rules define
the dequeued counts and event order independently of source insertion order.

`root_count` is 1 for each target phase, 2 for `incoming-direct` (the two
destination roles), and 1 for `incoming-predecessor` (the reverse-discovery
root); cycle-fallback propagation does not change it. `dequeued_node_count` is
the number of first-dequeue `NODE` events (zero for `incoming-direct`), while
`revisit_dequeues` is exactly the number of propagation `NODE` events. A CFG or
discovery `NODE` has `expanded=true` only after all permitted within-window
neighbors were inspected and enqueued/emitted; a node-cap `NODE` is false. A
propagation `NODE` is true only after its input/out-state update commits and
successors are considered; revisit-cap and discarded state-cell-cap nodes are
false. An evaluated leaf is expanded=true even when it has no successor.

## Sparse propagation contract

Only `incoming-predecessor` evaluates P-code. The adapter supplies immutable
instruction records to the pure core using read-only getters. Supported opcodes
are `COPY`, `INT_ZEXT`, `INT_SEXT`, `INT_ADD`, `INT_SUB`, `INT_MULT`, `INT_AND`,
`INT_OR`, `INT_XOR`, `INT_LEFT`, `INT_RIGHT`, `INT_SRIGHT`, `PTRADD`, `PTRSUB`,
`MULTIEQUAL`, `BRANCHIND` and `CALLIND`. Constants and known registers are
concrete. RAM/stack/external values, loads, calls, userops, invalid widths and
every unlisted opcode become a counted unknown for the affected output or
indirect sink. Memory bytes are never read.

A register key is `(address-space UTF-8 bytes, unsigned 64-bit offset, width)`;
width is 1 through 8 bytes. Per-instruction unique temporaries are discarded
after that instruction. Concrete math is unsigned two's-complement modulo the
output width. Extension/truncation is explicit. Shift counts at least the bit
width produce zero except arithmetic right shift, which produces the all-sign-
bit result.

Node state is sparse. An unevaluated predecessor is lattice bottom `UNSEEN`.
Once evaluated, a node stores only concrete register cells; every omitted cell
is implicitly `UNKNOWN`. Roots therefore begin with every register unknown;
committed roles select nodes/sinks and never invent register values. Merge
predecessors in canonical order: ignore unevaluated predecessors; one concrete
survives; identical concretes survive; any evaluated implicit unknown or
different concrete yields implicit unknown. Defer a non-root until at least one
predecessor is evaluated. Evaluate P-code in index order with fresh temporaries.
Enqueue canonical successors after an out-state first appears or changes, but
never duplicate an already queued node. A cell may only remain concrete, change
concrete value to implicit unknown, or remain unknown across revisits; an
unknown-to-concrete revisit is a refusal.

Each evaluated node retains sparse concrete merged-input and out-state maps;
the previous merged-input map is the comparison baseline for the next revisit.
The total concrete cells retained across both map kinds is capped at 1,048,576.
If a deterministic update would exceed it, discard that tentative
node update, append `STATE_CELL_CAP` after its transfer events, set
`state_cell_cap_hit`, do not expand that node, and return a non-exhaustive
success record. Terminal hashing enumerates only stored concrete cells and
binds the literal policy tag `implicit-evaluated-cell=UNKNOWN`; it never
materializes a node-by-key product. This sparse representation plus the cap is
the required storage bound. Fixtures must include a second predecessor that
arrives late in multiple insertion orders: equal constants remain concrete and
different/implicit-unknown inputs converge to unknown.

## Frozen commitments and ordering

All variable fields are `frame(x) = u32be(byte_length) || bytes`. Text is strict
UTF-8; enums/domain tags are ASCII; offsets/counts are u64be; widths are u32be;
booleans are one byte `0x00`/`0x01`; concrete values are width-sized unsigned
big-endian. An address payload is `frame(space) || u64be(offset)` and a state-key
payload is `frame(address-payload) || u32be(width)`. Address order compares
space UTF-8 bytes lexicographically, then offsets unsigned.

The option namespace and six distinct option keys are runtime inputs. Every
phase requires exactly one address for each role in this closed order:
`WINDOW_START`, `WINDOW_END`, `CALLER`, `NVRAM_REFERENCE`, `TARGET`,
`DISPATCH_ROOT`. The candidate commitment is SHA-256 of
`frame("gemini-fw-candidates-v1")`, the framed namespace, then framed
`role,key,address-payload` triplets in role order. The window commitment is
SHA-256 of `frame("gemini-fw-window-v1")`, framed address space/start/end,
u64be byte length and initialized/readable/executable booleans. It reads no
block bytes. Both expected lowercase digests must be frozen independently in
the later analysis contract; the tool refuses a mismatch and does not claim
that caller-supplied commitments are independently authoritative.

Reference-kind precedence is `isCall -> CALL`, then `isJump -> JUMP`, then
`isData -> DATA`, else `OTHER`. Kind order is `CALL,JUMP,DATA,OTHER`. Hit order
is `DIRECT_CALL,DIRECT_JUMP,INDIRECT_CONCRETE,INDIRECT_UNKNOWN,DATA_REFERENCE,
OTHER_REFERENCE`. Direct kinds map positionally to the corresponding direct,
data or other hit. A concrete `CALLIND`/`BRANCHIND` equal to committed caller or
target is `INDIRECT_CONCRETE`; a non-concrete sink is `INDIRECT_UNKNOWN`; a
concrete other address is recorded but not a hit. No name/text heuristic is
permitted.

For indirect equality, the adapter tags the sink with the containing
instruction's address space. Its value is an address only when the P-code input
width equals that address space's pointer width and its unsigned value is a
valid offset in that space. Equality then requires identical address-space
UTF-8 bytes and unsigned offset. A width/offset mismatch is `INVALID_WIDTH`
and cannot be an indirect concrete hit; no truncation, extension or default-
space substitution is allowed.

## Frozen event and output protocol

Event SHA-256 domain is `gemini-fw-events-v1`; terminal SHA-256 domain is
`gemini-fw-terminal-v1`. Hash input starts with the framed domain tag. Each
event begins with its framed variant and then these framed fields in order:

- `NODE(phase,address,first_dequeue,expanded)`
- `CAP(phase,cap_name,address_or_NONE,count)`
- `UNKNOWN(phase,node,pcode_index_or_NONE,state_key_or_NONE,reason)`
- `TRANSFER(phase,node,pcode_index,opcode,state_key_or_NONE,lattice,value_or_NONE)`
- `SINK(phase,node,pcode_index,opcode,lattice,value_or_NONE,hit_or_NONE)`
- `EDGE(phase,source,target)`
- `REFERENCE(phase,source,target,kind,hit_or_NONE)`

For one dequeue, emit `NODE` first; if it hits a node/revisit cap, emit `CAP`
and stop. Otherwise, for each P-code op emit at most one `UNKNOWN` for its
single output and at most one for its indirect sink, then at most one
`TRANSFER`, then at most one `SINK`.
Propagation merge-created `UNKNOWN` events occur immediately after `NODE`,
before P-code, in state-key order.
After all P-code, emit unique outgoing `EDGE` events in canonical target order.
Reference events occur only after canonical tuple sorting. A 65th-reference
peek emits `CAP(phase,TARGET_REFERENCE_CAP,NONE,64)` after reference 64. A state
cell overflow emits `CAP(phase,STATE_CELL_CAP,node,1048576)` after the tentative
node's transfer/sink events and before any edges. P-code indices/counts are
u64be. Opcode order is the supported-opcode order in the sparse propagation
section followed by `UNSUPPORTED`; an unlisted P-code operation is emitted only
as `UNSUPPORTED`, never with a tool-dependent mnemonic or integer. Cap names
are exactly `TARGET_NODE_CAP`, `TARGET_REFERENCE_CAP`, `INCOMING_NODE_CAP`,
`INCOMING_REVISIT_CAP`, `STATE_CELL_CAP`. Unknown reasons are exactly
`UNSUPPORTED_OPCODE`, `UNSUPPORTED_VALUE_SPACE`, `INVALID_WIDTH`,
`UNKNOWN_OPERAND`, `INDIRECT_SINK_UNKNOWN`, `MERGE_CONFLICT`,
`MERGE_IMPLICIT_UNKNOWN`. The first five are transfer reasons; each emitted
transfer-reason event increments `unknown_transfer_count` once. The last two
are join reasons; each emitted join-reason event increments
`unknown_join_count` once. For an output or sink with multiple applicable
failures, emit only the first in this priority order: `INVALID_WIDTH`,
`UNSUPPORTED_OPCODE`, `UNSUPPORTED_VALUE_SPACE`, `UNKNOWN_OPERAND`,
`INDIRECT_SINK_UNKNOWN`; operand insertion order never changes multiplicity.
Output events name the output key and sink events use key `NONE`. Emit one join
unknown only when a node's previously retained merged-input concrete cell is
removed on revisit. Use `MERGE_CONFLICT` when evaluated predecessors provide
different concretes; otherwise use `MERGE_IMPLICIT_UNKNOWN` when any evaluated
predecessor omits the cell. Conflict has precedence. No event is emitted for a
first evaluation, an unevaluated predecessor or a key already implicit unknown;
the monotonicity rule permits at most one join event per node/key. Join events
use P-code index `NONE`; all other unknowns use the producing/consuming P-code
index. `NONE`, lattice, opcode, reason, phase and cap name are closed ASCII
enums.

Terminal input begins with framed `implicit-evaluated-cell=UNKNOWN`, followed
by `NODE_STATE(node,EVALUATED)` for every evaluated node sorted by address,
including a node with no concrete cells, immediately followed by that node's
stored `CELL(node,state_key,CONCRETE,value)` records sorted by key. Unevaluated
nodes have no marker. Residual `QUEUE(address)` records follow in FIFO order
after a cap. An empty event or cell sequence still hashes its domain and policy
tags.

The only script-owned output is one UTF-8 JSON line with no insignificant
whitespace and one trailing newline. Success uses exact integers
`schema_version:1`, string `tool_version:"1.0.0"`, string `status:"success"`,
then keys in this exact order: `phase`, `candidate_commitment_match`,
`window_commitment_match`, `root_count`, `dequeued_node_count`,
`revisit_dequeues`, `unique_edge_count`, `unique_reference_count`,
`unknown_transfer_count`, `unknown_join_count`, `target_node_cap_hit`,
`target_reference_cap_hit`, `incoming_first_dequeue_cap_hit`,
`incoming_revisit_cap_hit`, `state_cell_cap_hit`, `queue_exhausted`,
`hit_counts`, `event_digest`,
`terminal_state_digest`. Counts are nonnegative
decimal integers, booleans JSON booleans and digests lowercase 64-hex. The
`hit_counts` object uses the six-category order above. Non-applicable cap flags
are false. `queue_exhausted` is true only when the selected worklist converges
empty without an operational cap; for admitted `incoming-direct`, it is true
after its complete bounded reference inventory is processed.

A refusal emits exactly
`{"schema_version":1,"tool_version":"1.0.0","status":"refused","reason":"CODE"}`
with a trailing newline and no partial counts/digests. Closed codes are
`ARGUMENT_COUNT`, `PHASE`, `COMMITMENT_FORMAT`, `OPTION_NAMESPACE`,
`DUPLICATE_OPTION_KEY`, `MISSING_OPTION`, `MALFORMED_OPTION`,
`AMBIGUOUS_ADDRESS`, `CANDIDATE_COMMITMENT`, `WINDOW_COMMITMENT`,
`WINDOW_METADATA`, `WINDOW_SIZE`, `INSTRUCTION_INVENTORY`,
`REFERENCE_INVENTORY`, `REGISTER_KEY_INVENTORY`, `ROOT_INVENTORY`,
`INCIDENT_EDGE_INVENTORY`, `ROOT_OUTSIDE_WINDOW`, `ROOT_NOT_INSTRUCTION`,
`STATE_MONOTONICITY`, `INTERNAL`. Controlled refusals print no exception,
address, option, path or partial result. Because GhidraScript does not provide a
portable process-exit contract, the record status is authoritative; a supplied
pure-Java verifier must return nonzero for `refused` or malformed records.

## Capability, validation and handoff

- **Read-only capability:** the adapter may import only `GhidraScript`,
  `Program`, `Options`, `Listing`, `Instruction`, `PcodeOp`, `Varnode`,
  `Memory`, `MemoryBlock`, `ReferenceManager`, `Reference`, `RefType`,
  `AddressFactory`, `Address`, `AddressSpace` and pure Java value/collection,
  UTF-8, SHA-256 and JSON/string output helpers. README must list every invoked
  Ghidra method and map it to arguments/current-program access or option,
  listing, flow, P-code, memory-block metadata, reference, address or sanitized
  output reads. Transactions, save, analysis commands, disassembly, memory-byte
  reads/writes, option setters, symbol/function/data creation, rename,
  map/block mutation, bookmark/property/comment/annotation, reflection,
  dynamic process/network and file-write APIs are forbidden. Static fixtures
  inject a representative of every forbidden family and must refuse it.
- **Model route:** Luna High (`gemini_implementer`, `gpt-5.6-luna`, high) for
  bounded implementation; Sol Medium (`gemini_reasoner`, `gpt-5.6-sol`,
  medium) for pre-dispatch and final review. Astra remains reserved for the
  later private interpretation, not this tool implementation.
- **Stop/escalation:** stop after two failed implementation repairs, any unclear
  Ghidra read API, inability to prove the positive capability boundary, need
  for private input, output leak or scope expansion. Return evidence, attempts,
  unresolved question and next discriminating check; do not weaken a cap or
  schema to pass tests.
- **Parent:** `ab0e0bacc38f4774556dba02015491ae844cec02`. The prior stopped
  tooling candidate is immutable escalation evidence; this candidate does not
  resume it.
- **Dependencies:** public Ghidra 12.1.2 Java API and Java toolchain only.
  Locate the installed API read-only and do not publish its machine path. Do
  not open a private program/database or read the retained firmware directory.
  Network access is unnecessary.
- **Worktree:** current small repository checkout; no Linux source or second
  worktree.
- **Validation:** strict-warning compile and execution of pure-Java tests;
  insertion-order permutations; unsigned signed-boundary ordering; FIFO and
  every exact cap boundary; duplicate collapse; kind precedence; sparse cell
  bound; equal/different/implicit-unknown and delayed-predecessor joins; all
  opcode/refusal/output schemas; digest golden vectors; unchanged controls
  before/after mutation; assertions-disabled behavior; positive import/method
  audit and forbidden-family injections. Compile-check the adapter against the
  installed Ghidra 12.1.2 API without opening a program. If it cannot be
  located, stop instead of claiming compatibility. Run source-rights,
  sensitive/private-path/address, link, whitespace and repository checks.
- **Hardware:** none. No Gemini SSH, firmware execution/loading, MMIO, radio,
  boot, partition, power or device action. The RE VM may only supply the
  program-free compile check and is not a kernel-build backend.
- **Upstream:** analysis tooling only; no Linux patch, vendor code, firmware
  right, regulatory policy, hardware claim or DCO certification.
- **Owner-away work:** the synthetic implementation and review can finish
  offline. Completion only permits a new separately contracted Astra analysis.
- **Device readiness:** not applicable.
- **Handoff:** exact parent/paths and source hashes; CLI/options; golden schema
  and digest vectors; strict host and mutation outputs; program-free Ghidra
  compile evidence; positive capability and forbidden-family results; rights,
  sensitive-data and link scans; known limits; explicit no-private/no-device
  confirmation.
- **State:** blocked before implementation. Contract drafted at
  `2026-09-06T06:31:16Z`; pending Sol Medium
  pre-dispatch review. Review at `2026-09-06T06:34:51Z` accepted the sparse
  bound and outer protocol but required exact role/stage behavior, closed
  unknown/cap semantics and an evaluated-node terminal marker; repair 1 applies
  those changes. Review at `2026-09-06T06:37:29Z` then required consistent role
  admission, one UNKNOWN precedence, bounded prior-merge semantics, exact root
  counts and indirect address normalization; repair 2 applies those changes at
  `2026-09-06T06:39:44Z`. Final allowed review at
  `2026-09-06T06:40:54Z` found incomplete mixed source-SCC initialization, a
  missing P-code-inventory refusal code and ambiguous input/out-state terminal
  hashing. The two-repair stop is active. Implementation did not start; no
  private program, VM or device was accessed.
- **Efficiency loop:** if the completed handoff is accepted, append one observed
  offline-item measurement to the active workflow ledger. Credits are measured
  or unavailable, never estimated.

## Escalation packet

- **Evidence:** the final Sol review accepted the sparse storage bound,
  role/phase mapping, UNKNOWN precedence, retained prior-merge semantics,
  root/dequeue fields, indirect-address normalization, read-only boundary and
  no-private/no-device scope, but identified three remaining correctness gaps.
- **Attempts:** repair 1 froze role/stage behavior, closed unknown/cap enums and
  evaluated-node terminal markers. Repair 2 made role admission consistent,
  bounded prior-merge state, defined UNKNOWN precedence and fixed root, node
  and indirect-address semantics.
- **Unresolved question:** how should source strongly connected components be
  seeded so every admitted predecessor contributes conservatively, and should
  terminal hashing bind merged input, output or both without ambiguity?
- **Next discriminating check:** only a fresh, explicitly reviewed item may add
  deterministic source-SCC seeding, a `PCODE_INVENTORY` refusal and a closed
  terminal map-kind contract. Do not dispatch or repair this candidate again.
