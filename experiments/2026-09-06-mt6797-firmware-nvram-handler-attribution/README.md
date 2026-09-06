# Retained firmware handler attribution: preflight scope stop

Both analysis branches stopped before execution. The five frozen private
scripts do not implement the traversal and counting rules required by the
[work contract](WORK_ITEM.md), which also prohibits creating or replacing a
script. The existing identities match; this is a tooling-scope conflict, not
evidence that the target is or is not an NVRAM handler.

The machine-readable [receipt](results/attribution.json) records four
`unresolved` verdicts: target contract, incoming reachability, record
application and calibration precedence. No policy, firmware application,
runtime behavior or hardware support is established.

## Preflight and exact identity evidence

All eight sanitized input records match the exact paths and SHA-256 values in
the contract and receipt. These are citation/constraint inputs; no additional
public repository or private firmware/library/storage corpus was inspected.
The frozen parent is `f43a702c107e3685c92c4d275dc3547acf7302ce`.

The existing RE VM was used only for read-only identity checks, reading the
retention note, and inspecting the five permitted analysis scripts. The exact
private identities are in the receipt; no private path, artifact name, stored
option value, address, source excerpt, firmware string or instruction listing
is included here.

| Check | Observed result |
| --- | --- |
| Retained firmware whole-file SHA-256 and size | Matched the contract; 411,632 bytes |
| Retained directory canonical SHA-256 | Matched before and after inspection |
| Regular-file inventory | 21 files and 1,619,222 aggregate bytes, before and after |
| Frozen import-log SHA-256 | Matched before and after; tool/language identity remains attributed to this frozen log |
| Five permitted scripts' ordered content-digest aggregate | Matched before and after |
| Independent mapped-section/window identity check | Not performed before global scope stop |
| Independent stored-option presence check | Not performed before global scope stop |

The directory digest uses C-locale sorting of relative regular-file paths,
without a leading dot-slash, NUL-delimited during sorting, followed by the
SHA-256 record stream and an outer SHA-256. The script aggregate uses the
contract's fixed order of five lowercase hexadecimal content digests, each
followed by a newline. No replacement identity was created.

Matching the whole directory verifies the bytes of the frozen retained state;
it does not independently interpret its program options or prove a candidate
mapping. Those separate prerequisite checks are explicitly marked unverified,
not false observations of absent options or mismatched windows. No Ghidra
program was opened or analysis script executed during this item.

## Tooling findings and stop decision

These are independently described facts about the frozen analysis tooling,
not new firmware behavioral findings:

- The retained target checker inspects at most eight instructions up to the
  first control transfer. It does not traverse the complete target slice or
  classify the requested one-level references.
- The retained predecessor walks use an unordered predecessor collection and
  different budget accounting. They do not guarantee the contract's sorted
  neighbor order and count-at-first-dequeue rule, including recording but not
  expanding the cap node.
- The retained target propagation follows one selected bounded path. It does
  not join all admitted predecessors or implement the requested incoming
  dispatch enumeration and count inventory.
- Some retained scripts reconstruct candidates or write program
  options/mappings. Reusing those actions would not independently verify the
  frozen candidates under the new contract.

The finding is not that the earlier scripts were unsuitable for their earlier
bounded investigations. Their frozen purposes and earlier published limits are
in the input records. They cannot supply this different traversal contract.
Modifying them, adding a traversal/verification script, or creating a
replacement database requires a scope amendment. Running a shorter prefix
again would not answer either branch's stated question.

## Attempt ledger and verdicts

| Branch | Executed attempts | Result |
| --- | ---: | --- |
| `target-contract` | 0 | Not started; global scope stop |
| `incoming-reachability` | 0 | Not started; global scope stop |

The preflight review is not counted as an analysis attempt. There are no new
roots, visited nodes, reference hits, unknown-transfer counts, cap results or
queue-exhaustion observations. The receipt represents those measurements as
null, not zero or exhaustive no-hit. Planned caps are retained only as planned
limits. No historical measurements are copied into a new attempt.

