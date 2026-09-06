# Work item: dynamic MT6797 reserved-memory binding decision

- **Outcome:** determine the smallest truthful change that lets the existing
  passive image owner describe Linux's initialized allocation for the Gemini's
  documented dynamic 2 MiB no-map
  connectivity reservation without treating that description as exclusive
  ownership, mapping permission or active-entry admission.
- **Owner and reviewer:** `/root` integrates; an Astra Medium specialist owns
  the upstream API and resource-lifetime decision; Sol Medium reviews any
  resulting cross-file implementation.
- **Scope:** the pinned Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`
  reserved-memory implementation and binding schema, the accepted passive
  snapshot, and `experiments/2026-09-05-mt6797-reserved-binding/`. This item may
  update or supersede that experiment with a passive-only patch and host tests.
  It does not edit the manifest, canonical series, board DT or support matrix.
- **Frozen parent:** repository commit
  `066a81226a327f50c69548e00a06ed4252fcd51d`.
- **Observed premise:** on the named Gemini, `consys-reserve-memory` is a live
  no-map node without `reg`; the admitted collector did not read its `size`,
  `alignment` or `alloc-ranges`, and its current allocation was not visible.
  Earlier durable evidence records the dynamic 2 MiB configuration. Exact
  chronology remains in
  `../2026-09-06-mt6797-consys-passive-ownership/`.
- **Acceptance:** identify which initialized kernel object owns the allocated
  base/size; distinguish DT configuration identity from allocated-resource
  identity and lifetime; determine whether a passive consumer can bind without
  invoking `of_reserved_mem_device_init_by_idx`; define revalidation and overlap
  limits; and preserve refusal for all mapping, copy, MPU, remap, DMA, power and
  firmware-start paths. Any code must replay its predecessor patch and pass
  sanitizer/refusal fixtures plus a real Buildbox object compile before use.
- **Stop/escalation:** stop implementation if the allocated extent cannot be
  obtained from a stable initialized kernel record, if safe lifetime requires
  an effectful init callback, or if the API contract conflicts with the live
  node. Report the conflicting evidence and next discriminating check; do not
  invent a hard-coded base or silently convert the node to static `reg`.
- **Hardware:** none. Do not access the Gemini, rerun the completed collector,
  use sudo, or queue a physical action from this work item.
- **Publication:** synthetic experiment authorship remains non-certifying and
  not submission-ready. No DCO identity may be invented.
- **Handoff:** a source-pinned decision with exact API/lifetime claims, proposed
  test cases, and either an implementable passive delta or a specific blocker.
- **State:** offline implementation accepted after specialist escalation and
  Sol re-review; real Buildbox object compilation is the next gate. Pinned
  source review found that `of_reserved_mem_region_to_resource()` exposes the
  initialized record without `reg` or an init callback. The implementation must
  retain the declaration separately, restrict dynamic nodes to equal one- or
  two-cell address/size widths, and describe—not certify—the record. A pinned
  allocator error path can leave a nonzero base after failed no-map marking, so
  neither lookup nor resource conversion proves successful physical reservation.
- **Efficiency loop:** eligible only if a bounded offline handoff is accepted;
  record one considered item after integration review.
