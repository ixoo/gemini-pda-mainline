# Work item: freeze the MT6797 HIF upstream architecture

- **Status:** accepted design stop at `2026-09-07T18:22:39Z` after one
  documentation-only shared-hardware lifetime repair.

- **Outcome:** map the already compiled private HIF/MTKE/EMI components onto
  current Linux subsystem ownership and identify the smallest coherent first
  upstream series, or return an exact design stop. Do not produce dead library
  code merely because it compiles.
- **Parent:** repository commit
  `5aa5e7d93114155cdefe00bcf462db168cdd45fc` on `origin/main`.
- **Owner and reviewer:** Sol Medium owns current-tree cross-file design;
  Astra Medium reviews any proposed shared CONSYS/EMI/AP-DMA hardware ownership
  before a later Luna High implementation contract. `/root` integrates records.
- **Model route:** `gemini_reasoner`, `gpt-5.6-sol`, medium. No implementation
  route is selected by this item.
- **Frozen project inputs:** the accepted
  [HIF core](../2026-09-05-mt6797-wifi-hif-core/README.md),
  [DMA/EMI contract](../2026-09-05-mt6797-wifi-contract/HIF_DMA_CONTRACT.md),
  [connected CONFIG phase](../2026-09-05-mt6797-wifi-contract/CONFIG_PHASE.md),
  [mainline lifecycle design](../2026-09-06-mt6797-mainline-connectivity-interface-design/README.md),
  [passive CONSYS runtime boundary](../2026-09-06-mt6797-consys-passive-boot/README.md),
  proposal patches `0001` through `0012` below `patches/proposals/`, and their
  existing compile/fixture evidence. Historical/private sources remain evidence,
  not code to copy. Exact input hashes belong in the result receipt.
- **Current upstream inputs:** pin current official mainline and relevant
  MediaTek/network/DMA/reserved-memory sources, bindings, maintainers and public
  overlapping efforts. Use primary sources. Checking refs changes no manifest.
- **Owned scope:** read-only review; `/root` may create only this experiment's
  work contract, source receipt, design record and validation record. Kernel
  patches, proposal patches, configs, manifest, series, roadmap, registries,
  private captures and device state are frozen during design.
- **Questions:** determine whether existing `mt76`/MediaTek CONN infrastructure
  matches the observed gen3 AHB SDIO-like protocol; assign ownership for CONSYS
  power/reset/remap/protection/reserved EMI, HIF MMIO/host IRQ and the AP-DMA
  channel; decide the firmware/binding boundary; identify which compiled helpers
  are upstream-shaped versus experiment-only; and specify a reviewable patch
  split that has an actual caller and test story.
- **Acceptance:** return a source-pinned ownership table and dependency graph;
  explicitly compare identity, register protocol, transport and resource
  contract before driver reuse; preserve the separate packet-DMA and firmware-EMI
  domains; account for probe failure, uncertain DMA completion, remove, suspend
  and shared-client lifetime; state exact bindings/maintainer routes; select one
  smallest implementation-ready slice with frozen interfaces and checks, or an
  exact stop with the next discriminating evidence.
- **Mandatory exclusions:** do not resume the owner-closed retained-instruction
  observer/checker, use its private outputs, create another diagnostic framework,
  import vendor ABI/source, invent a generic DMAengine provider, treat reserved
  EMI as a packet pool, choose an address width/extension rule without evidence,
  or infer teardown by reversing initialization.
- **Stop conditions:** stop if ownership requires an unproved address-extension,
  DMA-idle, power-domain, firmware, coexistence or teardown contract; if current
  overlap changes the intended owner; or if an initial series would be unused
  scaffolding. Name the missing primary fact and next bounded check.
- **Validation:** JSON/link/hash checks and focused consistency review. Do not
  repeat an identical HIF compile. A Buildbox build is considered only after a
  later accepted implementation changes exact kernel inputs and is committed,
  pushed and clean.
- **Hardware and private analysis:** none. No VM, device, firmware/radio action,
  capture read, boot candidate or deployment.
- **Upstream:** no contact or submission. Actual authorship, truthful DCO and
  coding-assistance disclosure remain later gates.
- **Handoff:** a concise architecture verdict, frozen owner/interface table,
  smallest patch split or stop decision, current-source receipt, limitations and
  review-ready UTC. The worktree contains concurrent user changes; do not edit or
  revert them.
