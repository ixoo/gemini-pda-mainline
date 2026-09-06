# Work item: deterministic read-only firmware traversal tooling

- **Outcome:** add independently written, reusable Ghidra tooling that can
  satisfy the deterministic traversal and accounting prerequisites which
  stopped the retained-firmware handler-attribution experiment. This item ends
  with a reviewed tool and synthetic evidence only; it does not run either
  private analysis branch or make a firmware, calibration, policy, runtime or
  hardware claim.
- **Owner and reviewer:** a Luna High implementer owns only this experiment;
  `/root` integrates; Sol Medium performs contract and final integration
  review. The worker is not alone in the repository and must preserve all
  concurrent or unrelated edits.
- **Scope:** create this experiment's README, original MIT-licensed Java source,
  deterministic synthetic fixtures, offline validators and results. The
  implementation must be generic: no firmware bytes, private addresses,
  artifact or database names, stored candidate values, instruction listings,
  strings, calibration data, personal paths or copied vendor/private script
  content. Do not edit the stopped experiment, shared manifests, patch series,
  roadmap, support matrix, hardware facts, workflow ledger or agent settings.

  Supply a pure-Java traversal core and a thin Ghidra 12.1.2 script adapter.
  The adapter may read an already-open program, its established instruction
  boundaries, references, flow edges, read-only P-code and caller-supplied
  program-option keys;
  it must never create, rename, disassemble, analyze, map, bookmark, annotate,
  save or otherwise mutate the program/project. Candidate option values are
  read only and accepted only when all required values exist, parse uniquely,
  lie in the caller-selected memory block and match a caller-supplied SHA-256
  commitment over the canonical encoding below. Option keys and values are
  runtime inputs and never embedded in Git. The expected candidate and window
  commitments must be independently frozen by the owning analysis contract;
  the adapter refuses their mismatch but does not itself prove independence.

  Implement exactly four separately selectable phases matching the stopped
  branch attempts: `target-cfg` traverses at most 4,096 nodes;
  `target-references` deterministically reconstructs that CFG and classifies at
  most 64 one-level references without entering callees; `incoming-direct`
  enumerates direct references/call targets to the retained caller and target;
  and `incoming-predecessor` performs a predecessor/constant-propagation search
  of at most 16,384 nodes. The phase enum is closed and no invocation combines
  phases. Preflight structurally refuses, with no measurement record, a
  selected window larger than 16 MiB, more than 1,048,576 established
  instruction boundaries, more than 262,144 direct references in the window,
  more than 65,536 distinct register-state keys, more than 16 roots, or more
  than 4,096 edges incident on one node. These are input-admission limits, not
  reportable traversal-cap hits. Inventories are streamed in deterministic
  order or counted against those limits; they are never first accumulated in
  an unbounded collection. Initial roots and
  instruction boundaries use unsigned-address order. Worklists are FIFO;
  unique successors or predecessors are enqueued in unsigned-address order;
  a node is counted when first dequeued; and a cap node is recorded but not
  expanded. Deduplicate references by `(source,target,reference-kind)` and
  process them in unsigned source, unsigned target, then reference-kind order.
  Constant propagation uses that same deterministic queue/order, joins only
  identical concrete values and changes disagreement or unsupported transfer
  to unknown without guessing. Reject altered cap arguments (the caps are not
  configurable), malformed commitments, missing/duplicate/ambiguous candidates,
  roots outside the selected block,
  non-instruction roots, cross-block traversal, malformed options and any phase
  outside the closed enum.

  Constant propagation operates only in `incoming-predecessor`. Its inter-node
  state maps `(address-space UTF-8 bytes, unsigned 64-bit offset, byte width)`
  register locations to the closed lattice `UNSEEN`, `CONCRETE(width,value)` or
  `UNKNOWN`; unique-space temporaries exist only while evaluating one
  instruction. Widths must be 1 through 8 bytes. Concrete arithmetic is
  unsigned two's-complement modulo `2^(8*width)`; extension/truncation is
  explicit. Shift counts at least the bit width yield zero except arithmetic
  right shift, which yields the all-sign-bit result. The supported read-only
  P-code transfer set is `COPY`, `INT_ZEXT`, `INT_SEXT`, `INT_ADD`, `INT_SUB`,
  `INT_MULT`, `INT_AND`, `INT_OR`, `INT_XOR`, `INT_LEFT`, `INT_RIGHT`,
  `INT_SRIGHT`, `PTRADD`, `PTRSUB`, `MULTIEQUAL`, `BRANCHIND` and `CALLIND`.
  Constants and known registers are concrete inputs; RAM, stack and external
  values, loads, calls, userops, malformed widths and every unlisted opcode
  produce a counted unknown for the affected output or indirect sink without
  reading memory bytes or guessing clobbers. A direct call is a boundary and
  is not entered.

  Graph discovery freezes the canonical predecessor set and the complete
  register-key universe before propagation. Every evaluated node materializes
  a state for every key. Root input keys start `UNKNOWN`; committed candidate
  roles select nodes and sinks, not invented register values. An unevaluated
  predecessor contributes lattice bottom `UNSEEN`, while an evaluated
  predecessor's absent or unsupported value is explicitly `UNKNOWN`.
  Predecessor out-states are merged in canonical predecessor order immediately
  before evaluation with `UNSEEN` as bottom and `UNKNOWN` as top: bottom joined
  with a value yields that value; identical concretes remain concrete;
  differing concretes or any join with `UNKNOWN` becomes `UNKNOWN`. A non-root
  with no evaluated predecessor is deferred, not evaluated.

  Evaluate each instruction's P-code in sequence order, using fresh per-node
  unique temporaries, then compare its complete out-state. Enqueue canonical
  successors when the out-state first appears or changes. The FIFO begins with
  roots in canonical order. Later predecessor changes enqueue a successor only
  if it is not already queued. A node contributes to the 16,384-node cap only
  on its first dequeue; later fixpoint dequeues increment a separate
  `revisit_dequeues` counter capped at 65,536. Across repeated evaluations, an
  input or output cell may change only `UNSEEN -> CONCRETE -> UNKNOWN` or
  `UNSEEN -> UNKNOWN`; an instruction overwrite computes its new output from
  the current input state, but a purported reverse transition is a refusal.
  Reaching the first-dequeue or revisit cap records that dequeued node and a
  cap event but does not evaluate or expand it. Queue exhaustion means the FIFO
  is empty after convergence without any traversal-cap hit. Fixtures must
  include a join whose second predecessor arrives later, in permuted insertion
  orders, and prove that two identical constants remain concrete.

  Canonicalization is fixed, not adapter-selected. Address order is unsigned
  lexicographic order of `(address-space UTF-8 bytes, unsigned 64-bit offset)`.
  Reference kinds use the closed order `CALL`, `JUMP`, `DATA`, `OTHER`, derived
  only from read-only `RefType` predicates; duplicates normalize to one exact
  tuple before counting. Candidate roles use the closed order `WINDOW_START`,
  `WINDOW_END`, `CALLER`, `NVRAM_REFERENCE`, `TARGET`, `DISPATCH_ROOT`, with
  exactly one value for every role in every phase and no duplicate option key.
  The option namespace and all six keys are runtime inputs. A
  candidate commitment is SHA-256 over the ASCII domain tag
  `gemini-fw-candidates-v1`, then the option namespace followed by every role,
  option key and normalized address in role order. The window commitment uses domain tag
  `gemini-fw-window-v1`, address-space, start, end, byte length and the
  initialized/readable/executable flags; it reads no block bytes. Every field
  is framed as a four-byte unsigned big-endian byte length followed by bytes;
  enum text is ASCII, text is strict UTF-8, offsets/lengths are unsigned
  eight-byte big-endian and booleans are one byte. Event and terminal streams
  use the same framing and canonical enum/address/value encodings. Hit
  categories have the closed order `DIRECT_CALL`, `DIRECT_JUMP`,
  `INDIRECT_CONCRETE`, `INDIRECT_UNKNOWN`, `DATA_REFERENCE`, `OTHER_REFERENCE`.
  SHA-256 covers the domain tag plus the entire framed stream, including an
  empty stream. Only the digest, never its preimage, is emitted.

  An address field payload is `frame(space UTF-8) || u64be(offset)`; a state-key
  payload adds `u32be(width)`. Reference classification tests predicates in
  precedence order `isCall`, `isJump`, `isData`, then `OTHER`. Hit categories
  follow directly: `CALL -> DIRECT_CALL`, `JUMP -> DIRECT_JUMP`,
  `DATA -> DATA_REFERENCE`, and `OTHER -> OTHER_REFERENCE`; a matching concrete
  `CALLIND` or `BRANCHIND` sink is `INDIRECT_CONCRETE`, while a non-concrete
  indirect sink is `INDIRECT_UNKNOWN`. A concrete indirect value that does not
  equal a committed caller or target is not a hit but remains in the event
  digest. No text/name heuristic participates.

  The event stream is append-only in actual algorithm order and has exactly
  these variants and field order, each field framed: `NODE(phase,address,
  first-dequeue,expanded)`, `EDGE(phase,source,target)`, `REFERENCE(phase,
  source,target,reference-kind,hit-category-or-NONE)`, `TRANSFER(phase,node,
  pcode-index,opcode,output-state-key-or-NONE,lattice,value-or-NONE)`,
  `SINK(phase,node,pcode-index,opcode,lattice,value-or-NONE,hit-category-or-
  NONE)`, `UNKNOWN(phase,node,pcode-index,reason)` and `CAP(phase,cap-name,
  address,count)`. Booleans are ASCII `true`/`false`; counts and P-code indices
  are u64be; concrete values are width-sized unsigned big-endian bytes;
  `NONE`, lattice, opcode, reason, phase and cap names are closed ASCII enums.
  Reference events occur after canonical tuple sorting. Transfer events occur
  in P-code order. The terminal-state stream sorts evaluated nodes by address,
  then all materialized cells by state-key order, and encodes exactly
  `CELL(node,state-key,lattice,value-or-NONE)` followed by
  `QUEUE(address)` entries in FIFO residual order when a cap stops traversal.

  The one-line aggregate is UTF-8 JSON with no insignificant whitespace, a
  trailing newline, decimal nonnegative integers, lowercase 64-character
  digests and exactly this key order: `schema_version`, `tool_version`, `phase`,
  `candidate_commitment_match`, `window_commitment_match`, `root_count`,
  `dequeued_node_count`, `revisit_dequeues`, `unique_edge_count`,
  `unique_reference_count`, `unknown_transfer_count`, `unknown_join_count`,
  `target_node_cap_hit`, `target_reference_cap_hit`,
  `incoming_first_dequeue_cap_hit`, `incoming_revisit_cap_hit`,
  `queue_exhausted`, `hit_counts`, `event_digest`, `terminal_state_digest`.
  `hit_counts` is an object in the six-category order above. Non-applicable cap
  flags are false. For node caps, the cap-th first/revisit dequeue is counted,
  digested and not evaluated or expanded. For the 64-reference cap, the 64th
  unique canonical reference is classified and digested; the flag is true only
  if a 65th exists, which is neither processed nor digested. Every cap flag
  names the exact stopped dimension; there is no singular `cap_exhausted` or
  `inventory_exhausted` field.

  Output only one canonical sanitized aggregate record: schema/tool version,
  phase, candidate-commitment and window-commitment match booleans, root count,
  dequeued-node count,
  unique-edge/reference counts, unknown-transfer and unknown-join counts,
  fixed per-phase cap flags and queue-exhausted boolean, revisit-dequeue count,
  hit-category counts in the closed order and SHA-256
  digests of canonical ordered event/terminal-state streams.
  It must not print addresses, option keys/values, symbols, strings, bytes,
  disassembly, paths or raw exception text. Refusal exits nonzero and emits a
  closed reason code with no partial measurements. No report field may assert
  target semantics, record application or source precedence.
