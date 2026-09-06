# Fresh AArch64-bypass Kallsyms provenance and interval audit

- **Outcome:** repeat the retained-image Kallsyms tuple and conservative
  interval audit through one prospectively frozen parser method that cannot
  invoke architecture-signature detection. Determine the original Kallsyms
  type and one conservative `[start, next distinct symbol)` inspection envelope
  for each of the four WLAN lifecycle symbols, or return a bounded unresolved
  result. This may authorize a later instruction-analysis contract; it does not
  decode instructions or establish exact function ends, calls, returns, xrefs,
  runtime execution, teardown safety or resource quiescence.
- **Parent:** repository commit
  `0052c6707011bb34b2061c8b45661a5ba05965f8`. The excluded predecessor is
  `experiments/2026-09-06-vmlinux-to-elf-symbol-provenance/`, pinned as
  inputs `cc93d3e9627e31a60d66ebcea8211104a47663313b0015a5390612624f50bf4b`,
  analysis `18c4bf0b55a4cd00450b1eead755edf610e4050612191a3b7fdca968c4b36c12`,
  intervals `30ab9bb53bff6c144ba75b390220f0c036e9cbe8730d2fcb7c562955a659f23d`,
  freeze `5c2b89f699f2fdb051a85049410406110a272f609b137486df5f1deeb8d210a2`
  and validation
  `6b1caee83ef5503ce5e5affc9d6c4ae9193943114c10088b7ba6e3b16a27b7b3`.
  Verify these before analysis. They are stop/provenance inputs only: do not
  read or reuse that attempt's private raw output, bounded metadata, symbol
  tuples, aliases, neighbors, counts or provisional interval verdicts.
- **Direct evidence dependency:** the accepted zero-size retained-ELF result at
  `experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/`,
  pinned as inputs
  `89dd591276e93c58dee6f35a53eab3b8daa93dec565f71387a997adf1c3875a1`,
  analysis `d08406c637cc19c943c761b302d7591eeb99a334cd03ac0fdf69fb084046cd70`,
  freeze `c91f67779fe9a2c12c33a5b21ad4d46897824a14f0545a513265a39c71bc47b3`
  and validation
  `5937d2772d49ec578d540225b7517bcfc9510212b286ee32bc7eefe0941f4360`.
- **Frozen private kernel tuple:** use the sole existing RE-VM workspace:
  Image.gz SHA-256
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`,
  Image `0570480c28bce1583636a240904df8da3af0b5e5b4bcc6254f5719b42bd723d0`,
  reconstructed ELF
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`
  and reconstruction diagnostics
  `3e58a3e5c2a43914558f761ccdf4488a9c49b869645b4152ad9b2ee05a2f10b8`.
  Verify all four before content access. Do not reconstruct or copy an ELF,
  export private bytes/logs/databases, or use any prior private parser output.
- **Frozen tool tuple:** installed `vmlinux-to-elf` 1.3.6 under Python 3.12.3;
  launcher `6140be2ee9638573c32b06e5c00ca387e647720b6c8434d123ede119ec11ca6b`,
  script `e3d2de8b5b7ac7ac4e8986369d7a034ae1bbae0af6e08b8d6e6c73c703cb3f15`,
  Kallsyms parser
  `2bff550d9486e90782a4320cec7bc26b249ead5048f58839eec6578b52c06c2d`,
  symbolizer
  `13e79cf4dc37050547f22b65ad35070dceba17473df823c7311311c3fb9e1118`,
  writer `f974b1189155d2cea4773d378990e1b20be866f27719be0593fef3110c56891d`,
  METADATA
  `133b5a6b7fab8081a7c201f2fc63b8a2d7a215475c423c8fe3938aff6a708c43`
  and RECORD
  `ac8d68216a496f0f4dedede5e3ea0d72051bbab7983ab196189da05f5aebdc1f`.
  Record exact hashes before source or private-image inspection. No install,
  update, download, network or database lookup.
- **Owner and reviewer:** Astra Medium owns the named parser-state and symbol
  boundary uncertainty. Sol Medium independently reviews the frozen result;
  `/root` integrates. The owner is not alone in the repository and must not
  revert or edit concurrent files.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for the parser and
  binary-provenance uncertainty; `gemini_reasoner`, `gpt-5.6-sol`, medium for
  review. No implementation route is selected.
- **Owned scope:** create only this experiment's `README.md`, `inputs.json`,
  `method.json`, `analysis.json`, `intervals.json`, `FREEZE.md`, assert-free
  normal/optimized verifier and `VALIDATION.md`. Private raw output stays in a
  fresh mode-0700 RE-VM child. Do not edit predecessors, hardware facts,
  support, roadmap, queue, workstreams, workflow ledger, configs, manifest,
  series or patches.
- **Pre-execution source gate:** inspect only the hash-pinned
  `core/kallsyms.py` and the already pinned launcher/symbolizer/writer sources.
  In `core/kallsyms.py`, enumerate every assignment and read of the parser's
  architecture state, including `self.architecture`, and identify the exact
  value/type convention required for frozen AArch64. No imported-source
  expansion is admitted. Stop before parsing if a required enum/value or
  consumer cannot be established from these four files and frozen ELF header
  metadata alone.
