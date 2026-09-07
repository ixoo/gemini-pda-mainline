# Retained WLAN instruction attribution: V10 refused before analysis

The single V10 run refused at `initial-inventory`, before package entry,
method loading or any private ELF read. Its one-run budget is consumed and
RE-VM custody is released. No binary init-chain edge, exit callee, teardown join
or exit-reference candidate was established. Missing results are unobserved,
not evidence of absence.

The exact published execution parent was
`f1fef5e6bb83d2a2e85b33f9a97e9256b8b11a55`.
All 101 input/control pins and source/method/freeze hashes passed before the
run. Startup passed; the next stage returned a closed `validation-failure`.
The receipt does not identify the failed predicate. No retry or source change
followed.

- [Work contract](WORK_ITEM.md) and [pinned inputs](inputs.json).
- [Prospective V10 contract](AMENDMENT-26.md) and [immutable source freeze](FREEZE.md).
- [Complete refusal receipt](bootstrap-v10-result.json).
- [Unobserved mapping/decoding record](analysis.json) and [unobserved edge/candidate record](edges.json).
- [Chronology, raw-log hashes, validation and escalation](VALIDATION-RESULT.md).
- [Public refusal verifier](verify-result.py): normal and optimized runs each
  rejected 514 mutations across all 11 predeclared families.

The independently accepted [V9 tools preflight](VALIDATION-V9.md) remains
immutable historical evidence. It did not admit a method or private analysis;
its success does not override V10's refusal. Earlier amendments and diagnostic
records remain linked through the work contract and input inventory.

This investigation concerns four accepted Kallsyms inspection envelopes, not
exact function ends or runtime behavior. The retained binary remains private;
no instruction bytes, disassembly, private paths or raw logs were published.
No hardware-support, firmware/radio, resource-release or teardown-safety claim
is made. The unresolved initial-inventory difference is handed off for a new
bounded decision; no further operation is authorized here.
