# MT6797 connectivity producer source-attribution work item

- **Outcome:** resolve or sharply bound the build-selected outer producer of
  `do_connectivity_driver_init()`, the origin/conditions of its chip argument,
  how its final aggregate is handled, and any corresponding teardown path at
  Planet commit `c5b0be85017ad0c599725e8273842efdbecdd88a`.
  Preserve source reachability separately from runtime execution, shared
  resource ownership, firmware success and radio safety.
- **Parent:** repository commit
  `45b57d265252e8b9068038b84e53b68624f3bab1`; direct input is the accepted
  `experiments/2026-09-06-mt6797-wlan-drv-init-lifecycle-source-attribution/`
  result and its immutable predecessor chain.
- **Owner and reviewer:** Astra Medium owns the hard producer/registration
  uncertainty; `/root` integrates; Sol Medium independently reviews. The owner
  may edit only this new experiment directory and must preserve concurrent
  work.
- **Frozen selection boundary:** begin from the already pinned
  `common/common_detect/Makefile` tuple and its selected product configuration.
  Revalidate that tuple field-for-field before choosing any new body. Fetch
  only complete Makefile-selected detector/stub source files needed to locate
  definitions or direct calls of `do_connectivity_driver_init`; filenames or
  directory inventory alone are not caller evidence.
- **Bounded fetch:** at most two predeclared batches, seven new regular files,
  one immediate-directory inventory only if a selected Makefile path cannot be
  mapped to a regular file, and two exact contextual rereads of inherited
  functions. Batch 1 is limited to the complete selected detector/stub bodies
  justified by the Makefile. Batch 2 may follow only direct caller,
  registration, chip-identity or teardown edges named by batch 1. Count and
  freeze all successes, failures and no-hits; no whole-tree/code search,
  archive, checkout, mirror or retained source body.
- **Acceptance predicates:** classify independently with exact source/line/
  symbol citations, conditions, missing edge and next discriminator:
  1. exact Makefile-selected producer corpus and relevant build conditions;
  2. direct caller/producer of `do_connectivity_driver_init()` or a bounded
     unresolved result;
  3. chip argument provenance and whether the MT6797 `0x6797` case is selected
     by established source conditions rather than assumed runtime state;
  4. handling of the final aggregate, including return, conversion, discard,
     retry or gating of later calls;
  5. exact initialization registration/invocation mechanism and ordering;
  6. any actual exit/teardown reference joining the established gen3 exit
     export, or a bounded unresolved result. Never infer teardown by reversing
     initialization order.
- **Evidence discipline:** store full identity tuples and complete request
  receipts only. Declare literal independent canonical freezes for all source
  tuples, citation anchors and immutable request evidence before verifier
  construction. Inherited tuples/files must match their independently pinned
  predecessor values field-for-field. Expected hashes may not be generated
  from mutable evidence at startup.
- **Validation:** normal and optimized verification must reject co-mutation of
  source/request/citation evidence, wrong selected objects or config, invented
  producer/registration/exit edges, assumed chip ID, hidden aggregate loss or
  retry, order inversion, built-in/module conflation, authority promotion,
  no-hit deletion and budget drift. Run JSON, in-memory compile, whitespace,
  local links, license/source-rights, sensitive-data, `git diff --check` and the
  common repository gate.
- **Source rights:** public vendor-derived source is evidence only. Retain no
  source body/excerpt and infer no reuse or redistribution right.
- **Effects and stop conditions:** no device, SSH, private capture, VM,
  Buildbox, kernel build, candidate, boot2, radio action, shared-file edit,
  staging, commit or push. Stop each unresolved edge when two batches are used,
  the file budget is reached, selection would require a repository-wide search,
  or evidence conflicts.
- **Handoff:** README, inputs, complete search receipts, verdicts, independent
  freeze, normal/optimized verifier and validation record. Report exact
  resolved/unresolved edges, budgets, checks and next discriminator.
- **Efficiency loop:** if accepted, record one sanitized item in active pilot
  03; credits remain unavailable unless actually measured.
- **State:** contract frozen; bounded public-source audit authorized.
