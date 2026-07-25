# Experiment: Gemini console keymap

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-20-keyboard-console-map-diagnostic` |
| Candidate | AA r0 (superseded) / AA r1 (current) |
| Status | AA r0 is preserved as superseded history; AA r1 passed one attended boot with the new keymap working, exact runtime gate evidence retained, and typed watchdog reboot successful; F1–F10 and Page Up/Page Down remain unconfirmed because the console supplied no visible discriminator |
| Subsystem | Linux VT console map over the proven AW9523 matrix input path |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-20 to 2026-07-21 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

Candidate AA r1 is a console-map-only runtime gate. It keeps Candidate Z's exact
kernel field, final DTB, resolved configuration, AW9523/matrix path, font,
interactive reboot dispatch, and typed-only watchdog recovery. It changes
three inherited initramfs members and adds a deterministic BusyBox binary
keymap plus static AArch64 Unicode-mode and `KDGKBENT` verification helpers.

The previously built AA r0 image was installed and fully read back from
live-GPT-resolved logical `boot2`, but it was superseded before selection: its
map omitted the documented Shift+Fn F1–F10 layer and its `dumpkmap` byte
comparison could not be a valid runtime oracle. The guarded AA r1 installation
has now replaced that exact r0 predecessor on `boot2`; r0 remains preserved as
historical build, backup, and write evidence. AA r1 has now passed one attended
runtime attempt: the owner reported that the new keymap worked and the system
was otherwise fine, while retained console-ramoops independently identifies
the exact image and successful map gate. F1–F10 and Page Up/Page Down remain
unconfirmed because the diagnostic console offered no visible discriminator.

## Question or hypothesis

Can the exact Candidate Z keyboard path expose the photographed US printable
and navigation legends on the Linux text console when tty1 is explicitly put
in Unicode mode and a deterministic VT map is loaded?

The unique evidence is more than marker text. The normal `GEMINI-AA-R1#` shell
is withheld until the map checksum is exact, `KDSKBMODE(K_UNICODE)` succeeds,
and `KDGKBMODE` reads back `K_UNICODE`. The gate then accepts one of two exact
states:

1. On a shell respawn, the already-loaded map passes complete `KDGKBENT`
   verification and is not loaded again.
2. On first entry, the seven inherited source tables are present and every
   other table is absent; BusyBox `loadkmap` then loads the pinned 2,311-byte
   eight-table map at SHA-256
   `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`,
   and complete verification passes afterward.

Complete verification reads all 2,048 kernel entries for the eight planned
tables: the 1,024 payload entries must be exact, every untouched upper-half
entry must be `K_HOLE`, table 3 must gain the kernel's allocation sentinel
after loading, and every undeclared table must remain absent.

Any failure exposes only `GEMINI-AA-R1-KEYMAP-FAIL#`, identifies the failed
stage, and retains Candidate Z's typed watchdog recovery. The unique normal
marker is `GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1`.

## Photographed layout and scope

The user-supplied US-keyboard photograph was inspected locally and is not
stored in Git:

```text
source:     /Users/julien/Downloads/IMG_2392.heic
HEIC SHA:   bc1b8bd28aec4ff46598de1ff9314c92c7dc61d5b1013b98a93e0ef4edce9cf9
local PNG:  /private/tmp/gemini-keyboard-IMG_2392.png
PNG SHA:    864e9486fe0ab16db868f6de23cb95befaaf8d635d185151ea3b2813e870ded1
```

The photo is direct evidence for printed legends, not for electrical contacts
or emitted keycodes. Candidate AA retains the already hardware-proven DT map:
52 assigned AW9523 matrix positions matching the working 3.18 map, with the
four vendor `KEY_UNKNOWN` positions still omitted. The physical Fn key remains
ordinary `KEY_LEFTMETA` at the input boundary; the VT map interprets keycode
125 as `K_ALTGR`, matching the userspace Level3-modifier model without adding a
Gemini-specific kernel input ABI.

A separate authenticated read-only inspection of the known-good Gemian XKB
file `/usr/share/X11/xkb/symbols/planet_vndr/gemini` recorded SHA-256
`56baafdde43da9e3d66474f231a9bfd9d8d9fda40cd4c4af939ae1251db426cb`.
It maps `<LWIN>`/`KEY_LEFTMETA` to `ISO_Level3_Shift`/Mod5 and keeps printable,
navigation, media, brightness, application, and fourth-level F1–F10 policy in
userspace. The file was not copied into the repository. This corroborates the
Fn modifier and subsystem boundary; it does not prove Candidate AA runtime.
See the historical r0 [layout-reference
record](results/layout-reference-20260720.txt) and the current r1 [layout
reference](results/layout-reference-aa-r1-20260721.txt).

