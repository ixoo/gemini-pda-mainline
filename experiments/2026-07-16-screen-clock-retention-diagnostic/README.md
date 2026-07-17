# Experiment: retain the LK backlight clock through simplefb

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-screen-clock-retention-diagnostic` |
| Status | Completed once; transient sideways fbcon text observed, then black |
| Subsystem | LK display handoff, simplefb, display-PWM clock retention |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Did Candidate E remain visually black because Linux unused-clock cleanup gated
`CLK_INFRA_DISP_PWM` and its `pwm_sel` parent before the initramfs marker was
written?

Candidate F is a strict one-variable derivative of Candidate E. It preserves
the exact `Image.gz`, initramfs, marker, Android-v0 parameters, framebuffer
base, geometry, stride, format and write. Its only semantic DT change is:

```dts
clocks = <&infrasys CLK_INFRA_DISP_PWM>;
```

on `/chosen/framebuffer@7dfb0000`. Linux simplefb holds every listed clock for
the framebuffer driver's lifetime. The MT6797 infra gate's CCF parent is
`pwm_sel`, so enabling the gate retains that parent as well.

## Provenance

The clock choice comes from the focused audit of bsg100 commit
`035d4b0ba386076e5b4c7cbca344f0807ac51f24`, whose hardware history records
unused-clock cleanup extinguishing the loader-retained backlight. The exact
source and local comparison are in
[`fbcon-commit-035d4b0-20260716.md`](../2026-07-13-bsg100-gemini-linux-comparison/results/fbcon-commit-035d4b0-20260716.md).

The build reconstructs Candidate E and refuses to continue unless these exact
baseline hashes match:

```text
boot image: 08845b5c3985a8bcba569d3009889bbfe210f942d1cef23b798f5fff5c2cb253
initramfs:  1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
DTB:        cd41adc3f38b2f94b69ca69a27f61ab2b3ff5dcbcf7094de2f250a341c726389
```

## Safety

The build tools are file-only and contain no device or flashing interface.
Candidate F does not probe or program native DRM, DSI, panel, PWM, regulators
or the display power domain. It only asks simplefb to retain one existing
loader-enabled clock and performs Candidate E's same bounded framebuffer-RAM
write. It contains no storage, reboot or poweroff action.

The packaged base DTB has no `/__symbols__`. The builder therefore resolves
the existing infra provider phandle from `/syscon@10001000`, verifies the exact
compatible and one-cell clock contract, and never hard-codes the numeric
phandle. A semantic validator permits exactly one added `clocks` property and
rejects any other node, property, reservation-map or boot-CPU delta.

Any hardware synchronization is a separate host action under the owner's
standing logical-`boot2` authorization. It must resolve the GPT label live,
preserve a fresh private backup, synchronize and flush the write, and require a
matching full-partition readback. It does not authorize a boot or reboot.

## Associated code

- `scripts/build-clock-retention-dtb.sh` derives the one-property DTB.
- `scripts/validate-simplefb-clock-delta.py` enforces the semantic delta and
  provider contract.
- `scripts/build-clock-retention-candidate.sh` reconstructs exact Candidate E,
  serializes Candidate F, runs the LK/parser/container checks, and writes a
  complete checksum manifest.

## Procedure and positive criterion

1. Build Candidate F twice from the exact Candidate E source package with
   source-date epoch zero.
2. Require both manifests to pass and both output trees to be byte-identical.
3. Export one exact candidate directory to the Git-ignored host artifacts.
4. Under the standing authorization, synchronize it to live logical `boot2`
   only after all preflight, backup, write, flush and readback gates pass.
5. On a later owner-attended boot, success is the same eight broad alternating
   white/dark-gray bands expected from Candidate E. Record backlight state,
   latency, duration, final power state and recovery behavior.

## Runtime observation and interpretation boundary

On one owner-attended `boot2` selection, the owner saw text move right-to-left
across the sideways display for about one second. The screen then became black
and no further visible output was reported. The text was not transcribed or
photographed; backlight state after the transition, final power state and the
recovery action were not reported. None of the expected bands was recognized.
The exact record is
[`results/runtime-candidate-f-20260716.txt`](results/runtime-candidate-f-20260716.txt).

This is the first positive visual runtime signal from the current Linux 7.1.3
handoff. Candidate F enables tty0/fbcon, describes the LK framebuffer through
simplefb and retains `CLK_INFRA_DISP_PWM`; the observation strongly supports
kernel entry plus simplefb/fbcon output and shows that the retained clock was
sufficient for transient visible scanout. The text was not captured or read,
so it is not content-attributed proof of a particular kernel stage or `/init`.

Candidate F's `/init` emits several console lines and then attempts the full
band-image write. The observed text-then-black sequence is temporally
consistent with reaching that path, but it does not prove that `dd` ran or
caused black; the expected bright bands were not recognized and no status
survived. Candidate G removes every raw framebuffer access while retaining the
exact kernel and DTB to test that explanation directly.

The observed text is sufficient to close the earlier all-black ambiguity for
kernel/simplefb/fbcon output, but not the experiment's intended marker proof.
Candidate F remains a loader-framebuffer retention result, not native display
support or proof that every scanout dependency is represented.

## Build and deployment result

Two independent Candidate F builds from the exact package were recursively
byte-identical. Both checksum manifests, the semantic DT allowlist, unchanged
initramfs gate, Android-v0 delta validator and LK parser passed. The exported
boot image is 6,533,120 bytes:

```text
boot image SHA-256: 14c1fe4116cd04331fa347502929ef9e60aed08cbc859b99621a5010e263df57
DTB SHA-256:        edcc5da98996cf594661c5c6da08996a6b2bf59f1e46bcbf6b89e9e9aac56abb
initramfs SHA-256:  1c76b34ea58956ffd8b97a640b76788b9f7e1ab92204a9881ad031bd7fe6c72c
```

The initramfs hash is exactly Candidate E's. The complete static result is
[`results/candidate-f-build-20260716.txt`](results/candidate-f-build-20260716.txt).

Under the owner's standing authorization, the live preflight resolved logical
`boot2` to the unmounted, writable 16 MiB `/dev/mmcblk0p30` while Gemian ran
from `/dev/mmcblk0p29`. AC was online and the battery reported 100%, Full and
Good. A fresh private full backup matched Candidate E. Candidate F was padded
to the exact partition size, staged and checksum-verified, then written with
`fsync`, followed by `sync` and a block-device buffer flush. Both the
device-side checksum and an independently retained complete laptop readback
matched:

```text
full boot2 SHA-256: d8ec6f64df9b28154b5e6dc42fc214e5b5eb981efa9cea84cd14c57b5ec378e2
```

No boot, reboot or shutdown occurred, and no other partition was touched. See
[`results/boot2-write-candidate-f-20260716.txt`](results/boot2-write-candidate-f-20260716.txt).

## Follow-up

The [Candidate G fbcon-text follow-up](../2026-07-16-fbcon-text-diagnostic/README.md)
retains Candidate F's exact kernel segment, DTB and clock reference, replaces
only the initramfs, removes the marker and raw framebuffer access, and holds a
distinctive console banner with a 30-second heartbeat. It is built
reproducibly, synchronized and fully read back from `boot2`. The exact F kernel
does not compile fbcon rotation, so G intentionally remains sideways; rotation
is a separately attributable later kernel-config test.
