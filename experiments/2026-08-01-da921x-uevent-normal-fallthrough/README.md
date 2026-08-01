# DA921x ordinary kobject uevent fallthrough

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-normal-fallthrough` |
| Status | `deployed and powered off; selected-boot runtime pending` |
| Subsystem | I2C, OF, kobject uevent, netlink |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 transport boundary |

## Question or hypothesis

Can the exact runtime-proven stage-24 event leave the experiment branch
through the ordinary `kobject_uevent_env()` network-broadcast call site and
return through the public uevent function exactly once, while producing the
same single exact userspace receipt and preserving the zero-hardware and
serviceability baseline?

Stage 24 proved the original namespace-routing wrapper through an
experiment-local direct call followed by a forced cleanup jump. Stage 25 moves
exactly one boundary outward: it uses the unmodified fallthrough call site and
normal function return. It remains a post-serviceability replay and does not
claim natural `device_add()` context.

## Decision

- One call-site entry and return, one public return, normalized return zero,
  one exact receipt, and no duplicate advances to stage 25.
- A missing or repeated target, nonzero return, counter mismatch, receipt
  mismatch, or baseline change rejects attribution.
- Success permits design of the separate natural `device_add()` boundary; it
  does not establish driver bind, regulator-provider behavior, or A72 power.
- Visual white/grey-screen and reboot behavior alone remains inconclusive.

## Safety and build policy

The experiment emits one intentional uevent multicast only after reconstructing
the proven stage-24 predecessor with checksum-pinned helpers. The matching
DA921x driver remains module-only and absent from the initramfs; the real client
remains unbound. The patch adds no driver, provider, I2C transfer, register
access, printk, usermode helper, or device-storage path.

Build only through `./scripts/build-kernel --backend buildbox` from an exact
clean pushed commit. Do not run a native VM kernel build unless the owner
explicitly requests one. The experiment-only patch has no DCO sign-off and is
not submission-ready.

## Associated code

- Patch `0146` adds the one-shot ordinary-fallthrough observation.
- `scripts/build-listener.sh` source-pins and mechanically derives the static
  stage-25 listener from the runtime-proven listener source.
- `scripts/run-serviceability-check.sh` accepts only the exact stage-24
  predecessor and validates the stage-25 return, receipt, and safety state.

## Follow-up

Select `boot2` once. If USB/netcat becomes serviceable, reconstruct the exact
stage-24 predecessor and run the frozen stage-25 listener once. Visual
white/grey-screen or reboot behavior alone remains inconclusive.