The console policy covers:

- the normal Linux letters, digits, Tab, both Shift keys, Ctrl, Alt, Space,
  Enter, Backspace/Delete, and arrows inherited from the pinned default map;
- the photographed shifted digit punctuation;
- plain/Shift `\\|`, `,/`, and `.?`, including reinterpretation of the
  proven physical backslash key's retained `KEY_APOSTROPHE` code;
- Fn number-row `~`, backtick, `£`, `€`, `<`, `>`, `[`, `]`, `{`, and `}`;
- Fn `+`, `-`, `=`, `_`, `;`, double quote, `:`, and apostrophe;
- Fn+period as U+263A WHITE SMILING FACE;
- Fn+Tab as Caps Lock and Fn+arrows as Home, Page Up, Page Down, and End;
- Shift+Fn with digits 1 through 0 as F1 through F10, matching the captured
  known-good Gemian fourth-level policy.

Media, brightness, airplane-mode, voice-assistant, application-launch, phone,
and power legends are userspace actions or separate input paths, not printable
VT keysyms. Candidate AA does not guess those functions into the AW9523 map.
Esc retains the standard VT mapping. On/Off and the phone keys need separate
attributable input evidence if they are to be claimed.

## Provenance and environment

- Kernel release: `7.1.3-gemini-observability-L`, byte-exact Candidate Z
  kernel field.
- Source package profile:
  `observability-fbcon-rotation-keyboard-wrrd-manual-reboot`.
- Patchset SHA-256:
  `4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4`.
- Resolved configuration SHA-256:
  `0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74`.
- Candidate Z artifact-manifest SHA-256:
  `534484e5362e1e4c73ec8438bd36656b444e88199dbd17724a160c75403dbaaa`.
- Candidate Z raw-image SHA-256:
  `985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9`.
- Pinned Linux v7.1 `drivers/tty/vt/defkeymap.c_shipped` SHA-256:
  `318f48316e6bed5ada064879535ec2bca470dc1a8b8c9abd1d92da81bb2c6c7c`.
- Compiler recorded by the inherited package: GCC 13.3.0; the static helper
  was also built with Ubuntu GCC 13.3.0 on Linux AArch64.
- Intended boot path: retained Planet LK, manually selected logical `boot2`.
  AA r1 was manually selected and booted once, then its typed watchdog reboot
  returned the device to Gemian.

Candidate AA does not import a third-party keyboard implementation. The map is
generated from the checksum-pinned Linux default VT map and the repository's
already-normalized keycodes, with the photograph used only to select console
legends.

## Safety assessment

AA r1's generation, canonical helper calibration, two reproducible builds,
and artifact validation were hardware-inert.
The initramfs performs no storage or runtime-network configuration. No
automatic path opens `/dev/watchdog0` or requests reset; only an owner-typed
`reboot` retains Candidate Z's exact guarded one-ping watchdog recovery.

The historical AA r0 guarded installation followed the repository's standing
`boot2` policy: it resolved the logical label from the live GPT, rejected
in-use and unsafe states, preserved a private full backup, padded to the exact
partition size, wrote only resolved `boot2`, flushed, and required matching
remote and local full readbacks. It did not reboot or select a slot. Primary
`boot`, `boot3`, preloader, NVRAM, GPT, and whole-device writes remained
untouched.

The calibrated AA r1 installer required the exact full-partition AA r0
predecessor checksum, preserved another private mode-0600 backup, and repeated
all of the same safety, flush, and full-readback gates without rebooting. It
resolved active root as `/dev/mmcblk0p29` and logical `boot2` as
`/dev/mmcblk0p30`, confirmed the exact power gate, wrote only that resolved
partition, and required the full 16 MiB readback to equal the candidate's
padded checksum. The device boot ID remained
`753bf760-02aa-4731-a797-c73e88dfb414`; no slot was selected and no reboot was
requested.

## Associated code

- `scripts/generate-console-keymap.py` parses only the pinned Linux default map
  and emits the target little-endian BusyBox `bkeymap` format.
