# MT6797 `wmt_loader` ioctl static-attribution v2 work item

- **Outcome:** statically resolve or sharply bound whether the exact retained
  `system/vendor/bin/wmt_loader` issues `COMBO_IOCTL_DO_MODULE_INIT` to
  `/dev/wmtdetect`, the value supplied as its third ioctl argument, command
  ordering and how the returned aggregate is interpreted. Preserve binary
  reachability separately from runtime execution, successful initialization,
  firmware activity, radio safety and a future mainline ABI.
- **Parent and immutable inputs:** repository commit
  `65f1b43333b727f0d5bbddf900cd38486a896e4d`; direct source predecessor is
  `experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/`.
  The only retained binary admitted is logical path
  `system/vendor/bin/wmt_loader`, SHA-256
  `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`.
  Match its hash before analysis and stop on mismatch or absence. The excluded
  v1 record is chronology only; discard and do not reuse its partial tool output.
- **Repair to v1:** this is a fresh contract and budget. Use only static tools
  whose complete arguments are predeclared. Set `DEBUGINFOD_URLS` to the empty
  string. Do not use `readelf`/`objdump` debug-dump or DWARF options, including
  `-w`, `--debug-dump`, `--dwarf`, `--dwarf-depth` or `--dwarf-start`; do not
  request unwind/debug metadata. A tool message naming, opening or consulting
  any file other than the exact admitted binary is an immediate stop. Do not
  use automatic symbol servers, separate-debug lookup, build IDs or debug links.
- **Owner and reviewer:** Astra Medium owns the hard stripped-binary data-flow
  uncertainty; `/root` integrates; Sol Medium independently reviews. The owner
  may edit only this new v2 experiment directory, must not edit this frozen
  contract, and must preserve concurrent work.
- **Analysis environment and boundary:** use `./scripts/dev-vm re-shell` and
  guest-owned in-memory/temporary analysis state only. Never execute, load,
  emulate or dynamically trace the program and never invoke an ioctl. Analyze
  only `wmt_loader`; do not inventory or inspect adjacent binaries, filesystem
  content, live processes or device state. Remove bounded temporary state on
  success and failure; do not duplicate the retained binary.
- **Bounded analysis:** at most two predeclared batches, one exact admitted
  binary, 14 static-tool child invocations total and 20 ioctl call sites. Batch
  1 may use hash/file identity, non-debug ELF headers/sections, exact selected
  string-anchor lookup and disassembly only within virtual addresses
  `[0xb00,0x1200)`. Batch 2 may disassemble at most four directly reached local
  functions or literal-pool/data regions, with each interval declared from a
  batch-1 direct edge and at most 4096 bytes total. Count analyzed functions,
  call sites, basic blocks, byte intervals and every tool invocation. Stop
  rather than broaden to whole-binary decompilation, debug/unwind data, another
  binary or unrelated property/configuration paths.
- **Acceptance predicates:** classify independently with exact binary address,
  normalized semantic anchor, conditions, missing edge and next discriminator:
  1. exact identity/architecture and `/dev/wmtdetect` open-to-fd flow;
  2. exact request matching `COMBO_IOCTL_DO_MODULE_INIT` and its direct call;
  3. third-argument provenance, including whether `0x6797` is constant,
     property-derived, kernel-query-derived or otherwise conditional;
  4. ioctl return interpretation, conversion, retry, gating and process result;
  5. relative order/conditions for module init, cleanup and SDIO autok requests;
  6. compatibility observation versus a proposed mainline userspace contract,
     which stays unresolved absent an explicit standard-interface design.
- **Evidence discipline:** retain exact input identity, tool/version and bounded
  receipts, virtual addresses, normalized instruction/data-flow semantics and
  independently authored prose/verifier code only. Retain no raw bytes,
  instruction listings, complete function dump, decompiler output, strings
  corpus, analysis database, credentials, identifiers or private paths. Declare
  literal independent canonical freezes for immutable metadata, semantic
  anchors, receipts and verdicts before verifier construction; never generate
  expected hashes from mutable evidence at startup.
- **Validation:** normal and optimized verification must reject binary-identity
  drift, forbidden tool option or external-file evidence, invented request/call
  site/value origins, pointer-versus-scalar conflation, order inversion, hidden
  return discard/retry/gating, runtime/mainline-ABI promotion, missing receipts
  and budget drift. Run JSON, in-memory compile, whitespace, local links,
  retained suffix, privacy/source-rights, `git diff --check` and repository gate.
- **Effects and stop conditions:** no device, SSH, live process, network,
  Buildbox, kernel build, candidate, boot2, radio action, binary execution,
  shared-file edit, staging, commit or push. Stop on input mismatch, external
  file lookup, tool ambiguity, conflicting data flow, budget exhaustion or need
  for another binary/runtime trace.
- **Handoff:** README, complete sanitized input/analysis receipts, verdicts,
  independent freeze, normal/optimized verifier and validation record. Report
  exact resolved/unresolved predicates, budgets, checks and next discriminator.
- **Efficiency loop:** if accepted, record one sanitized item in active pilot
  03; credits remain unavailable unless actually measured.
- **State:** amended contract frozen; fresh bounded private static analysis is
  authorized under the repository's standing retained-evidence policy.
