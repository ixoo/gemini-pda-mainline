# Retained QEMU result assessment

The eight intended reset arithmetic cases passed in the retained run. Four
additional upstream virtual-CPU interrupt cases also passed. This is a
separate offline assessment of complete immutable evidence: the original
execution gate remains **REFUSED**, because its contract expected two suites.
No guest was repeated and the execution contract remains unchanged.

The [assessment record](results/qemu-offline-assessment.json) pins its inputs,
exact ordered suite/case names and checks. The [original attempt](VALIDATION_ATTEMPT_1.md)
retains the refusal, complete serial/QMP streams and source attribution of the
unexpected `refcount_interrupt` suite. The intended cases inspect mapping,
descriptor and register-address arithmetic; none establishes provider
registration, MMIO transactions or Gemini hardware support.

## Reproduction and review

Read the exact evidence tree from Git revision
`f34f0b57532e4b67ba0dd9f011b1b8f6e52eff2d`, preserving CRLF bytes.
Both independent review and coordinator accounting completed these checks:

1. Pin `inventory.json` to
   `9c846b56ceabf7cd2e977f6595efb1feda3067d7021abaff20f4d820d37fb87c`.
   Require its 15 exact members, plus only the inventory and `.gitattributes`,
   and verify every digest and all seven embedded log digests.
2. Load the original execution helper and contract at `30f20586`, with the
   digests recorded in the assessment. Require its original `classify_exit`
   and exact generated argument list to pass. Its `classify_log` must still
   raise the original recorded KTAP refusal, and both original result and
   completion decision must remain `REFUSED`.
3. Decode the pinned serial bytes strictly, normalize CRLF only, and compare
   all KTAP tokens to one `1..3` plan followed by the assessment's exact ordered
   suites. Each suite must have its own four-case plan, four exact passing
   case lines and matching suite result. The order is explicitly recorded;
   JSON object ordering in the original two-suite contract is not the oracle.
4. Require exactly one correct release banner, the admitted command line,
   final power-down line, original stream-size limits, and no failure, skip,
   bailout, panic, oops, BUG, warning, NUL or escape character. Inspect the
   pinned diagnostic totals: each suite reports four passes and zero failures
   or skips.
5. Require the five raw QMP objects to be the greeting, capability reply,
   resume event, start reply and guest shutdown. Raw events must equal the
   original process receipt. Confirm zero exit, no host stop or termination,
   absent process group, empty stderr and elapsed time within 45 seconds.
6. Match the package identity to the 132-member preflight receipt and verify
   identical before/after prefix-check receipts, including their tool/setup
   identities, 2257 prefix members and 50 resolved libraries. These remain
   historical check receipts with the later checker correction disclosed in
   the original-attempt review; no retrospective execution is claimed.

Independent source review retrieved and hash-checked the pinned upstream
Makefile and interrupt tests listed in the original attempt. Direct
`CONFIG_KUNIT` selection accounts for the extra suite; disabling the separate
IRQ-test option did not remove it. The IRQ cases exercise virtual local
interrupt-state transitions, so they are distinguished from the eight intended
arithmetic cases.

The resulting observation is three complete suites and twelve passing cases,
including all eight intended cases, with guest-requested poweroff. Total
recorded run time is 0.852986 seconds, including capture and cleanup. This
closes the retained-log interpretation question. Schema
validation and upstream submission requirements remain separate gates.