- `scripts/validate-console-keymap.py` requires the exact seven inherited
  tables plus new Shift+Fn table 3 and the exact 53-entry semantic delta,
  including Pound, Euro, smiley, F1–F10, modifier-release, and backslash
  modifier semantics.
- `scripts/test-console-keymap.py` checks two deterministic generations,
  fail-closed source/output behavior, and 16 focused map mutations.
- `src/console-unicode-mode.c` sets and reads back tty1 `K_UNICODE` mode and
  selects UTF-8 output.
- `src/console-keymap-verify.c` parses the exact `bkeymap`, verifies the
  pre-load table policy, and checks the loaded map through `KDGKBENT` before
  the normal shell is exposed.
- `scripts/build-initramfs.sh`, `validate-initramfs.py`,
  `build-boot-from-z.py`, `validate-boot.py`, and
  `validate-final-artifact.py` construct and validate the exact-Z derivative.
- `scripts/build-keyboard-console-map-candidate.sh` is the hardware-inert
  Linux-AArch64 build entry point.
- `scripts/test-validator-mutations.py` exercises focused artifact/component
  corruption cases, including verifier inventory and identity.
- `scripts/derive-installer.py` preserves the historical r0 derivation;
  `scripts/derive-revision-installer.py` and
  `install-candidate-aa-boot2.sh` form the fail-closed r1 guarded installer.

The following exact build, installer, and write records describe historical AA
r0 and must not be presented as AA r1 evidence:

[build-validation-20260720.txt](results/build-validation-20260720.txt). See also
the [layout reference](results/layout-reference-20260720.txt), [installer
validation](results/installer-validation-20260720.txt), and [guarded
write/readback](results/boot2-write-candidate-aa-20260720.txt). Their checksums
are pinned in [results/SHA256SUMS](results/SHA256SUMS).

Current AA r1 evidence is recorded separately in [build
validation](results/build-validation-aa-r1-20260721.txt), [installer
validation](results/installer-validation-aa-r1-20260721.txt), [guarded
write/readback](results/boot2-write-candidate-aa-r1-20260721.txt), and the
[layout reference](results/layout-reference-aa-r1-20260721.txt). The first
attended boot and retained console-ramoops are recorded in the [runtime
result](results/runtime-candidate-aa-r1-attempt-1-20260721.txt).

## Procedure

AA r1 uses this gated sequence:

1. Validate the exact Candidate Z artifact and checksum-pinned Linux default
   keymap source inside the AArch64 recovery development VM.
2. Generate the 2,311-byte eight-table map twice. Require byte identity, the
   exact 53-entry semantic delta, all pinned source entries 128–255 to be
   `K_HOLE`, and rejection of all 16 focused map mutations.
3. Build both static AArch64 helpers twice with the pinned compiler and flags;
   require byte identity, no interpreter, expected ELF machine, and calibrated
   hashes. Exercise the verifier's parser and 11 rejection cases.
4. Replace only `/init`, `/bin/local-shell`, and `/bin/x-record`; add only
   `/bin/console-keymap-verify`, `/bin/console-unicode-mode`, and
   `/etc/gemini-us.bkeymap`; preserve every other Candidate Z member.
5. Rebuild the Android-v0 image while requiring Candidate Z's exact kernel
   field, `Image.gz`, final DTB, configuration provenance, LK addresses, name,
   and command line. Build twice, require recursive equality, rerun every
   component and 32 LK gates, and reject focused mutations.
6. Calibrate the r1 installer from the exact r0 installer foundation. Require
   exact installed r0 as predecessor, repeat the live-GPT/root/in-use/power/
   boot-ID checks, preserve a full private backup, perform one bounded `boot2`
   write, flush, and require complete matching readback. Do not reboot.

Steps 1–6 pass. The recovery VM produced the canonical static verifier at
SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.
Two clean candidate constructions were recursively identical, the complete
artifact and mutation validation suite passed, the final package was exported,
and the calibrated installer replaced only exact AA r0 on logical `boot2` with
matching full-partition readback. The attended runtime sequence below was then
performed once.

The attended runtime attempt kept the kernel restart change out of scope and
used this decision-changing sequence:

1. Manually select logical `boot2` and require either normal
   `GEMINI-AA-R1#` or explicit `GEMINI-AA-R1-KEYMAP-FAIL#`. A missing prompt or
   boot/display/input regression rejects AA r1.
