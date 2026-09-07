# Work item: refresh the MT6797 display upstream architecture

- **State:** accepted design stop at `2026-09-07T19:38:50Z` after one
  hardware-contract documentation repair and independent Astra Medium review.
- **Outcome:** map the existing MT6797 display, panel and backlight work onto
  current upstream DRM/SoC/PHY/PWM/regulator interfaces and select the smallest
  coherent upstream-facing topic with a real consumer/test story, or return an
  exact design stop. Do not enable a panel from a software-selected name or
  submit dead SoC scaffolding.
- **Parent:** published repository commit
  `2af9532b3b1c1850cfa071a0f279154127a04db1` on `origin/main`.
- **Owner and review:** Sol Medium owns current-tree cross-file design;
  `/root` integrates. Any novel shared display-power, reset, bias or MIPI-PHY
  ownership proposed for implementation requires an independent Astra Medium
  review before Luna High work. The owner is not alone in the repository,
  owns only this experiment directory and must not edit/revert concurrent or
  shared files.
- **Model route:** `gemini_reasoner`, `gpt-5.6-sol`, medium. No implementation
  route is selected by this item.
- **Frozen project inputs:** parent-pinned canonical patches 0028 through 0044
  below `patches/v7.1.3/`; panel recovery README SHA-256
  `31d566248f3bcddcd6b31db1f3121628474b2c769777a13904a7210f09b3ff10`;
  input/backlight recovery
  `67a6dcea22135ba6b5f87995be6d11e196133a35fc02567608a89342693ca430`;
  display-mutex recovery
  `02320df194edd35078ca8a2a1ec74f9688fd8af22fac3ca18859e73dedee3d99`;
  durable live resource map
  `f3f7a191e3e41d8e63f4658a437006b9d8b0e3d01a412a7f38b59f77c57f51b4`;
  support matrix
  `58cbc5e8d6bf1bda968260e0347f1deb65adc50562f59f79baef953bf69f5947`.
  Pin exact hashes for all selected local patches and any additional project
  evidence in the result receipt.
- **Current upstream inputs:** inspect current official mainline, DRM/MediaTek
  integration, PWM and DT-schema refs as needed. Fetch individual primary
  source/binding/MAINTAINERS files only; retain no Linux tree. Pin ref, URL,
  byte hash and relevant absence. Search current public mailing-list overlap
  only where it can change ownership or patch ordering. Do not treat posting as
  acceptance.
- **Dependency graph:** account explicitly for M4U/SMI, CMDQ/GCE, display mutex,
  MMSYS routes/resets, OVL/RDMA and fixed-function components, DSI host,
  MIPI-TX PHY, SoC DT nodes, the Gemini single-DSI pipeline, panel variant,
  reset ownership, positive/negative bias rails, display PWM and standard
  backlight consumer. Separate reusable SoC support from board-specific panel
  and power facts.
- **Questions:** determine which local behaviors are absent, present or
  superseded upstream; whether existing compatibles and drivers match exact
  identity/register/transport/resource contracts; whether any subset has an
  immediate upstream caller; whether the panel descriptor remains blocked by
  NT36672-versus-SSD2092 evidence; whether GPIO reset can truthfully replace
  MMSYS `LCM_RST_B`; whether a generic regulator compatible is justified for
  the I2C `0x3e` bias protocol; and how PWM/backlight ownership composes with
  the panel and display power domain.
- **Per-patch disposition:** classify every local patch 0028 through 0044 as
  retain/adapt/split/superseded/hold/historical-only. Preserve canonical
  dependencies and distinguish compile evidence on Linux 7.1.3 from current
  applicability, schema validation and hardware support.
- **Acceptance:** source-pinned current matrix; exact dependency graph and
  maintainer/tree routes; per-patch disposition; explicit panel/bias/reset
  contradiction handling; evidence-transfer limits; and one smallest coherent
  implementation-ready series with frozen interfaces/checks or an exact stop
  with one next discriminator. A first topic must be useful to a current or
  immediately following consumer and must not silently enable hardware.
- **Mandatory exclusions:** no device/SSH, private capture, DSI/I2C/GPIO/PWM or
  panel action, vendor ABI/source import, speculative compatible, claim that
  `lp3101` proves LP3101 or TPS65132 silicon, conflation of DSI PLL request and
  DRM pixel clock, reuse of an NT36672E command table for an unproved variant,
  GPU work, kernel patch/config/manifest/series edit, build, upstream contact,
  authorship or DCO action.
- **Bounds:** at most 40 current primary source/binding files, 20 public message
  pages and the 17 local display patches. No whole-tree clone, broad GitHub
  code search, device access, private raw evidence or binary analysis.
- **Stop conditions:** stop if panel identity, bias/reset electrical ownership,
  current overlap, shared power/IOMMU/CMDQ lifetime or absence of a real caller
  prevents a coherent first topic. Name the missing primary fact and next
  discriminating check; do not shrink the intended end state into an unused
  library-only patch merely because it compiles.
- **Outputs:** create only `README.md`, `results/source-review.json` and optional
  `VALIDATION.md` under this experiment. No shared-file edits. Record exact
  input hashes, links, current refs, limits and review-ready UTC.
- **Validation/effects:** JSON/link/hash checks, canonical patch-order check and
  focused consistency review. No Buildbox run unless a later accepted
  implementation changes kernel inputs and is committed/pushed clean. No VM,
  device, firmware, panel, display-power or upstream-publication effect.
- **Handoff:** concise architecture verdict, dependency/ownership graph,
  per-patch table, smallest series or stop, exact next discriminator,
  limitations and review-ready UTC.
- **Efficiency loop:** if independently accepted, append one sanitized accepted
  offline item to the active workflow cohort with actual routes/timestamps,
  review result and measured credits or explicit unavailability.
