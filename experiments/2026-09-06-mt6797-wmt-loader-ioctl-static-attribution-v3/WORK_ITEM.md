# MT6797 `wmt_loader` ioctl static-attribution v3 work item

- **Outcome:** freshly and statically resolve or sharply bound whether the exact
  retained `system/vendor/bin/wmt_loader` issues
  `COMBO_IOCTL_DO_MODULE_INIT` to `/dev/wmtdetect`, its third-argument origin,
  command ordering and return handling. Preserve static reachability separately
  from runtime execution, successful initialization, firmware/radio behavior
  and any future mainline ABI.
- **Parent and immutable input:** repository commit
  `65f1b43333b727f0d5bbddf900cd38486a896e4d`; exact logical binary path
  `system/vendor/bin/wmt_loader`, SHA-256
  `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`.
  Match before analysis and stop on mismatch/absence. The accepted source
  predecessor is
  `experiments/2026-09-06-mt6797-connectivity-producer-source-attribution/`.
- **Prior-attempt treatment:** v1 and v2 are excluded chronology and selection
  evidence only. V2 identifies the candidate routine interval `[0xb10,0x14d0)`
  and exact literal intervals `[0x14d0,0x14df)` and `[0x1510,0x152d)` for
  prospective selection here. Discard all prior raw/partial output and rederive
  every identity, count, address, semantic edge and verdict from fresh v3 tool
  output. A mismatch with the candidate ranges is an immediate stop, not repair.
- **Owner/reviewer:** Astra Medium owns the stripped-binary uncertainty;
  `/root` integrates; Sol Medium independently reviews. The owner may edit only
  this new v3 directory, not this frozen contract, and must preserve other work.
- **One-batch boundary:** use one RE-VM shell and exactly one predeclared
  analysis batch. Set `DEBUGINFOD_URLS` empty. The batch may invoke at most eight
  static child tools: exact hash and tool-version queries, `readelf -h -SW` on
  the admitted binary, and one `objdump -d --no-show-raw-insn` over exactly
  `[0xb10,0x14d0)`. One in-memory controller may read exactly the two selected
  NUL-terminated literal intervals and derive control/data flow from that fresh
  disassembly. This contract explicitly admits the complete selected routine
  interval and its two literals in the first and only batch; no replay, second
  batch, direct-edge expansion or other byte interval is permitted.
- **No-follow repair:** do not request debug/unwind metadata or use any
  `readelf`/`objdump` debug/DWARF option (`-w`, `--debug-dump`, `--dwarf`,
  `--dwarf-depth`, `--dwarf-start` or equivalents). Do not consult build IDs,
  debug links, symbol servers or separate files. Any tool diagnostic naming,
  opening or consulting another file is an immediate stop. Do not duplicate the
  retained binary or save raw tool output.
- **Acceptance predicates:** independently classify with exact address,
  normalized semantic anchor, conditions, missing edge and next discriminator:
  1. exact identity/architecture and selected device-path open-to-fd flow;
  2. exact numeric module-init request/direct call and its gates;
  3. scalar third-argument provenance and conditional `0x6797` selection;
  4. local ioctl return interpretation/retry/gating/routine-return behavior,
     while keeping separate libc/process conversion unresolved if outside;
  5. relative order/conditions for autok, chip-cache set, cleanup and init; and
  6. vendor compatibility evidence versus an unresolved mainline ABI/design.
- **Accounting/evidence:** count the single batch, every static child/controller
  invocation, exact analyzed intervals/bytes, selected instructions/blocks,
  direct and ioctl call sites, literals, diagnostics and temporary files.
  Retain only exact input/tool/receipt identities, addresses, normalized
  semantics and independently authored prose/verifier code—no raw bytes,
  instruction listing, function dump, decompiler output, string corpus,
  database, private path, credential or identifier. Declare literal independent
  canonical freezes for inputs, anchors, complete receipts and verdicts before
  verifier construction; do not derive expectations from mutable inputs.
- **Validation:** normal/-O verification must reject binary/predecessor drift,
  any second batch/replay/extra interval/tool, forbidden option/external-file
  evidence, invented request/call/value origin, pointer/scalar conflation,
  order inversion, hidden return propagation/retry/gating, runtime/mainline
  promotion, missing receipt and budget drift. Run JSON, in-memory compile,
  whitespace, links, suffix/privacy/rights checks, `git diff --check` and the
  repository gate.
- **Effects/stop:** static RE-VM reads only. No device, SSH, live process,
  network, execution/emulation/ioctl, Buildbox/build, candidate/boot2/radio,
  shared-file edit, staging, commit or push. Stop on conflict, mismatch,
  diagnostic, budget exhaustion or need for another interval/binary/runtime.
- **Handoff:** README, sanitized input/analysis receipts, verdicts, independent
  freeze, normal/-O verifier and validation record; exact resolved/unresolved
  predicates, counts, checks and next discriminator. Record start/review-ready
  UTC and measured credits only; otherwise credits are unavailable.
- **Efficiency loop:** if accepted, record one sanitized pilot-03 item. This is
  the final in-scope repair; another failure requires a new owner decision.
- **State:** v3 contract frozen; one fresh bounded static batch authorized.