2. At the normal prompt, exercise all photographed printable groups:

   ```text
   1234567890
   !@#$%^&*()
   ~`£€<>[]{}
   \|:
   ,/.?☺
   +-=_;"'
   ```

3. Test Fn+Tab Caps Lock, Fn+Up Page Up, Fn+Down Page Down, Fn+Left Home,
   Fn+Right End, and Shift+Fn+1 through Shift+Fn+0 as F1 through F10. Exercise
   Tab, both Shift keys, Ctrl, Alt, and each modifier-release ordering.
4. Leave the shell idle beyond 45 seconds to ensure there is no automatic
   watchdog owner. Then use the inherited typed watchdog recovery once. The
   separate kernel-native reboot experiment remains out of scope for this boot.

The exact normal prompt, retained runtime gate, and owner's successful keymap
exercise permit preserving AA r1's console policy for the later reboot
candidate. F1–F10 and Page Up/Page Down require a future test with a visible
discriminator before those individual functions can be claimed. No recovery
prompt, boot, console, provider, or matrix regression was observed.

## Observations

### Historical AA r0

AA r0 built twice, validated, and was written/read back exactly, but was
superseded before boot. Its immutable identities remain historical evidence:

```text
artifact:          candidate-AA-keyboard-console-map-final-a2ad7a41
artifact manifest: e67fcd4aaaf9f192ebb36291f9065a62848818af4241ab97c67459513d0d7c32
boot SHA-256:      a2ad7a4107abd99cbd349b8f2deadd0185cbdd5bb0884ecbdae8ff2a7499ed4c
boot size:         7,120,896 bytes
initramfs SHA-256: fe1db038fead9d9675048f49bae89f713d1fe161f1bee5323cbabfa76dfa4ef2
keymap SHA-256:    48f1f61a9ad8ba327a3105c0dfbbc698c1e55bb3bcca695b46887888be8ca821
16 MiB padded SHA: 157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa
```

Before the r1 write, the device partition still matched that exact padded r0
identity. The r1 installer preserved it in the private mode-0600 directory
`artifacts/device-partitions/pre-candidate-aa-r1-20260721T100921Z` before
replacing it. No r0 selection or reboot occurred. Its successful build and
write prove only historical artifact and stored-byte identity; they do not
validate its incomplete map or invalid `dumpkmap` byte-comparison oracle.

### Current AA r1

The photographed/XKB-derived r1 map is deterministic at SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
Tests pass two generations, two generator rejections, 16/16 semantic
mutations, exact Unicode encodings, Shift+Fn closure, modifier-release policy,
and backslash Ctrl/Alt semantics. The verifier source is SHA-256
`70d70bcef6e403d850c32b85f4bab928b2eb1444fae68ec3f629d7ff7c22785d`;
the canonical Ubuntu GCC 13.3.0 Linux-AArch64 static verifier is SHA-256
`29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238`.

The final package was built twice with recursive equality, passed the complete
artifact and focused-mutation validation gates, and was exported as:

```text
artifact:          candidate-AA-keyboard-console-map-final-37e82bf3
artifact manifest: 2a291c5e8f20442140ce025028af578272a06f41c53498baec728ba61c49c343
boot SHA-256:      37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7
boot size:         7,378,944 bytes
initramfs SHA-256: 4218be56af7b844f8b572f57e49ddeb106d48331bd34c61bec58afb7215c2aa7
16 MiB padded SHA: 38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703
```

The calibrated wrapper is SHA-256
`94b26c3410dd06254b91505833cd26bb87cefb102df5b03e296370e5054f414c`
and its derived installer is SHA-256
`f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f`.
Against active root `/dev/mmcblk0p29`, the live GPT resolved logical `boot2` as
`/dev/mmcblk0p30`. The installer required predecessor SHA-256
`157c7cd5d814d7b2704d679faacd3215c5e889642b4261441f99653957585eaa`,
preserved its full backup, and wrote/read back r1 at exact full-partition
SHA-256
`38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703`.
The installation evidence manifest is SHA-256
`8c07a62ccb92e5555017ca518db1d147c1441472b9bd8ff632846ec7cc02908e`.
Power remained exact at AC online, battery status `Full`, capacity 100%, and
health `Good`; the boot ID remained
`753bf760-02aa-4731-a797-c73e88dfb414`, and no reboot occurred. Thus `boot2`
contained exact AA r1 and was ready for the attended test described below.

### AA r1 attended attempt 1

The owner manually selected AA r1 and reported that it booted, the new keymap
worked, the system was otherwise fine, and the typed `reboot` worked. The
console offered no visible discriminator for F1–F10 or Page Up/Page Down, so
those individual mappings remain unconfirmed rather than failed.

Retained console-ramoops supplies an independent attributable record. It
contains the exact marker `GEMINI_KEYBOARD_CONSOLE_MAP_20260720_AA_R1`, records
`origin=loaded-now` at 2.407618 seconds, and identifies map SHA-256
`02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
The gate recorded `K_UNICODE`, all 2,048 planned entries exact, every upper
half `K_HOLE`, every undeclared table absent, and table 3 allocated. It then
exposed `GEMINI-AA-R1#` and recorded successful interactive dispatch
validation.

