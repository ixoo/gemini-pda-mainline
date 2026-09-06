# Executed validation and limits

review_ready_utc = 2026-09-06T23:41:14Z

## Identity and provenance checks

All four predecessor files matched the frozen hashes before analysis. The
dispatch HEAD matched `85fe579edc44266cec9ca3dc09127482f119d273`.
`inputs.json` was written before private/tool source inspection.

Through `./scripts/dev-vm re-shell`, `sha256sum` verified the retained
Image.gz, Image, vmlinux and reconstruction diagnostics, plus the launcher,
four selected installed Python sources, METADATA and RECORD. All matched the
contract. The installed interpreter reported Python 3.12.3. METADATA reported
vmlinux-to-elf 1.3.6 and GPL-3.0-or-later; the four source entries were present
in RECORD. License metadata was not treated as authority to copy source.

Source inspection used bounded `rg -n` and `nl -ba | sed -n` reads solely from
the four admitted source files, with exact function/line citations in
`analysis.json`. No source imports were expanded for inspection. No CLI
reconstruction was run.

## Parser invocation and escalation

The installed interpreter invoked `KallsymsFinder(Image, bit_size=64)` once.
Before importing the parser, a Python audit hook rejected socket connect,
DNS lookup, subprocess and shell acquisition attempts. None occurred.
Environment: empty `DEBUGINFOD_URLS`, `DEBUGINFOD_PROGRESS=0`, `R2_CURL=0`,
`PIP_NO_INDEX=1`, `LC_ALL=C`, umask 077. A new mode-0700 private RE-VM child
retains the log and bounded metadata; the full symbol table was never persisted.

The full parsed list was used in memory to count exact target-name matches,
enumerate same-address aliases, and select the nearest lower/higher distinct
addresses. Each neighbor address had one tuple. The four tuples, aliases and
neighbors alone were emitted. ELF region checks read only header/section-name
metadata; no instruction range was decoded, dumped or separately hashed.

The parser reported 64,417 symbols and zero warnings/errors. However, later
source tracing established that its constructor unconditionally called
`ArchitectureDetector.guess`, even with bit size supplied. The source describes
ISA-prologue signature detection. This conflicts with the explicit
no-instruction-classification condition. The specialist immediately notified
the coordinator and stopped; no attempt was made to hide or repair the run.
The RE shell was closed at the 2026-09-06T23:37:40Z stop. No source expansion,
second parser invocation, new ELF, device action, network lookup or build followed.

Thus the tuple/interval result is provisional and later instruction analysis
remains blocked. Raw-log identities are frozen; no proprietary bytes, long
source excerpt, full log or personal path is included here.

## Host refusal checks

After freezing all three JSON records, these commands passed:

```text
python3 experiments/2026-09-06-vmlinux-to-elf-symbol-provenance/verify.py
  provisional packet PASS; mutations=66; later-analysis=blocked
python3 -O experiments/2026-09-06-vmlinux-to-elf-symbol-provenance/verify.py
  provisional packet PASS; mutations=66; later-analysis=blocked
git diff --check
  PASS
```

Mutations cover every recorded input/tool hash class, source transformation,
target uniqueness/type/address, alias overflow, order/cross-region bounds,
synthetic-binding strength claims, exact-end promotion, scope/authority,
private paths and mutable expected digests. These tests preserve the blocked
packet and numeric interval predicates; they cannot retroactively make the
original parser invocation conform to the strict contract.

## Focused review repair

Replaced the private-path mutation with an actively rejected synthetic sentinel
that does not resemble a personal absolute path. Recorded the observed original
`review_ready_utc` above and in `FREEZE.md`. No JSON evidence or conclusion
changed, so the fixed JSON digests remain unchanged.

Normal and optimized verifier reruns each passed 66 refusal mutations.
`git diff --check` passed. `./scripts/check-repository` passed, including its
publication gate and seven-file change selection. It reported the documented
Linux-only provenance/package skips; kernel build, Checkpatch, DT schemas and
device tests were not run. No private-input inspection or device action was
part of this repair.