- **Model route:** Luna High (`gemini_implementer`, `gpt-5.6-luna`, high) for
  bounded implementation; Sol Medium (`gemini_reasoner`, `gpt-5.6-sol`,
  medium) for contract and final review. This is tooling construction, not the
  hard firmware interpretation reserved for a later Astra Medium item.
- **Stop/escalation:** stop after two failed repair attempts, on unclear Ghidra
  API semantics, inability to prove read-only behavior, a need for private
  inputs, or any required scope expansion. Return evidence, attempts, the
  unresolved question and next discriminating check. Do not weaken the stopped
  experiment's traversal contract to make a fixture pass.
- **Parent:** repository commit
  `414c7128774cf8ac9a07c0423c0b5beb7034ed5d`. The motivating sanitized stop
  receipt is
  `experiments/2026-09-06-mt6797-firmware-nvram-handler-attribution/results/attribution.json`
  at SHA-256
  `826fa707817d1743e2ba25f35fd2e427cbcc3f9db5b9df12b9875b83a3b5e6d9`;
  verify this identity before implementation. It is context only and must not
  be modified or imported into fixtures.
- **Dependencies:** Ghidra 12.1.2's public Java API and a Java toolchain for
  compile checks. Discover any Ghidra installation and repository mount
  read-only; do not publish machine-specific locations. No private firmware,
  retained analysis directory, database or program may be opened in this item.
  Network access is unnecessary.
