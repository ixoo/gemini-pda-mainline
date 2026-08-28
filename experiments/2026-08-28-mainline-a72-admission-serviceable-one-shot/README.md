# Experiment: one-shot CPU8 admission on the serviceable live boot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-28-mainline-a72-admission-serviceable-one-shot` |
| Status | `offline gates pass; exact same-boot action pending` |
| Subsystem | MT6797 A72 admission controller and CPU hotplug |
| Device variant | Planet Computers Gemini PDA, named project device |
| Date(s) | 2026-08-28 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 7, first attributable CPU8 request |

## Question or hypothesis

On the exact serviceability-passed boot, does the already hardware-free-proven
one-shot admission transaction bring CPU8 online, return an attributable
terminal error before/after its sole request, or reset exactly after the
durable trigger boundary?

This follow-up changes no kernel, DT, ramdisk, LK container, or device
partition. It binds the action to installed candidate `f4cb1b2c...`, mainline
boot ID `21bb6547...`, and the exact armed state already captured and published
by the predecessor experiment.

## Provenance and environment

- Published serviceability proof: commit `894e4d5b`, exact release
  `7.1.3-gemini-a72-admission-live`, restored DT `1478f2c8...`.
- Exact installed boot2 image: `f4cb1b2c...`; CPU0--7 online and CPU8--9
  offline before the action.
- The production live-trigger implementation and the one-shot remote action
  source are unchanged from the Buildbox/KUnit-proven predecessor. Its exact
  action script remains `93e6ee4b...`.
- No kernel build is needed or performed; no native VM build is used.
- The owner observes no visibly working console framebuffer on this boot.
  That is a contextual display limitation, not a boot-failure oracle: the
  exact USB/netcat path is live and is the only control path used here.

## Safety assessment

Before any write, the host must re-capture and validate the exact candidate,
release, boot ID, USB interface, controller binding, CPU0--7/CPU8--9 state, and
`armed` zero-execution status. The accepted frame and trigger intent are
fsynced before the sole trigger connection opens.

The exact token is atomically one-shot. The kernel can execute the admission
core once and issue at most one CPU8 request. CPU9, CPU_OFF, retry, storage,
partition, firmware, watchdog-reset, and reboot paths remain absent. The host
never retries after a commit-bearing response or transport loss. On a returning
path it restores virtual sysfs read-only before reading terminal state.

The three accepted results are: CPU8 online with exact terminal success,
terminal admission error with CPU8 still offline, or post-commit transport
loss. All other transcripts fail classification. Retained records are
corroborating only.

## Associated code

- `scripts/remote-pretrigger.sh`: read-only exact live frame.
- `scripts/validate-pretrigger.py`: source-pinned candidate and boot-ID gate.
- `scripts/remote-trigger.sh`: byte-exact proven one-shot action.
- `scripts/classify-attempt.py`: source-pinned three-branch classifier.
- `scripts/test-runtime.py`: 13 unsafe runtime mutations plus three positive
  branches.
- `scripts/run-one-shot.sh`: source-pinned durable collector, with the
  sandbox-safe route fallback and one fixed private output path.

Private transcripts remain below ignored `artifacts/runtime-captures/`.

## Procedure

1. Revalidate all source hashes, shell/Python syntax, ShellCheck, the exact
   published pre-trigger capture, and all runtime mutations.
2. Materialize the collector twice and require exact hash `f7b77371...`.
3. Publish this definition before the device action.
4. On the still-running boot, re-capture exact armed state and fsync it plus
   the trigger intent.
5. Send exact token `run-a72-admission-20260828-a` in one netcat session.
6. Accept one terminal frame or one commit-bearing transport loss; never retry.
7. Publish sanitized evidence and select the next source action from the exact
   terminal result.

## Observations

The predecessor accepted the exact armed frame at 28 seconds uptime: one
controller bound, CPU0--7 online, CPU8--9 offline, sysfs read-only, and every
trigger, supplier, core, CPU, CPU_OFF, and retry counter zero. The mainline boot
remains available on exact USB/netcat. The owner reports no visibly working
console framebuffer.

Offline derivation preserves the exact action script and all three previously
proven terminal branches. Seven pre-trigger and six terminal mutations fail
closed. The validator additionally rejects any boot ID other than the already
qualified live boot. The collector's routing check now falls back to the exact
`10.15.19/24` netstat entry when the sandbox denies the macOS routing socket.

## Analysis

This is the first attempt that can test the CPU8 transaction without conflating
it with boot or observation-channel serviceability. Reusing the same proven
boot also removes another boot-selection variable. The missing visible console
does not weaken attribution because the action, commit marker, terminal state,
and CPU lists all use the already qualified direct USB link.

## Conclusion

The definition and offline gates pass. The one-shot device action remains
pending publication of this exact contract.

## Follow-up

If CPU8 reaches `0-8`, validate a bounded coherency/accounting check before any
CPU9 work. If the controller returns a terminal error, use its exact return and
consumption/request counters to isolate the failed admission stage. If the
commit is observed and transport is lost, perform changed-ID Gemian recovery
without retry and treat the trigger boundary as the primary evidence.
