# Experiment: mainline A72 A34 provenance-owner audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-a72-a34-provenance-owner-audit` |
| Status | completed offline audit; capture-only TOPRGU boundary selected |
| Subsystem | MT6797 reset provenance and secure A72 replay state |
| Device variant | Planet Gemini PDA named development unit |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 owner |

## Question or hypothesis

Can exact retained firmware and kernel sources supply both authority inputs to
the proven A34 evaluator without treating an ordinary Linux reboot or a
zero-initialized kernel object as authority?

The hypothesis is intentionally split. TOPRGU `WDT_STATUS` may provide a
read-only reset-cause observation if captured before the mainline watchdog
initializes. Firmware-private `big_on` may be proven zero only across a fresh
secure-platform epoch with a complete writer inventory; it cannot be inferred
from Linux membership or from calling active PSCI `AFFINITY_INFO`.

## Provenance and environment

- Repository parent: `8513b645fb122e766779f276e30ce74b4af82ec5`.
- Canonical Linux baseline: pinned 7.1.3 through patch `0302`, whose SHA-256 is
  `f07b490279cedf9ee7c4f9d294c4b4e966db72715a78b2d25c2abd64b3fd861b`.
- Public Gemian kernel source: commit
  `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Public Planet LK source: commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Exact retained secure payload: private bytes identified only by SHA-256
  `2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`.
- Buildbox was used only for read-only source inspection. The managed analysis
  VM was used only for read-only AArch64 data-flow inspection. No source tree
  was copied to or from Buildbox.
- Exact public-source hashes and sanitized private-analysis facts are recorded
  in [`results/provenance-20260821.txt`](results/provenance-20260821.txt).

## Safety assessment

This audit was offline and read-only. It did not contact the Gemini, issue an
SMC, read or write a device partition, build a kernel, create a boot image,
request CPU hotplug, change a regulator or MMIO register, reboot, or shut down
hardware.

The selected next implementation is also capture-only. It may read the
already-mapped TOPRGU status word once before watchdog initialization, but it
must not classify the result as A34 authority, publish AVAILABLE, invoke a
provider, arm P30, call PSCI, or change either CPU veto.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the source-derived authority boundary and
  the selected capture-only implementation slice.
- [`results/authority-matrix.tsv`](results/authority-matrix.tsv) separates
  observations, authority, preservation, and unresolved semantics.
- [`results/provenance-20260821.txt`](results/provenance-20260821.txt) records
  exact revisions, hashes, analysis addresses, and negative findings without
  private paths or bytes.
- [`results/audit-validation-20260821.txt`](results/audit-validation-20260821.txt)
  is the passing frozen-audit validation receipt.
- [`scripts/validate.py`](scripts/validate.py) checks the pinned repository
  parent, canonical patch, matrix decisions, and safety boundary.

Run from the repository root:

```sh
python3 experiments/2026-08-21-mainline-a72-a34-provenance-owner-audit/scripts/validate.py
```

## Procedure

1. Inspect the exact vendor MT6797 watchdog header and implementation at the
   pinned Gemian revision.
2. Inspect the exact Planet LK MT6797 watchdog initialization and all calls to
   its `WDT_STATUS` reader.
3. Compare both with exact mainline `drivers/watchdog/mtk_wdt.c` after the
   canonical patch series.
4. Reconstruct the preloader ram-console status layout from independently
   matching LK and vendor-kernel readers.
5. Recheck the retained secure payload hash, on-image private replay byte, and
   every data reference to that byte.
6. Separate facts that survive source review from assumptions requiring a
   fresh secure-platform epoch or runtime capture.
7. Select only the earliest implementation that cannot open the lifecycle.

## Observations

- Vendor MT6797 defines TOPRGU `WDT_STATUS` at offset `0x0c`, with distinct
  hardware-watchdog, software-watchdog, IRQ-watchdog, debug-watchdog, SPM,
  thermal, and security bits.
- Planet LK has a reader for this register, but the pinned tree has no call to
  it. LK initialization changes MODE, INTERVAL, LENGTH, request-mode fields,
  and optionally reloads the watchdog; it does not write or read-to-clear
  `WDT_STATUS`.
- Exact mainline does not define or read offset `0x0c`. Its probe maps TOPRGU
  and then calls `mtk_wdt_init()`, so the earliest non-destructive capture point
  is immediately after mapping and before that call.
- Preloader separately stores a semantic watchdog/reset status in the retained
  ram-console header. LK and the vendor kernel agree on its signature/offset
  layout. This is not the same object as raw TOPRGU `WDT_STATUS`, and the full
  preloader value map is not present in the audited public sources.
- The secure payload's private `big_on` byte is zero in the exact image. The
  complete static cross-reference set contains the deferred A72 teardown path,
  which reads and clears target bits, and the A72 CPU-on path, which reads and
  sets target bits. No independent non-SMC runtime reader or reset-epoch
  attestation exists.
- The active `AFFINITY_INFO` path remains unsuitable as a reader: when a target
  bit is set it enters state-changing, potentially unbounded teardown.

## Analysis

LK preservation is sufficient to make a pre-`mtk_wdt_init()` raw TOPRGU read
worth implementing. It is not sufficient to classify any raw value as a
completed platform or external reset. In particular, a software-watchdog bit
would identify exactly the ordinary-reset class that A34 forbids accepting.
Zero is also not self-authenticating: it needs agreement with the preloader
status and a proven fresh platform epoch.

The secure replay proof is narrower than earlier wording implied. It is not a
Linux generation counter. A fresh load of the exact secure payload starts the
byte at zero, and the existing CPU8/CPU9 boot veto prevents the only set path
from running before A34. But a warm reset is not itself proof that the secure
payload was freshly initialized. The proof chain must therefore start with a
known-good cold/platform or external-reset epoch; Linux BSS zero and an
ordinary reboot remain rejected substitutes.

The smallest honest next implementation is consequently a one-read TOPRGU
capture in the existing watchdog owner, before any watchdog initialization.
It should retain the raw word and provide a typed read-only snapshot for a
later provenance combiner. It must expose no boolean “safe reset” conclusion
and have no A34 production caller. Ram-console validation and cold-epoch
combination remain later, separate boundaries.

## Conclusion

`confirmed` for source preservation of raw TOPRGU `WDT_STATUS` through pinned
LK and for a safe mainline capture point before `mtk_wdt_init()`.

`confirmed` for the exact retained secure payload's zero initial private
replay byte and the two lifecycle writer families described above.

`rejected` for using raw `WDT_STATUS`, a command-line boot reason, Linux
zero-initialization, or an ordinary Linux reboot alone to open A34.

`inconclusive` for the complete production A34 authority tuple until a later
combiner validates independent reset observations and a fresh secure-platform
epoch. No CPU8 request or device boot follows from this audit.

## Follow-up

The authoritative next action is maintained in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md). Implement and prove only the
capture-only TOPRGU snapshot on Buildbox, then audit the ram-console/cold-epoch
combiner. Keep the lifecycle CLOSED and both CPU vetoes unchanged.
