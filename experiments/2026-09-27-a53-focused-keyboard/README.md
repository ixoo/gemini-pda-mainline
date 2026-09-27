# A53 focused keyboard reader candidate

The first A53 keyboard-method trial reached an authenticated mainline boot but
the embedded `keyboard-observe` refused `--diagnose` before any key prompt.
The separately validated focused reader already supports that mode and has
been exercised on the PDA in a previous keyboard experiment. This candidate
replaces **only** that reader in the previously validated A53 service RAM
image. It retains the kernel, DTB, init script, console map, authentication,
logger and recovery path.

Run `build-candidate.py` with the exact private A53 candidate, the fetched
Buildbox focused-reader package identified by SHA-256
`477db0d31c2d2a5d9830022e7dc63288a4e8cd48717aa3cee9b25d4043cc1927`,
and `artifacts/a53-focused-keyboard` as the output root. The script validates
every parent candidate member and package inventory, the static AArch64 reader,
the single initramfs-member delta, LK container and full boot2 padding. The
result remains private and is not yet an admitted boot2 image.

For a later device trial, the hypothesis is that the exact A53 image will pass
the same CPU0–7, console, USB and complete-log checks while the focused reader
actually enters its two physical-key windows. The unique observation is a
verified changed mainline boot, the `--diagnose` header and one owner key
challenge with raw evdev and console bytes; this separates a method failure
from a keyboard translation failure. A reader refusal or console-exclusion
failure stops before input; missing USB or boot identity is inconclusive;
successful capture still needs repeat-aware analysis, complete log preservation
and changed-boot Gemian return before the method can be accepted. A new guarded
installer/session binding and finite budget are required before deployment.
No unchanged-image repeat or ten-cold-boot cycle is authorized by this
offline candidate.

## Offline composition result

The recipe at clean pushed commit `0f24d026` produced a private candidate with
boot SHA-256 `ea8adc12…18adac2` and exact 16 MiB boot2 SHA-256
`34b56a58…780020`. The [sanitized receipt](results/candidate.json) pins the
complete identities. An independent archive comparison found 47 matching
member names with only `bin/keyboard-observe` changed; that member retained
its mode. The kernel, Gemini DTB and config are byte-identical to the A53
parent, the LK container validated, and the full-partition padding and file
inventory rechecked. No device write, boot or keyboard action occurred.

The [session binding](session.py) verifies every private candidate file and
initramfs member against the parent. The [installer](installer.py) derives the
reviewed boot2 guard, binds it to this image and a single preceding Gemian boot,
requires a full-partition readback, then requests a clean poweroff. The
[host session](host-session.py) allows one changed-boot USB observation, a
55-second keyboard phase, complete RAM-log preservation and the reviewed
changed-boot Gemian return. A keyboard-method failure after authenticated
observation still proceeds to log export and return. The two input windows ask
for **1 alone**, then **left Shift + Fn + 1 followed by A with no modifiers**;
release all keys between presses. Each lasts 15 seconds after a two-second
no-input preflight. The owner must physically select boot2 only after the host
collector is armed. No ten-cold-boot cycle is included in this trial.

## Device deployment

The [sanitized deployment result](results/deployment.json) records a guarded
boot2 write from the identified Gemian boot, matching full-partition readback,
and clean shutdown. The one armed 600-second USB collector expired without a
new route or owner boot2 selection. No mainline boot or keyboard observation
was made. A future trial requires a newly armed collector before physical
selection; the installed image does not need another write unless boot2 changes.

## Physical observation

The owner selected boot2 with a fresh collector armed. The
[sanitized runtime result](results/runtime-1.json) records a changed mainline
boot, successful reader preflight, two complete 15-second input windows,
restored console, complete sealed log and changed-ID Gemian return. Both
windows contained zero input events and zero console bytes. The owner had not
been explicitly given the key sequence before selection, so the empty capture
does not establish a keyboard failure or a keyboard pass. The focused reader
method reached the windows, but the physical-key question remains unanswered.
This finite session is closed; no repeat is selected while Wi-Fi is the
development priority.