The bare `reboot` request arrived at 126.258967 seconds, proving more than 123
seconds of runtime without an automatic watchdog reset. The inherited recovery
then opened `/dev/watchdog0` on fd 3, issued its exact single ping with timeout
31, and printed the expected countdown values from 5 through 30 seconds before
reset. After return to Gemian, the boot ID had changed; the collected reasons
were `boot_reason=4`, `androidboot.bootreason=wdt_by_pass_pwk`, and
`powerup_reason=reboot`.

The private capture is
`artifacts/device-pstore/candidate-aa-r1-attempt-1-post-return-20260721T101944Z`
with evidence-manifest SHA-256
`d18eff262b66af21ee5cd61b05fd2f25b8b107187564774001f09ae3d9765a6a`.
Collection did not remove the remote pstore records. The collection itself
performed no partition access and requested no reboot.

## Analysis

Exact Candidate Z kernel/DT/config identity keeps the hardware-proven keyboard
provider and matrix path fixed. The six-member initramfs delta isolates the
next boot's decision to VT map loading and interpretation. Verified Unicode
mode prevents Pound, Euro, or smiley code points from being transformed twice.
The preflight rejects unexpected pre-existing maps; post-load `KDGKBENT`
verification checks all 2,048 entries of the eight planned kernel tables,
including `K_HOLE` across every upper half, and rejects any undeclared table.
A successful `loadkmap` exit alone cannot expose the normal prompt.

Because VT maps survive an interactive shell exit, a respawn first attempts
the same complete `KDGKBENT` verification. An exact already-loaded map returns
to the normal prompt without reloading. An untouched or source-table-only
state falls through to preflight, is overwritten, and must pass exact readback.
An unexpected allocated table fails preflight; any state that cannot be made
exact receives only the recovery prompt.

Undefined modifier-combination tables deliberately fail closed. Linux updates
`key_down` before map lookup and recomputes modifier state from the plain table
when a selected table is absent, so Ctrl/Fn/Shift/Alt release order does not
leave a stuck modifier. Every present table also preserves each physical
modifier entry.

Canonical builds, validation, export, exact full-partition readback, and the
retained runtime gate prove the intended map was deterministically loaded in
Unicode mode on the selected hardware. The owner's test provides one positive
hardware result for the new console map and no observed keyboard regression.
It does not distinguish F1–F10 or Page Up/Page Down, so those keys remain
explicitly unconfirmed. Media, brightness, phone, airplane, launcher, voice,
and Sym are userspace actions and remain outside this VT-map claim.

## Conclusion

`r0-superseded-preserved; r1-pass-once-with-unconfirmed-keys`: exact AA r1
booted once, exposed its fully verified Unicode keymap and normal prompt, and
the owner reported the new keymap working with the system otherwise fine.
F1–F10 and Page Up/Page Down remain unconfirmed only because the console had
no visible discriminator. More than 123 seconds without an automatic watchdog
reset and the successful typed watchdog reboot also validate the inherited
recovery dispatch. This result unlocks assembly of the separate AB
kernel-native-restart candidate while preserving AA r1's tested console map.

## Follow-up

Assemble and validate the separate AB kernel-priority reboot candidate while
preserving exact AA r1 console-map policy. Its attended test should isolate the
kernel-native restart change. Confirm F1–F10 and Page Up/Page Down later with a
console program or escape-sequence capture that supplies a visible
discriminator; do not promote those mappings from structural verification to
manual hardware confirmation yet.
