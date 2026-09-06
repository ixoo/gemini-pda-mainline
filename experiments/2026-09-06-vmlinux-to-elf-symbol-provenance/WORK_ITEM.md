# Retained-kernel symbol provenance and conservative interval audit

- **Outcome:** determine exactly what the installed `vmlinux-to-elf` 1.3.6
  reconstruction preserves or synthesizes for Kallsyms name, address, type,
  ELF binding, ELF symbol type, size and section; recover the original
  Kallsyms tuples for the four WLAN lifecycle symbols from the exact retained
  kernel image; and decide whether each symbol has a defensible conservative
  analysis interval even though the reconstructed ELF has `st_size=0`. Return
  a bounded unresolved result if provenance or interval conditions do not pass.
  This may authorize a later analysis contract; it performs no instruction
  decoding and establishes no call, return, runtime or teardown result.
- **Parent:** repository commit
  `3ab35a2eced0081d6278f0ce76d2b310fe4570df`. Direct predecessor is the
  accepted unresolved packet at
  `experiments/2026-09-06-mt6797-wlan-final-linkage-teardown-attribution/`:
  inputs `89dd591276e93c58dee6f35a53eab3b8daa93dec565f71387a997adf1c3875a1`,
  analysis `d08406c637cc19c943c761b302d7591eeb99a334cd03ac0fdf69fb084046cd70`,
  freeze `c91f67779fe9a2c12c33a5b21ad4d46897824a14f0545a513265a39c71bc47b3`,
  validation `5937d2772d49ec578d540225b7517bcfc9510212b286ee32bc7eefe0941f4360`.
  Record these in `inputs.json` before analysis.