- **Frozen bypass method:** define one local subclass of the pinned
  `KallsymsFinder`. It must inherit the original constructor and parsing
  methods unchanged and override only `guess_architecture`. Its override must
  set every architecture field the pre-execution gate proved necessary from
  exact frozen primitives: ELF64, little endian and AArch64/e_machine 183. Do
  not invent an enum, use `None`, call any detector, inspect image bytes, or
  accept a merely parse-compatible substitute. Freeze the complete subclass
  source and its SHA-256 in `method.json` before loading private image content.
- **Bypass assertions:** before and after the single parser construction,
  actively require the imported module path/source hash; exact MRO `subclass →
  pinned KallsymsFinder → object`; inherited constructor identity; subclass
  namespace containing no parser override other than the reviewed
  `guess_architecture` plus ordinary Python metadata; override call count
  exactly one; unchanged identities for every parsing method it uses; and
  exact final architecture fields. Temporarily replace
  `ArchitectureDetector.guess` with a fail-closed sentinel that records and
  raises on any invocation, then restore it in a `finally` block. The observed
  detector-call count must be zero. Record exception/restore outcomes without
  weakening the zero-call predicate.
- **Fresh exact-image analysis:** instantiate only
  `FrozenAArch64Finder(Image, bit_size=64)` after all method checks pass. A
  Python audit hook must reject socket/DNS, subprocess and shell acquisition.
  Use the resulting table in memory only to recover exact name, address and
  original Kallsyms type for `do_connectivity_driver_init`,
  `do_wlan_drv_init`, `mtk_wcn_wlan_gen3_init` and
  `mtk_wcn_wlan_gen3_exit`. Enumerate each target's same-address aliases and
  immediate preceding/next distinct-address symbols. Persist only this fresh
  bounded result and counts; never compare it against or import values from the
  excluded attempt.
- **Interval rule:** admit `[target start, next distinct recovered Kallsyms
  symbol start)` only when exact-name uniqueness, reconstructed-ELF start
  equality, complete same-address alias inventory, strictly greater next
  address in the same executable image region, monotonic tuple ordering and
  noncontradictory type evidence all pass. It is an inspection envelope, never
  an exact end; it may contain padding, literal pools, aliases or tail sharing.
  Classify ordinary/weak/local final linkage only from the fresh original
  Kallsyms type and the pinned type/case transformation, not reconstructed ELF
  `GLOBAL` alone.
- **Bound:** one retained kernel tuple, one installed distribution, one source
  gate over four already pinned files, one frozen subclass, one parser
  construction and four targets. At most four aliases plus one previous/next
  distinct tuple per target. No prior raw result, second attempt, whole-table
  persistence, instruction/prologue classification, instruction bytes,
  disassembly, xref/branch/call analysis, source expansion, reconstruction,
  network, device or Buildbox.
- **Acceptance predicates:** independently establish (1) every input/tool and
  source identity; (2) complete parser architecture-state consumers and exact
  frozen field values; (3) frozen subclass/method and all bypass assertions;
  (4) zero detector calls and successful restoration; (5) one fresh unique
  original tuple and strength class per target; (6) bounded aliases/neighbors;
  (7) interval admissibility per target; and (8) whether those envelopes may
  feed a later bounded instruction contract without exact-end claims. A
  negative result is acceptable when it closes the method path truthfully.
- **Refusal and validation:** reject input/source/method drift, unresolved
  architecture state, extra subclass members or overridden parser methods,
  detector invocation, sentinel/restore failure, prior-output reuse, multiple
  parser construction, network/subprocess attempt, target ambiguity, alias
  overflow, cross-region/nonmonotonic boundary, synthesized-binding strength,
  exact-end promotion, decoded bytes or semantic call/xref claims, mutable
  expected digests, private paths/content or authority expansion. Freeze all
  JSON evidence before writing the verifier. Normal and optimized modes must
  use active checks and mutations for every identity, method, sentinel,
  target, alias/boundary, strength, interval and authority class.
- **Rights and privacy:** installed open-source tool text and the private
  retained kernel are analysis inputs. Publish only hashes, versions, bounded
  source-function/line identities, complete frozen subclass text, bounded
  symbol metadata/counts, raw-log hashes and independently worded conclusions.
  No private paths, binary bytes, disassembly, long source excerpts,
  credentials, serial/IMEI/calibration data or proprietary content.
- **Hardware/build effects:** none. The device remains known-good Gemian with
  custody released. No SSH/device action, firmware/radio action, build, patch
  integration, commit or push by the owner.
- **Stop/escalation:** stop on any identity mismatch, need for imported-source
  expansion, architecture field ambiguity, detector/sentinel hit, subclass or
  parser-method mismatch, prior-output dependency, parser ambiguity, alias
  overflow, need for decoding or conflict with accepted evidence. Return exact
  evidence, attempts, unresolved question and next discriminating check.
- **Handoff:** exact parent/predecessor/kernel/tool identities; source-consumer
  inventory; frozen subclass text/hash and assertion outcomes; detector and
  construction counts; four fresh bounded neighborhoods; per-predicate
  verdicts; private raw-log hashes; normal/optimized mutation counts;
  limitations; and review-ready UTC. State whether later bounded instruction
  analysis is admitted, partially admitted or blocked.
- **Efficiency loop:** if independently accepted, append one sanitized item to
  the active workflow cohort with actual routes/timestamps, first-review result,
  rework/escalation and measured credits or explicit unavailability.
- **State:** frozen for fresh offline specialist dispatch; no device action.