| Verdict | Missing evidence | Next discriminator |
| --- | --- | --- |
| `target_contract=unresolved` | A complete admitted target input/consumer slice | Admit and freeze a read-only deterministic target traversal/verification implementation before a new attempt |
| `incoming_reachability=unresolved` | An exact incoming transfer chain | Admit and freeze the corresponding deterministic incoming-reference/predecessor implementation |
| `record_application=unresolved` | Both foundations and payload-to-effect def-use | After the foundations resolve, require the actual submitted-payload consumer trace |
| `calibration_precedence=unresolved` | Concrete ordering among the three sources | After an admitted application trace, inspect ordering under explicitly stated branch predicates |

The known local entry, reference, conditional target and ABI remain hypotheses.
No target is labeled from text proximity, an argument convention or a size.
No new decoder ambiguity, contradictory firmware semantics or encrypted
transfer was encountered because no firmware branch was executed. Neither
absence of measurements nor a tooling refusal supplies a contradicted verdict.

## Escalation packet and preservation

Evidence: all frozen file/directory/script identities match, while the permitted
implementations lack the required traversal behavior. Attempts: zero analysis
attempts and zero tooling repairs. Unresolved question: whether the integration
owner will admit and freeze the missing read-only deterministic tooling.
Next discriminating check: review a concrete additional tooling contract with
implementation identity, immutable-candidate verification, exact accounting
and sanitized output before resuming either branch.

This is an immediate `required-scope-expansion` global stop. It is not authority
to create that tooling, run a branch, change an anchor, decrypt firmware,
emulate a processor, or access the device. There were no private file additions
or removals; the final directory digest still matches the initial digest. The
existing private state remains retained for the owning investigation. The RE
shell was closed after preservation checks.

Contract start was `2026-09-06T05:41:02Z`; the observed preflight clock was
`2026-09-06T05:41:33Z`, and preservation/stop was recorded at
`2026-09-06T05:44:00Z`. These bound preflight, not invented branch timestamps.
Actual owner route is Astra Medium. Review is assigned to Sol Medium; acceptance,
review duration and credits are not claimed by the worker.

## Offline validation and rights

The original [verifier](verify.py) reads only this sanitized receipt and the
eight exact repository records. It enforces exact input paths, hashes, purposes,
rights and private identity metadata; two stopped branches with zero attempts;
all four unresolved verdicts and their false predicates; null unmeasured counts;
and no-policy/no-runtime boundaries. A fixed canonical receipt digest also
prevents silent mutation of remaining metadata, timestamps or conclusions.
It does not access the private artifact, project, VM, network or hardware.

The [refusal fixtures](refusal_test.py) mutate deep-copied receipts in memory,
including co-mutated valid path/hash pairs, expanded rights, altered private
identities, fabricated measurements/attempts, promoted verdicts and runtime
permissions. Unchanged controls must pass before and after. No fixtures contain
firmware or private anchors. Run both with Python `-B`; optimized-mode execution
also retains all checks because the verifier uses explicit refusals, not asserts.

Actual validation: the offline verifier passed normally and under Python `-O`;
all 46 refusal fixtures and unchanged controls passed normally and under `-O`;
both Python files compiled in memory; four local Markdown links resolved;
repository and explicit new-file whitespace checks were clean; focused
private-path/artifact-name/address/key scans had no matches. No bytecode cache
was retained. Tests verify the sanitized stop receipt, not firmware semantics.

Firmware and the retained project/tooling remain private evidence; analysis
authorization is not redistribution permission. Only independently written
MIT-licensed verification code, sanitized descriptions and opaque identities
are added. No kernel, host command implementation, policy, shared document,
ledger, device state, commit or push changed. The integration owner handles
repository publication gates and any accepted workflow measurement separately.
