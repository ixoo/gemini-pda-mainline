# Experiment: owner-away session preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-05-owner-away-experiment-preparation` |
| Status | preparation in progress; initial design below, current readiness in the linked queue |
| Subsystem | A53 serviceability, authenticated USB, keyboard and eMMC |
| Device variant | Named Planet Computers Gemini PDA, MT6797 |
| Date(s) | 2026-09-05 |
| Investigator(s) | A53 baseline and queued device tests; initial design by Gemini mainline project |
| Tracking issue | [Preparation queue](../../project/experiment-queue.json) |

## Question or hypothesis

Can each session packet be prepared and independently validated offline so that
the owner's return requires only its stated physical actions and an already
reviewed, attributable observation? The proposed hardware hypotheses are below.
The authenticated baseline now has a reproducibly constructed private candidate
and reviewed session tools; its [preparation evidence](baseline/PREPARATION_RESULTS.md)
and [integration review](baseline/INTEGRATION.md) own the current gates. Keyboard
and eMMC preparation is linked below. None has physical admission, and queue
membership does not imply readiness.

## Provenance and environment

- Planning parent: `b18a0a13397abcfdb3956ff8abfb48bdd6efe01e`.
- Candidate foundation: the exact passed
  [PWRAP-reset serviceability experiment](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md).
  Its artifact identity, rather than the current profile name, is authoritative.
- Audit the tested upstream revision, patch contents/order, resolved config,
  toolchain, package inventory, Image, composed DT, initramfs and LK container
  before selecting a new baseline. Record every proposed delta and its purpose.
- The present `mt6797-pwrap-reset-serviceability` profile selects a later frozen
  series; equivalence to its earlier runtime-tested package is not established
  by that name. The quarantined historical eMMC profile is not a foundation.
- The [baseline preparation record](baseline/PREPARATION_RESULTS.md) now pins
  candidate, protocol, runner and installer identities and their offline checks.

## Safety assessment

The initial preparation design involved documentation only; it performed no
device access, build, installation or runtime observation. Subsequent milestones
belong in their own records. Preparation uses the
[session contract](../../project/DEVICE_SESSION.md) and
[safety policy](../../docs/SAFETY.md).

Future packets must specify finite action/time budgets, refusal conditions,
receipt-bound boot attribution and reviewed recovery before admission. Preserve
CPU0–7 serviceability with CPU8/9 offline and the existing power/load limits.
No packet admits thermal consumption, CPU load, rail/frequency changes or suspend.
Any boot2 preparation requires the complete current guarded deployment path;
historical installers cannot be reused without adopting and validating it.

The completed [V4 thermal session](../2026-09-04-mt6797-thermal-snapshot/V4_RUNTIME_ACCEPTANCE.md)
is consumed and supplies no reusable action budget for these packets. Boot2
selection remains physical; admission of one packet never starts another.

## Associated code

The [baseline session](baseline/SESSION.md) links its constructor, validators,
guarded installer, capture and recovery helpers. The [keyboard packet](keyboard/README.md)
and [eMMC packet](emmc/README.md) own their observers, classifiers and fixture
results. Their later launchers and physical prerequisites remain preparing;
neither dependent packet is included in the first baseline boot.

## Proposed session packets

<a id="a53-authenticated-baseline"></a>
### A53 authenticated baseline

**Hypothesis:** a separately attributable authenticated USB administration
initramfs preserves the proven A53, PWRAP, eMMC, keyboard, console and recovery
contracts while accepting only the intended authenticated administrative path.

Preparation must resolve the exact foundation above, audit userspace source and
redistribution rights, define credential provisioning without committed secrets,
separate kernel logs from the interactive console, and freeze the minimal delta.
Validate successful authentication, rejected credentials, interruption and
recovery with the exact candidate userspace. Authentication and end-to-end
serviceability on this proposed candidate have no runtime evidence yet.

An attributable serviceability pass permits dependent packets on matching
inputs; it does not complete cold-boot reliability. Authentication failure with
otherwise intact serviceability returns to userspace design. A regression in
binding, console or recovery rejects the baseline and blocks its dependents.
Missing identity or transport gives no hardware conclusion. The separately
defined repeated-cold-boot acceptance remains open after a first pass.

<a id="keyboard-coverage"></a>
### Keyboard coverage

**Hypothesis:** the frozen matrix and VT map produce the declared key and
modifier press/release events for a specified physical sequence, with a readable
console and no retained modifier after release.

Prepare a finite owner key sequence, exact input-device/map checks, event
classifier and synthetic malformed/missing-event cases using the
[keyboard evidence](../../docs/hardware/keyboard.md). The [packet](keyboard/README.md)
owns the proposed sequence, bounds and coverage; actual metadata, delivery and
session integration remain prerequisites. IRQ/wake, rollover and unknown
contacts must not be inferred from a map-only pass.

Execution depends on the new baseline's attributable USB/console pass and
matching candidate inputs, plus the owner's key presses. It need not wait for
completion of the cold-boot reliability series. Correct captured events with
incorrect visible characters isolate VT/userspace mapping; incorrect events
retain the input-path question. Missing or ambiguous capture is inconclusive.
A pass establishes only the explicitly exercised keys and combinations.

<a id="emmc-readonly"></a>
### Read-only eMMC regression

**Hypothesis:** bounded reads from explicitly reviewed eMMC ranges complete
without targeted controller errors or loss of baseline serviceability on the
exact candidate, while issuing no storage write or mount operation.

Prepare live device/range identity checks, finite byte/time limits, a read-only
observer and failure classifier against the
[existing storage evidence](../2026-07-25-emmc-development/README.md). Target
ranges and finite budgets are proposed in the [packet](emmc/README.md);
its launcher and exact session integration remain preparing. Private partition
contents must not enter published evidence; retain only reviewed metadata and results.

Execution depends on baseline serviceability and reviewed recovery, independently
of keyboard coverage. Identity ambiguity refuses before reads. Targeted errors
reject the bounded transfer claim; lost attribution is inconclusive. A pass
does not establish filesystem safety, persistent-root I/O, broad reliability,
suspend or permission to write any partition.

## Procedure

Each packet must complete its input audit, frozen protocol and decision map,
offline fixtures, applicable Buildbox/package validation and independent review.
Only then can it request a device slot through the session contract. Concrete
invocations and numeric budgets belong in the completed packet before admission.
The [roadmap](../../docs/ROADMAP.md) alone orders work.

## Observations, analysis and conclusion

The initial record established preparation scope. The linked records now hold
offline construction and protocol evidence, while all three new hardware
hypotheses remain untested. Existing subsystem results remain scoped to their
original artifacts.

## Follow-up

Track preparation and dependencies in the [queue](../../project/experiment-queue.json).
Record each completed packet's exact inputs and validation here or in a linked
owning experiment; update support claims only after attributable runtime evidence.
