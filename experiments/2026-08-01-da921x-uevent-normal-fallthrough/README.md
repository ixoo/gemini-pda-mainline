# DA921x ordinary kobject uevent fallthrough

| Field | Value |
| --- | --- |
| ID | `2026-08-01-da921x-uevent-normal-fallthrough` |
| Status | `runtime stage 25 passed` |
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
- `scripts/collect-runtime.sh` pins all nine helpers and reconstructs the full
  stage-20-to-25 chain in four explicitly ordered checker phases.

## Follow-up

The selected-boot capture reconstructed stages 21 through 24, then traversed
the ordinary `kobject_uevent_env()` network-broadcast call site and public
return once. The kernel recorded one call-site entry, one call-site return, one
public return, and return zero. The listener received the exact 293-byte,
nine-entry group-1 event with root credentials and no duplicate. The client
remained unbound, CPU0-7 stayed online with CPU8-9 offline, all I2C and oracle
activity remained zero, and serviceability passed. A separate read-only
postcheck confirmed persistent stage 25, exact counters, read-only sysfs, no
predecessor printk, and removal of all nine helpers. No partition read, storage
write, or reboot occurred. Sanitized evidence is in `results/runtime.txt`.

Do not repeat this artifact unchanged. The next Gate 3 experiment must move
the same event into its natural `device_add()` context while retaining an
independent, decision-changing observation path. That boundary remains
separate from driver bind, regulator-provider behavior, and A72 power. Visual
white/grey-screen or reboot behavior alone remains inconclusive.