- **Worktree:** the existing small repository checkout on the current topic;
  no Linux source tree and no second repository worktree.
- **Validation:** pure-Java fixtures must prove deterministic behavior across
  insertion-order permutations; unsigned ordering across the signed-long
  boundary; FIFO/count-at-first-dequeue semantics; cap-node record-without-
  expansion; duplicate-edge/reference collapse; reference tuple ordering;
  queue versus cap exhaustion; identical-value join; disagreement and
  unsupported-transfer unknown joins; and every refusal above. Add a mutation
  or refusal driver whose unchanged controls pass before and after mutations
  and whose checks remain active with Java assertions disabled and Python
  optimization if Python is used. Compile and run the core/tests with strict
  warnings. Compile-check the adapter against Ghidra 12.1.2 in the existing RE
  VM without opening a program; if the installation cannot be located, stop
  rather than fabricate compatibility. Add a static no-write scan with a
  reviewed forbidden-operation list, a public-source/provenance scan, focused
  secret/private-path/address checks, link checks and `git diff --check`.
  Read-only review is a positive capability audit, not only a denylist scan.
  The adapter may import only `GhidraScript`, `Program`, `Options`, `Listing`,
  `Instruction`, `PcodeOp`, `Varnode`, `Memory`, `MemoryBlock`,
  `ReferenceManager`, `Reference`, `RefType`, `AddressFactory`, `Address`,
  `AddressSpace`, Java immutable/value collections, JSON/string/number helpers
  and SHA-256/UTF-8/I/O needed to emit the one record. Freeze in the README
  every invoked method and verify it belongs to this read capability: script
  arguments/current-program access; program option, listing, memory, reference
  and address-factory getters; option lookup; instruction iteration/lookup,
  address/flow/fallthrough/P-code getters; P-code/varnode getters and type
  predicates; memory-block metadata getters/predicates; reference iteration and
  type predicates; address/address-space getters; output of the sanitized
  record; and pure Java computation. Any transaction, save, analysis command,
  disassembly, memory read/write, option setter, symbol/function/data creation,
  rename, map/block mutation, bookmark/property/comment/annotation operation or
  dynamic/reflection/process/network/file-write API is forbidden. Static
  fixtures must inject at least one representative from every forbidden family
  and prove refusal; compile success alone is not read-only evidence.
