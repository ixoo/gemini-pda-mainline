# MT6797 retained WLAN bounded AArch64 instruction attribution

- **Outcome:** use the independently accepted Kallsyms inspection envelopes to
  determine whether the retained binary contains reachable direct AArch64 call
  edges `do_connectivity_driver_init -> do_wlan_drv_init ->
  mtk_wcn_wlan_gen3_init`, classify the reachable direct callees of
  `mtk_wcn_wlan_gen3_exit`, and enumerate aligned `BL`-encoding and exact
  address-word candidates that reference the exit entry. Return a bounded
  unresolved result for any edge whose code reachability, caller boundary or
  indirect ownership cannot be proved. This is static attribution only: it does
  not establish exact function ends, runtime invocation, safe teardown,
  synchronization, resource release, firmware success or radio operation.
- **Parent and start:** repository commit
  `e25df337406b52bc4da44aa428262a8123d8da21`; work start
  `2026-09-07T01:36:36Z`. Verify all exact dependency hashes in `inputs.json`
  before private-content access. The accepted v3 interval record is the sole
  source of target ranges. Earlier excluded parser tuples/raw outputs must not
  be read, compared or used.
- **Frozen private input:** the sole existing retained reconstructed ELF in the
  approved RE-VM workspace, SHA-256
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`.
  Require ELF64, little endian, AArch64, `ET_EXEC`, the recorded Linux
  `3.18.41+` family and exact `.kernel` section tuple from `inputs.json` before
  reading instruction content. Do not reconstruct, copy or export the ELF,
  instruction bytes, disassembly or an analysis database.
- **Owner and reviewer:** Astra Medium owns the instruction-boundary and
  static-control-flow uncertainty. Sol Medium independently reviews the frozen
  result; `/root` integrates. The owner is not alone in the worktree and must
  preserve all other changes.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for the named
  binary-control-flow uncertainty; `gemini_reasoner`, `gpt-5.6-sol`, medium for
  independent review. No implementation route is selected.
- **Owned scope:** create only this experiment's `README.md`, `inputs.json`,
  `method.json`, `analysis.json`, `edges.json`, `FREEZE.md`, an assert-free
  normal/optimized verifier and `VALIDATION.md`. Raw outputs stay in a fresh
  mode-0700 RE-VM child with mode-0600 files. Do not edit dependencies,
  hardware/support facts, roadmap, queue, workstreams, workflow ledger,
  configs, manifest, series or patches.
- **Tool and method freeze:** use the approved `./scripts/dev-vm re-shell`
  path with debuginfod, network and automatic plugin/download behavior
  disabled. Before private ELF content access, record Python, pyelftools and
  Capstone versions plus exact nonsymlink module/native-library/executable
  hashes and sizes for every selected decoder component. Stop on an unresolved
  origin, symlink, absent digest, dependency outside the installed environment
  or source/tool drift. Freeze the complete independently written collector,
  ELF mapper, raw AArch64 branch decoder and control-flow traversal source in
  `method.json`, with SHA-256 values, before content. Syntax-checking the frozen
  scripts is permitted before content; do not run them against another binary.
- **Execution guard:** install a child-process audit hook before private reads.
  Permit read-only opens of the exact retained ELF and exact frozen installed
  tool files only. Reject filesystem writes, socket/DNS, subprocess/shell,
  dynamic library/plugin discovery outside the frozen set and any unexpected
  read. The outer collector may write only the two named private pipe captures.
  Record guard attempts and unchanged admitted-file identities afterward.
- **Exact bytes and mapping:** independently parse and cross-check the ELF
  header, section table, `.kernel` file-offset/virtual-address mapping and
  symbol-table starts. For each of the four accepted half-open ranges, require
  exact start/end/length from the hash-pinned `intervals.json`, four-byte
  alignment, complete containment in `.kernel`, a file-backed byte for every
  address and the accepted retained-ELF start equality. Record only byte-range
  SHA-256 and size, never bytes. The next distinct symbol is a conservative
  inspection boundary, not an exact end.
- **Dual decoding:** decode each four-byte-aligned word with the frozen
  Capstone engine and an independent fixed-mask AArch64 control-flow decoder.
  Require exact address, width four, mnemonic/control-flow class and immediate
  target agreement for `B`, `BL`, `B.cond`, `CBZ/CBNZ`, `TBZ/TBNZ`, `BR`,
  `BLR`, `RET` and exception/terminal instructions. Stop a target's semantic
  analysis on an undecodable word, width drift, disagreement, unclassified
  Capstone jump/call/return/interrupt, or target arithmetic outside signed
  AArch64 encoding rules. Non-control instructions fall through exactly four
  bytes; their other semantics are not inferred.
- **Reachability traversal:** start solely at each accepted target entry and
  traverse basic blocks within its accepted range. Follow fallthrough and every
  direct conditional/unconditional in-range target. A reachable `BL` records a
  direct call and continues at fallthrough; a reachable `B` outside the range
  records only a tail-branch candidate and ends that path. `RET`, exception and
  direct nonreturn exits end a path. `BR` ends a path unresolved; `BLR` records
  an unresolved indirect call and continues. Refuse a complete-body or return
  claim if any reachable path crosses/falls through the exclusive boundary,
  targets a nonaligned/interior-unmapped address, encounters unknown control
  flow, overlaps inconsistently or exceeds the finite block/instruction cap.
  Unreachable decoded words remain data-or-code unknown and cannot support an
  edge.
- **Direct-edge rule:** a direct call is admitted only for a reachable `BL`
  whose independently decoded immediate target exactly equals a retained
  symbol start. The two init-chain edges require exact target equality to the
  accepted v3 entries. For the exit envelope, record every reachable direct
  callee, exact callsite/target/symbol and whether all paths are contained; do
  not infer callee effects, completion or cleanup safety. At most sixteen
  reachable direct calls may be published across the four envelopes; stop on
  overflow.
- **Whole-section exit scan:** scan every four-byte-aligned word of the exact
  `.kernel` bytes once with the independent raw `BL` mask and signed target
  arithmetic. Enumerate only words targeting the exact
  `mtk_wcn_wlan_gen3_exit` entry. These are `BL`-encoding candidates, not calls,
  unless their address is in the proved reachable set of one of the four
  accepted traversals. Record total scanned words and candidate count; publish
  at most eight candidate addresses with nearest reconstructed symbol labels
  clearly marked non-boundary/non-reachability metadata. Stop rather than
  expand if candidate count exceeds eight.
- **Bounded indirect-reference scan:** enumerate ELF relocation records whose
  resolved symbol/addend names or value exactly target the exit entry, and scan
  eight-byte-aligned words of each file-backed `SHF_ALLOC` section for the exact
  little-endian exit address. Record section/count and at most eight candidates.
  These are relocation or raw-address candidates, never proof of address-taking,
  callback registration or execution. ADR/ADRP arithmetic, jump tables,
  unaligned constants and arbitrary dataflow are outside scope. Zero candidates
  proves absence only in these stated encodings. Stop on overflow or ambiguous
  relocation interpretation.
- **Bounds:** one ELF, four accepted envelopes totaling 1,568 bytes, four entry
  traversals, at most 512 reachable instruction addresses and 128 basic blocks
  per target, sixteen published reachable direct calls, one aligned raw-BL scan
  of the exact `.kernel` section, one relocation scan and one aligned exact
  address-word scan of file-backed allocated sections. At most eight exit
  candidates per scan class. No additional caller body, whole-program
  recursive traversal, generic xref engine, source fetch/search, prior raw
  output, architecture signature classifier, decompilation, reconstruction,
  device, network or build.
- **Acceptance predicates:** establish independently: all frozen identities;
  exact file/virtual mapping and byte hashes; decoder agreement; bounded
  traversal completeness or precise per-target refusal; each reachable direct
  call; both binary init-chain edges or their exact missing condition; reachable
  exit-body callees; whole-section exact-exit `BL`-encoding candidates; bounded
  relocation/address-word candidates; and the strongest teardown conclusion
  without indirect/runtime/safety promotion. A negative/no-candidate result is
  acceptable when the complete bounded scan passes.
- **Refusal and validation:** reject identity, interval, mapping, tool/method or
  byte-hash drift; exact-end language; decode disagreement; unrecognized control
  flow; boundary fallthrough; unproved reachability; candidate-to-call
  promotion; omitted candidates; cap overflow; prior-output dependency;
  private bytes/paths; mutable expected digests; or runtime/resource/firmware/
  radio authority. Freeze `method.json`, then the result JSON files, before
  writing the verifier. Normal and `-O` modes must use active checks and
  mutations covering identity, chronology, mapping, byte hashes, tool method,
  decoder agreement, traversal, each edge/candidate, bounds and authority.
- **Rights and privacy:** the retained ELF and decoded bytes are private
  evidence. Publish only identities, hashes, addresses, symbol names, bounded
  instruction/control-flow counts, candidate classes and independently worded
  conclusions. No instruction bytes, full/long disassembly, private paths,
  credentials, identifiers, calibration or proprietary content.
- **Hardware/build effects:** none. Device remains known-good Gemian with
  custody released. No SSH/device, boot2, firmware/radio, Buildbox or kernel
  build action is admitted.
- **Stop/escalation:** stop on any mismatch, tool acquisition, method ambiguity,
  decode/control-flow conflict, boundary or candidate overflow, need for another
  function/source/input, or conflict with accepted evidence. Return exact
  evidence, attempts, unresolved question and next discriminating check; do not
  repair with a second analysis run or inference.
- **Handoff:** exact parent/dependency/ELF/tool/method identities; guard and
  chronology counts; per-target mapping/hash/traversal status; reachable direct
  edge inventory; exit `BL`/relocation/address candidate counts; raw-log hashes;
  mutation counts; limitations; review-ready UTC; and whether init linkage and
  a direct or indirect teardown join are proved, partially bounded or missing.
- **Efficiency loop:** if independently accepted, append one sanitized item to
  the active workflow cohort with actual routes/timestamps, first-review result,
  rework/escalation and measured credits or explicit unavailability.
- **State:** frozen for one offline specialist dispatch; no device action.
