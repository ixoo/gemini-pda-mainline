# Experiment: MT6797 thermal/AUXADC transaction implementation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-04-mt6797-thermal-transaction` |
| Status | `completed`; hardware-free implementation gate passed |
| Subsystem | MT6797 thermal controller and AUXADC transaction |
| Device variant | Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-04 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | CPU8/CPU9 thermal/frequency-observability gate |

## Question or hypothesis

Can the source-frozen MT6797 thermal/AUXADC order be represented by a real
disabled-node production adapter and proven at every success/failure boundary
without activating hardware?

The hypothesis is that one callback-driven executor can be shared by the
production adapter and a pure KUnit fixture. That makes the complete ordering
and unwind independently observable before any DT enablement or device boot.

## Provenance and environment

- Repository parent: `afabe4df4e18eca3ab0d70648c9db1899479bd28`.
- Canonical series before this gate: 505 entries, SHA-256
  `0fb18bba40d9d55bb6dc7e0f3d5b3ebfe7bdbc36963991ac77c1913883071010`.
- Prepared Linux source state:
  `c8b7023e45d7b15dd76d2bb3c2b9376be2e213fa738da399ce3ee3f11172694c`;
  recursive integrity `e3e2f0a36e172ecd7ad7753433ec8c03429d904fa9fd79d64b269546a99086b1`.
- Production and test parent hashes are pinned in
  `scripts/generate-on-buildbox`.
- Source contracts come from the preceding
  [transaction audit](../2026-09-03-mt6797-thermal-auxadc-transaction-audit/README.md),
  [reset repair](../2026-09-03-mt6797-infracfg-reset-repair/README.md), and
  [PWRAP serviceability pass](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md).
- Build backend: Buildbox only.
- Boot path: none. This gate must not create a device candidate.

## Safety assessment

Patch generation operates on bounded copies of five exact files in the
Buildbox-managed prepared source. KUnit invokes pure callbacks backed by an
in-memory event ledger. It performs no MMIO, clock, reset, NVMEM, thermal-zone,
platform-device, storage, network, firmware, or device operation.

The production adapter cannot probe because both MT6797 DT nodes remain
disabled and the thermal node deliberately does not gain its reset phandle in
this gate.

## Associated code

- `DESIGN.md`: production order, unwind, and deferred contracts.
- `contract.json`: exact inputs and forbidden scope.
- `scripts/source_edits.py`: deterministic production and KUnit edits.
- `scripts/validate_source.py`: edited-source semantic checks.
- `scripts/validate_patches.py`: normal-format-patch and path checks.
- `scripts/generate-on-buildbox`: pinned two-patch generator and replay gate.
- `scripts/run-kunit-qemu`: bounded, no-network arm64 QEMU runner.
- `scripts/classify-kunit.py`: exact six-case KTAP classifier.
- `results/patch-generation-20260904.txt`: exact generation and admission
  receipt.
- `results/buildbox-kunit-build-20260904.txt`: exact published build receipt.
- `results/kunit-qemu-20260904.txt`: exact isolated runtime result.

## Procedure

1. Validate and publish the deterministic generator from a clean repository.
2. Generate one production patch and one focused KUnit patch from the exact
   Buildbox source state.
3. Replay the normal patches, run semantic and strict style checks, and fetch
   only the checksum-covered review package.
4. Admit the two patches in canonical order, add one isolated profile, and
   audit every manifest profile for canonical-subsequence compliance.
5. Build the exact pushed profile on Buildbox and execute the focused suite in
   no-network arm64 QEMU.

## Expected observations

- The production patch changes only the MediaTek AUXADC thermal driver and its
  internal header.
- The test patch changes only MediaTek thermal Kconfig/Makefile and adds one
  focused KUnit source.
- The exact success ledger contains six prepare operations before the channel
  commit, all six enables before any release, and all six releases before any
  first-sample check.
- Each of the 31 fallible operation positions returns to a completely closed
  state through the same reverse cleanup path.
- Neither patch changes DT, references `AUXADC_MISC`, requests an IRQ, adds PM
  callbacks, programs CPU policy, or performs a device action.

## Result

The first submission was correctly rejected before copying or editing source:
the managed tree had advanced from the audit state through canonical reset
patches 0514--0516. All five pinned thermal parent-file hashes were unchanged.
The next review stopped at `git diff --check`: Python string escapes had kept
generator indentation ahead of tabs. No package was published. The generator
now emits canonical kernel indentation and literal diagnostic newlines. Patch
generation then reached the semantic validator, which rejected an ambiguous
cleanup-definition anchor that also matched its executor call. A subsequent
run reached the patch validator and exposed an indentation-sensitive reset
anchor. Both anchors are now definition-specific. The latest run passed source
semantics, patch shape, and deterministic replay, then stopped at strict style
review: 17 production checks and two test warnings plus 47 test checks. It
published no package and performed no build or device action. The generator now
uses normal continuation layout, sleepable delay, and explicit KUnit callbacks
instead of flow-control macros. That repair reduced the next strict review to
six production and four test alignment checks, again with no package, build,
or device action. The remaining call continuations are now aligned or reduced
to single lines. The following review passed the test patch with zero findings
and left one production first-sample continuation check; that call is now one
line. Canonical admission, build, and isolated KUnit execution were still
pending at that point.

The final Buildbox generation at repository commit `84d66801449c...` passes
source semantics, exact two-patch replay, package checksums, and strict
checkpatch with zero errors, warnings, or checks. The fetched patches are
byte-identical to canonical patches 0517--0518. The resulting 507-entry series
and all 178 manifest profiles pass the canonical-subsequence invariant.

Exact published repository commit `1397a6fe14a7...` built the isolated profile
on Buildbox. Both the production thermal adapter and focused KUnit object
compiled and linked; 123 DTBs and all package checksums passed. The fetched
package then ran once in no-network arm64 QEMU. Its only focused suite passed
all six exact cases, including the complete success ledger, each of 31
fallible positions returning to a closed state, invalid-start rejection,
APMIXED mask, idle predicates, and first-sample validity. The private raw log
is represented by SHA-256 `f47ce9b88a40...` and remains ignored.

No boot candidate was built. No Gemini, firmware, storage, clock, reset, MMIO,
thermal zone, or AUXADC hardware action occurred.

## Follow-up

Separately add the thermal reset description and design one minimal
serviceability candidate. Enable only the thermal consumer; keep the standalone
AUXADC platform consumer disabled so ownership does not compete. Require exact
calibration-provider, reset, clocks, ordered transaction, all-bank first-valid
samples, thermal-zone, console, USB/netcat, eMMC, PWRAP, and MT6351 evidence,
then recover to changed-ID Gemian and attest unchanged `boot2`. Keep
IRQ/watchdog protection, trips/cooling, cpufreq/OPP, CPU8/CPU9 load, idle, and
suspend excluded until valid temperature observability is proven.

## Conclusion

The hardware-free gate passes. The MT6797 path now has one source-pinned,
fail-closed transaction and an exhaustive pure failure ledger. This proves
ordering, cleanup, compilation, and helper behavior, but it deliberately does
not yet claim that the Gemini hardware returns valid temperatures.