- **Hardware:** none. No Gemini SSH, MMIO, firmware loading/execution, radio,
  boot, partition, power or device action. The RE VM is used only for a
  program-free compile check and is not a kernel-build backend.
- **Upstream:** generic private-analysis support tooling only, not a Linux
  patch. It supplies no vendor code, firmware redistribution right, regulatory
  policy, runtime result or DCO certification. Remove or revise it if later
  review shows that its Ghidra contract is not genuinely read-only.
- **Owner-away work:** implementation and review can finish offline. A complete
  handoff may enable, but does not start, a separately contracted Astra Medium
  private-analysis item.
- **Device readiness:** not applicable. Synthetic traversal evidence is not a
  firmware application receipt or physical-session admission.
- **Handoff:** exact parent and changed paths; source and fixture hashes;
  documented CLI/options and output schema; strict host test output; mutation
  inventory; program-free Ghidra compile evidence; static no-write/source-
  rights/sensitive-data/link results; known limitations; and explicit
  confirmation that no private program or device was accessed.
- **State:** blocked before implementation. Contract drafted at
  `2026-09-06T06:17:57Z`. Sol Medium review at
  `2026-09-06T06:20:24Z` required hard caps/phases, implementable propagation,
  fixed canonicalization and a positive Ghidra read allowlist; repair 1 applies
  those changes. Repeat review at `2026-09-06T06:25:00Z` required separating
  preflight refusals from traversal cap reports, arrival-independent fixpoint
  joins and complete event/output schemas; repair 2 applies those changes at
  `2026-09-06T06:26:41Z`. Repeat review at `2026-09-06T06:27:49Z` left the
  total propagation-state bound and final canonical success/refusal encoding
  unresolved. The two-repair stop activated at `2026-09-06T06:28:30Z`.
  Implementation did not start; no private program, VM or device was accessed.
- **Efficiency loop:** if accepted as one offline tooling item, append its
  sanitized observed measurement to the active ledger under
  `project/workflow-improvement.json`; do not estimate credits. The comparable
  review group, if any, must be explicit and need not equal the strict settings
  tuple.

## Escalation packet

- **Evidence:** both Sol reviews accepted the parent/input identity,
  read-only capability direction, rights boundary, fixed branch caps,
  arrival-independent join scheduling and no-private/no-device scope. The
  second repeat review identified two remaining acceptance gaps in this
  contract.
- **Attempts:** repair 1 added closed phases and caps, explicit P-code/lattice
  semantics, canonical commitments and a positive Ghidra capability boundary.
  Repair 2 separated preflight refusals from per-phase cap evidence, repaired
  delayed-predecessor joins and specified event, terminal and aggregate
  encodings.
- **Unresolved question:** can the design bound total retained propagation
  state while preserving the exact join result, and freeze a complete canonical
  success/refusal protocol without turning this generic helper into a large new
  analysis framework?
- **Next discriminating check:** review a reduced sparse-state design with a
  hard total-cell cap and a complete domain-tag/version/event/refusal schema as
  a new work item. Do not resume this candidate or run private analysis from
  the present contract.
