# Experiment: time fbcon loss during active refresh and static hold

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-16-fbcon-refresh-timing-diagnostic` |
| Candidate | I |
| Status | Built reproducibly, exported, and synchronized to logical `boot2`; runtime observation pending |
| Subsystem | LK display handoff, simplefb, framebuffer console, initramfs timing |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-16 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

While preserving Candidate H's kernel, DTB and boot container contract exactly,
does one tty0 update per second keep the visible console alive, and does the
display transition to black only after those updates stop?

Candidate I is an initramfs-only timing diagnostic. Its `/init` emits a unique
Candidate I marker as part of one short tty0 counter line per second from
`T+01` through `T+60`, emits one final static-hold line, and then remains alive
without further deliberate console writes. The sequence is intended to:

1. identify a confirmed Candidate I/`boot2` selection;
2. measure the black transition against a visible counter rather than an
   estimated boot duration; and
3. compare an actively updated console with the immediately following static
   hold in one boot.

This experiment does not claim that tty writes should be necessary for correct
display retention. It uses them only as a bounded timing and activity
discriminator.

## Prior observation and clock-cleanup boundary

In one owner-attended Candidate H series, two attempts visibly progressed
farther than Candidate G before the screen became black and the backlight went
off. Later attempts did not reproduce that visible progress. On a visible
attempt, the owner recalled a line approximately as `GEMINI FBCON TEST`.
Candidate H has a distinctive marker emitted only by tracked initramfs `/init`,
so the recalled content strongly supports `/init` execution, although the lack
of a photograph or exact transcription leaves a small attribution uncertainty.

The external initramfs `/init` runs after the kernel initcall sequence. In this
kernel, unused-clock cleanup is a late initcall. Therefore, if the visible line
was H's unique `/init` marker, `clk_disable_unused` had already run before that
line was drawn. The later black transition cannot then be explained simply as
"the first unused-clock sweep happened after the marker." This is an inference
from Linux initialization order plus the content attribution, not a measured
clock trace.

For that reason Candidate I keeps Candidate H's clock description unchanged
and defers the broad `clk_ignore_unused` diagnostic. That command-line option
would retain every otherwise-unused clock and would make the next result much
less specific. It remains available only if a later experiment produces
evidence that clock cleanup timing is still the best discriminator.

## Provenance and comparison boundary

Candidate I mechanically reconstructs and hash-pins the exact validated
Candidate H artifact. The following remain byte-for-byte identical:

- `Image.gz` and appended Candidate H DTB kernel segment;
- Candidate H simplefb node, including `CLK_INFRA_DISP_PWM` and
  `CLK_TOP_MUX_MM` references;
- Android boot-image version, addresses, page layout, forced command line and
  LK-compatible container boundaries.

The reconstructed initramfs archive has the same path, type, mode and link
manifest as exact H; `/init` is its only differing regular file. In the Android
v0 container, only `ramdisk_size` and the canonical ID derived from the changed
ramdisk differ. The validator requires that complete archive and boot-container
delta before emitting an artifact.

The bsg100 Gemini effort is useful comparative evidence for LK handoff and
eventual native display ownership, but it used a different Android-plus-Kali
software history and partition layout. Candidate I neither imports its code nor
assumes its timing, clock state or hardware-visible behavior transfers to this
unit. Similarities and differences remain evidence to test, not facts about the
current device.

## Implemented initramfs behavior

The tracked `/init` waits one second before the first line and then emits these
exact line forms to `/dev/tty0` and, when present, `/dev/ttyS0`:

```text
GEMINI_FBCON_REFRESH_20260716_I T+01 ACTIVE REFRESH 01/60
...
GEMINI_FBCON_REFRESH_20260716_I T+60 ACTIVE REFRESH 60/60
GEMINI_FBCON_REFRESH_20260716_I T+60 STATIC HOLD; NO FURTHER CONSOLE WRITES
```

Each numbered line follows its one-second delay; the implementation does not
overwrite a single line with a carriage return. After the static-hold line,
`/init` sleeps indefinitely and makes no further deliberate console writes.
There is no separate immediate marker before `T+01`, so the first Candidate I
attribution is expected about one second after `/init` begins this loop.

Candidate I does not access runtime storage, a framebuffer device, raw memory,
network interfaces, USB gadget state, reboot/poweroff/halt paths, watchdogs or
reset controls. It does not change rotation, panel state, clocks or regulators.
Its only repeated runtime action is a bounded tty write followed by sleep; the
procfs and sysfs mounts are read-only. Dormant USB/network binaries inherited
byte-for-byte from the exact H archive remain present but are never invoked by
Candidate I `/init`.

## Associated code

The tracked inputs are:

- `initramfs/init`: unique marker, `T+01` through `T+60` refresh sequence, then
  a silent static hold;
- `scripts/build-initramfs.sh`: deterministic exact-H initramfs derivative;
- `scripts/validate-initramfs-delta.sh`: allow only the tracked `/init` delta
  and reject storage, network, raw-framebuffer and reset behavior;
- `scripts/validate-boot-delta.py`: require an identical H kernel segment and
  permit only ramdisk-derived Android-v0 header differences; and
- `scripts/build-fbcon-refresh-candidate.sh`: reconstruct exact H, run every
  gate, and emit a complete checksum manifest without selecting or writing a
  device partition.

The validators hash-pin the exact H boot image, DTB, initramfs and `Image.gz`,
and hash-pin Candidate I's tracked `/init`, resulting initramfs and boot image.

## Safety assessment

The build path is file-only and non-flashing. Device synchronization was a
separate operation governed by the repository's standing logical-`boot2`
policy: the live GPT label was resolved, a private full backup was preserved
and checksummed, identity/power/size checks passed, the write was synced and
flushed, and a full-partition readback matched. No reboot was part of the build
or synchronization procedure.

At runtime the candidate only writes characters to tty0 and, when present,
ttyS0, and changes volatile shell state. It does not intentionally write eMMC,
alter firmware, reset the device or program display hardware. Stop testing
under the repository's normal heat, battery, filesystem, watchdog-loop or
recovery-behavior stop conditions.

## Procedure and evidence criteria

1. Candidate I was implemented as the validated initramfs-only delta described
   above.
2. It was built twice into new output directories. Recursive byte equality,
   both checksum manifests, exact-H kernel identity, the allowlisted initramfs
   delta, and all Android-v0/LK container gates passed.
3. One exact validated directory was exported and its manifest rechecked. Its
   candidate was padded to the exact partition size and synchronized only to
   logical `boot2` under the standing safety policy; the complete readback
   matched the padded input byte-for-byte.
4. Perform up to five owner-attended `boot2` selections, or stop after three
   marker-confirmed Candidate I attempts. For every attempt, record whether the
   unique I marker appeared; the first and last readable counter values; screen
   orientation; black-transition counter/time; backlight state; behavior after
   the static marker; final apparent power state; and recovery action.
5. Treat an attempt with no unique I marker as an unconfirmed selection or
   handoff result. Do not use it to time Candidate I's post-`/init` behavior.

Interpretation is deliberately bounded:

- Black during the `T+01`–`T+60` updates shows that continued fbcon activity is
  insufficient to retain the display. Repetition at a similar counter would
  establish a timing pattern, not its cause.
- Visibility through `T+60` followed by black only during the silent hold
  supports an activity-dependent console, panel or bootloader-retained-state
  effect. It does not identify a specific clock or prove native display
  ownership.
- A static marker that remains visible with the backlight on rejects the
  immediate-retention failure for that attempt.
- Intermittent appearance of the unique marker confirms that selection or
  early handoff repeatability is itself a separate problem; it does not make
  unseen attempts equivalent to post-`/init` blackouts.

## Results

Build, export and logical-`boot2` synchronization are complete. Detailed,
sanitized evidence is in:

- `results/candidate-i-build-20260716.txt`; and
- `results/boot2-write-candidate-i-20260716.txt`.

```text
exact Candidate H input:        594a83d4b48ad33688abb3e0c5ffd1914d6027c680d7799322f9379bef8f4b09
Candidate I boot image:         6,520,832 bytes; 92e1a870dad1086f83c777b048d4a684d601a42603157929996769a6ab47a01a
Candidate I initramfs:          1,006,187 bytes; 85059d3128e643deaafc3989c745ed21ec94ec5f24f5002839e0d080d13dfe85
Candidate I full boot2 image:   16,777,216 bytes; d823c5b619f4199ff596a38b3f3aa0cd1f6139fd73f6d4e3ad64c9fd0dd5c0e7
independent build equality:     PASS — two final directories recursively byte-identical
boot2 full-readback match:      PASS — full 16 MiB readback byte-identical to padded candidate
marker-confirmed attempts:      PENDING
black-transition counters:      PENDING
```

The exported files remain under the Git-ignored
`artifacts/vm-export/boot-candidates/gemini-fbcon-refresh-I-final1/` path. The
full padded image, pre-write backup, and post-write readback remain mode `0600`
under the Git-ignored
`artifacts/device-partitions/pre-candidate-i-20260717T034729Z/` path. None of
those private or generated artifacts is tracked. The completed build and write
do not constitute a runtime result.

## Conclusion and follow-up

Current conclusion: `built, exported, and synchronized; runtime pending`.
Logical `boot2` contains the exact validated Candidate I full-partition image,
but no Candidate I boot attempt has yet been recorded.

After marker-confirmed repetitions, select the next experiment from the timing
result. Keep fbcon rotation, native DRM/panel enablement, broad clock retention,
USB networking and storage access out of this A/B so the observed transition
remains attributable.
