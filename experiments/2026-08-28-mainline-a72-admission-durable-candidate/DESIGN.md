# Durable physical candidate contract

The candidate changes no Device Tree supplier, controller, binder, CPU, or
serviceability node relative to the retired admission candidate. Canonical
patches `0415`--`0418` add the only source delta: immutable retained records 2
and 3 plus their controller calls.

Before a boot, the exact hypothesis is: controller entry commits record 2
before prerequisites; a consumed source-register, derive, or publish failure
commits its exact record-3 terminal; an admitted request leaves record 3 empty
and transfers evidence ownership to the record-1 transition ledger. The unique
observation is therefore independent of USB timing and survives only if the
platform retains the corresponding record across the reset.

The attempt changes the next action as follows:

- exact CPU8 online frame and terminal transition ledger: begin bounded CPU8
  coherency/accounting validation; do not request CPU9 yet;
- exact record-3 terminal: repair only the named source branch;
- entry plus empty record 3 and empty ledger: localize prerequisite deferral or
  interruption before consumption;
- entry plus transition ledger: repair only its last complete physical stage;
- no exact or conflicting evidence: retire the candidate and improve the
  evidence boundary without repeating it.

There is one physical boot budget. The candidate permits at most one CPU8
request and no CPU9 request, CPU_OFF, or retry.
