# Work item: MT6797 camera-clock current-upstream architecture

- **Outcome:** Produce an independently reviewable current-public-source
  disposition for local patches 0021/0022 and their camera consumer boundary:
  identify the smallest coherent upstream clock topic with a real consumer and
  validation story, or record an exact stop.
- **Owner and reviewer:** `gemini_reasoner` / Sol Medium owns the source audit;
  Project Planning integrates; Astra Medium reviews any clock/resource ownership
  decision.
- **Scope:** This experiment directory only. Read local patches 0021/0022, the
  frozen July camera design/contract, current official Linux clock, binding,
  MT6797 DTS and media sources, and bounded public history. Map the immediate
  Camsys/Imgsys clock consumers without reopening display patches 0028–0044 or
  editing shared files.
- **Model route:** Sol Medium for cross-subsystem current-tree reasoning; Astra
  Medium review because clock gates, SMI/IOMMU and camera lifetime are shared
  hardware ownership.
- **Stop/escalation:** Stop after classifying both patches, current overlap,
  provider/consumer dependencies, upstream order and testability. Do not
  implement. Escalate on conflicting clock-parent/gate/domain evidence or if a
  proposed provider would have no truthful current consumer.
- **Parent:** repository commit
  `c8344011557b2369e8d15187a5969103108a2c18`; patch 0021 SHA-256
  `df7b724bfdd38301416a4e0474338a9f7ef8fbde882d3e27a39c22b7f12c8f05`;
  patch 0022 SHA-256
  `03dfe99596f00f1c406c36da968b9d53de2368008c26c8caebc62cb9a28eee26`;
  July README/design/pipeline SHA-256 values
  `050017875b353d95073f0e84e4aea6aa93e93d3fd6d193d2dfe89479899b6e08`,
  `bc53b7c292fd556395d8a9750776c30cde98252841ba5d1f3592108334f4dfca`,
  and `ac7452eaa33f71474b23cbecd3a28d191dcc4d42c485fa052f71c6f457ede9d1`.
  Record exact current public revisions and file identities.
- **Dependencies:** Public source/network access only. No build, device,
  private vendor source, retained binary, or upstream feedback.
- **Worktree:** Shared checkout; ownership is limited to
  `experiments/2026-09-07-mt6797-camera-clock-upstream-architecture/`. Other
  agents work concurrently; do not revert or overwrite their edits.
- **Validation:** Strict JSON; frozen/current hashes; local links; whitespace;
  canonical local positions; source-backed compatible, gate, parent and consumer
  claims. Separate provider compilation/schema feasibility from camera runtime.
- **Hardware:** None. No Gemini/private access, clock operation, camera probe,
  stream, register access or device-session admission.
- **Upstream:** Identify target clock/Devicetree routes, truthful authorship and
  DCO boundary, dependency order and local-patch removal conditions.
- **Owner-away work:** Entire item is offline. An accepted stop does not enable
  Camsys, Imgsys, SENINF, ISP, a sensor or an IOMMU/SMI path.
- **Device readiness:** Not applicable; no queue/candidate change.
- **Handoff:** Create `README.md` and `results/source-review.json` with exact
  sources, patch dispositions, dependency map, validation, limits,
  recommendation and `review_ready_utc`.
- **State:** complete; review-ready at `2026-09-07T20:47:53Z` and accepted
  on first review at `2026-09-07T20:52:42Z`.
- **Efficiency loop:** If accepted, Project Planning appends one measured offline
  item to pilot 04; credits remain unavailable unless actually measured.
