# CPU8 one-boot admission-candidate design

## Hypothesis

On the exact Gemini baseline with CPUs 0-7 online and CPUs 8-9 possible,
present, and offline, the source-derived controller can consume one admission,
publish P17/P18, and synchronously request CPU8. The existing binder will
either bring CPU8 online or leave a last-complete retained transition stage
before the recovery watchdog resets the device. CPU9 is never requested.

## Candidate graph

The candidate inherits the serviceable base Gemini DT directly. It enables
the platform-state, DVFSP clock, and BigiDVFS suppliers; one default-off binder;
and one admission controller. It deliberately does not inherit or instantiate
the older standalone physical-source observer. The controller registers the
same source implementation for the exact lifetime of its one transaction, so
a second observer would create an unrelated capture and ambiguous evidence.

`CONFIG_NR_CPUS=10` and the established `maxcpus=8` baseline leave CPU8's CPU
device possible and present but offline. Linux `add_cpu(8)` calls
`device_online(get_cpu_device(8))`, which is the correct hot-add path for this
state; it does not require CPU8 to be absent.

## One-boot evidence contract

Before boot, candidate construction must prove the exact package, config,
Image, candidate DTB, initramfs, Android boot-v0 layout, padded boot2 size, and
all LK-container gates. Runtime prerequisites are the previously serviceable
Gemini topology (0-7 online, 8-9 offline) and stable power.

The single physical boot has three decision-changing outcomes:

1. CPU8 is online and the controller reports one consumed request: preserve
   runtime topology, release, boot ID, controller terminal line, and transition
   ledger as success evidence.
2. The recovery watchdog resets the device: recover the newest valid retained
   transition record. Its phase/stage/terminal class selects the next binder or
   executor repair.
3. The controller refuses before consumption: preserve its prerequisite error
   and make no second boot until the missing supplier/token is repaired.

Screen color and reboot timing are supporting observations only. They do not
classify kernel behavior without the independent controller or retained record.

## Safety boundary

This definition performs no device action and is not a boot candidate. Later
installation remains limited to the live-GPT-resolved inactive, unmounted
logical `boot2`, with exact-size padding, full-partition readback, and clean
shutdown after a verified write. No fresh filesystem or partition backup is
required. Primary boot, boot3, preloader, NVRAM, GPT, and whole-device writes
remain excluded.