- **Frozen private kernel tuple:** the one existing RE-VM workspace only:
  compressed kernel field SHA-256
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`,
  decompressed Image
  `0570480c28bce1583636a240904df8da3af0b5e5b4bcc6254f5719b42bd723d0`,
  reconstructed ELF
  `cc66df06194d3315335462760962165e1dcb2e50221574aeb45a0805bb17a162`,
  and retained reconstruction diagnostics
  `3e58a3e5c2a43914558f761ccdf4488a9c49b869645b4152ad9b2ee05a2f10b8`.
  Verify these before reading beyond hashes. Do not reconstruct a second ELF,
  copy private bytes, or export private logs/databases.
- **Frozen tool tuple:** exact installed distribution `vmlinux-to-elf` 1.3.6
  under the existing dtschema environment, Python 3.12.3. Launcher SHA-256 is
  `6140be2ee9638573c32b06e5c00ca387e647720b6c8434d123ede119ec11ca6b`;
  relevant installed source hashes are script
  `e3d2de8b5b7ac7ac4e8986369d7a034ae1bbae0af6e08b8d6e6c73c703cb3f15`,
  Kallsyms parser
  `2bff550d9486e90782a4320cec7bc26b249ead5048f58839eec6578b52c06c2d`,
  ELF symbolizer
  `13e79cf4dc37050547f22b65ad35070dceba17473df823c7311311c3fb9e1118`,
  and ELF writer
  `f974b1189155d2cea4773d378990e1b20be866f27719be0593fef3110c56891d`.
  Metadata is
  `133b5a6b7fab8081a7c201f2fc63b8a2d7a215475c423c8fe3938aff6a708c43`;
  RECORD is
  `ac8d68216a496f0f4dedede5e3ea0d72051bbab7983ab196189da05f5aebdc1f`.
  Record full hashes before source inspection. No package install, update,
  database download or network.
- **Owner and reviewer:** Astra Medium owns this named reconstruction and
  symbol-ownership uncertainty. Sol Medium independently reviews the frozen
  result; `/root` integrates. The owner is not alone in the repository and
  must not revert or edit concurrent files.
- **Model route:** `gemini_specialist`, `gpt-6-astra`, medium for the tool and
  binary provenance question; `gemini_reasoner`, `gpt-5.6-sol`, medium for
  integration review. No implementation route is selected by this audit.
- **Owned scope:** create only this experiment's `README.md`, `inputs.json`,
  `analysis.json`, `intervals.json`, `FREEZE.md`, an assert-free normal/optimized
  verifier, `VALIDATION.md` and sanitized result metadata. Private raw output
  stays in a mode-0700 RE-VM work child. Do not edit the predecessor, hardware
  facts, support matrix, roadmap, queue, workstreams, workflow ledger, configs,
  manifest, series or patches.
- **Tool provenance analysis:** inspect only the four hash-pinned relevant
  Python sources plus distribution metadata/RECORD. Trace the complete field
  transformation from recovered Kallsyms tuple to emitted ELF symbol. Record
  whether case and weak/local/global type distinctions are retained, normalized
  or discarded; how `STB_*`, `STT_*`, `st_size` and section index are chosen;
  and whether tool output can prove original final-link strength. Cite bounded
  line/function identities and independently worded behavior, not long source
  excerpts. License metadata is evidence only, not permission to copy code.
- **Exact-image symbol analysis:** invoke only the installed parser/library on
  the exact decompressed Image, with network/debuginfod disabled, to recover
  name/address/original Kallsyms type for exactly
  `do_connectivity_driver_init`, `do_wlan_drv_init`,
  `mtk_wcn_wlan_gen3_init`, and `mtk_wcn_wlan_gen3_exit`. Enumerating the full
  recovered symbol table in memory is admitted solely to identify each exact
  target's same-address aliases and immediately preceding/next distinct-address
  symbols; persist only those bounded neighborhoods and counts. Do not decode,
  dump, hash or classify instruction bytes.
- **Interval rule to evaluate:** a conservative interval may be admitted only
  as `[target start, next distinct recovered Kallsyms symbol start)` when the
  target tuple is unique by exact name, its start matches the reconstructed
  ELF, all same-address aliases are enumerated, the next distinct address is
  strictly greater and within the same executable recovered image region, and
  no contradictory type/order evidence exists. It is an inspection envelope,
  not an exact function end: padding, literal pools, aliases or tail-sharing
  remain possible. Separately classify whether the original Kallsyms type
  itself supports weak versus ordinary final linkage. Do not use ELF `GLOBAL`
  or symbol proximity alone for that strength claim.
- **Bound:** one retained kernel tuple, one installed tool distribution, four
  target symbols, at most four same-address aliases per target and one
  predecessor/next-distinct symbol each. No instruction bytes, disassembly,
  Ghidra/radare analysis, public/vendor source, new reconstruction, device,
  network or Buildbox. Whole-table parsing/order is the admitted discriminator;
  whole-table publication is forbidden.
- **Acceptance predicates:** independently classify with exact evidence and
  limitations: (1) reconstruction/tool identities; (2) the source-level field
  transformation and whether binding/size are synthetic; (3) original
  Kallsyms tuple and strength class for each target, or why unavailable;
  (4) alias and immediate-neighbor inventory; (5) conservative interval
  admissibility per target; (6) whether a later bounded branch/xref contract
  can use those envelopes without claiming exact function ends. A negative or
  partially unresolved answer is acceptable when it closes the evidence path.
- **Refusal and validation:** reject any input/source hash drift, second ELF,
  hidden network/database acquisition, ambiguous/missing/duplicate target,
  unbounded neighborhood output, alias overflow, non-monotonic/cross-region
  boundary, inferred strength from synthesized ELF binding, exact-end claim,
  decoded instruction byte, semantic call/return/xref claim, mutable expected
  digest, private path or raw proprietary content. Freeze inputs, tool behavior,
  target tuples, neighborhoods and verdicts before writing the verifier.
  Normal and optimized verifier modes must use active checks and mutations for
  every identity, target, alias/boundary, strength, interval and authority
  class.
- **Rights and privacy:** installed open-source tool text and the retained
  kernel are analysis inputs. Commit only hashes, versions, bounded symbol
  metadata, counts, raw-log hashes and independently worded conclusions. No
  private paths, binary bytes, disassembly, large source excerpts, credentials,
  serial/IMEI/calibration data or proprietary material.
- **Hardware/build effects:** none. The device is confirmed back on changed-ID
  known-good Gemian with custody released. No SSH/device action, firmware/radio
  action, build, patch integration, commit or push by the owner.
- **Stop/escalation:** stop on any identity mismatch, tool auto-fetch, parser
  ambiguity, alias overflow, need for instruction decoding/source expansion,
  or conflict with the predecessor. Return exact evidence, attempts, unresolved
  question and next discriminating check; do not repair ambiguity by inference.
- **Handoff:** exact parent/input/tool identities, relevant source-function
  inventory, four bounded neighborhoods, transformation table, per-predicate
  verdicts, private raw-log hashes, normal/optimized mutation counts,
  limitations, and review-ready UTC. State whether later bounded instruction
  analysis is admitted, partially admitted or still blocked.
- **Efficiency loop:** if independently accepted, append one sanitized item to
  the active workflow cohort with actual routes/timestamps, first-review result,
  rework/escalation and measured credits or explicit unavailability.
- **State:** frozen for offline specialist dispatch; no device action.
