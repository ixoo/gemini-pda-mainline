# Mapping diagnostic v2 — observer recursion refusal

The one authorized diagnostic refused with `RecursionError: maximum recursion
depth exceeded`. It retained zero affected file identities and zero affected
mapping rows. The original pyelftools mapping delta remains unidentified; this
is not a successful diagnostic or a native-mapping admission.

## Chronology and frozen identities

- Clean dispatch: `81078ebdfe89aebfe59b202f2356c5c72a19a784`.
- Twenty-six controlling and eighteen dependency hashes passed.
- [Diagnostic source](mapping-diagnostic-v2.json) frozen:
  `2026-09-07T03:33:45Z`.
- Run started: `2026-09-07T03:34:02.619302+00:00`.
- Run ended: `2026-09-07T03:34:02.806271+00:00`.
- Diagnostic file SHA-256:
  `959f7fa92fd6dadbb54960aca276e1e4a912ece1d508306b5893d797e377a94d`.
- Embedded source SHA-256:
  `2d1646bb44d678eb0d069ecd25c425bb0acea992353b901c11c84635dc12e456`.
- [Result](mapping-diagnostic-result-v2.json) SHA-256:
  `699183d1b6b22f55d5e515c1969d66a7921e5bd82fd73fc3463ae09734327214`.

## Evidence and limits

The audit hook preceded metadata discovery and remained active through exit.
Both package inventories, pre-import drift and the Capstone import/closure
gates precede the instrumented interval in the frozen source. The failure
receipt reports 143 import events and 25 entered/completed package modules:
only the Capstone package bodies completed. It reports one Capstone native
request, zero optional requests and zero write/cache/network/process/private
events. No engine, callback, method freeze or private analysis occurred.

The 73-module completion predicate was not reached. The receipt does not
retain the recursive request sequence, so it cannot prove the exact observer
reentrancy cause. The wrapper's restoration is in `finally`, but the separate
successful-postcondition checks were not reached; no successful restoration
receipt is claimed. Child exit ended the instrumentation.

No repair, second execution or further mapping inspection followed. The RE
shell was closed. No raw maps, virtual addresses, private capture files or
private paths were written. Historical inputs remain unchanged. Only the three
named v2 diagnostic files are the worker delta.

Tests actually run: forty-four frozen hash comparisons, diagnostic source
digest and syntax checks, exactly one isolated no-ELF diagnostic, and host
refusal-result checks for pins, claims and bounds. `git diff --check` passed.
No mutation suite, device, network, acquisition, build, commit or push occurred.

Next discriminating check: prospective review of observer reentrancy and a
separately authorized bounded diagnostic identifying any imports initiated by
the mapping observer itself. Do not raise the recursion limit, bypass the
observer, infer a native dependency, or retry under this consumed diagnostic
budget. The single private-analysis execution remains unused.
