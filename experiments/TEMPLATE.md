# Experiment: concise title

## Record

| Field | Value |
| --- | --- |
| ID | `YYYY-MM-DD-short-name` |
| Status | `planned`, `running`, `completed`, `inconclusive`, or `superseded` |
| Subsystem |  |
| Device variant |  |
| Date(s) |  |
| Investigator(s) |  |
| Tracking issue |  |

## Question or hypothesis

State one falsifiable question. Separate prior reports from the claim being
tested.

## Provenance and environment

- Kernel release/commit:
- Patchset SHA-256 or patch revision:
- Configuration SHA-256:
- Tool and compiler versions:
- Boot path and target slot/partition:
- Referenced public sources or vendor-tree paths and commits:

## Safety assessment

Describe recovery prerequisites, protected areas, electrical limits, write
boundaries, stop conditions, and why the procedure is reversible. State
explicitly whether the procedure is read-only.

## Associated code

List every script, source file, fixture, dependency, and invocation. Explain any
privileges or hardware access required.

## Procedure

Provide numbered, repeatable steps. Include expected observations and the number
of repetitions. Destructive or state-changing steps must never be implicit.

## Observations

Record what happened without interpretation. Link small sanitized evidence in
`results/`; describe any private evidence retained elsewhere.

## Analysis

Explain how the observations support or contradict the hypothesis. Identify
alternative explanations, uncertainty, and conflicting evidence.

## Conclusion

Use `confirmed`, `rejected`, or `inconclusive`, scoped to the named variant and
exact revisions. A compile-only result cannot establish hardware behavior.

## Follow-up

Link resulting hardware-document updates, support-matrix changes, patches,
issues, and the next discriminating experiment.
