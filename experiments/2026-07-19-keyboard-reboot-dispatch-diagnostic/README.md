# Experiment: dispatch-safe typed watchdog reboot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-19-keyboard-reboot-dispatch-diagnostic` |
| Candidate | Z |
| Status | Reproducibly built and validated; one owner-attended boot, keyboard, and typed-watchdog return passed |
| Subsystem | Early-userspace BusyBox command dispatch and MT6797 TOPRGU reset |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-19 to 2026-07-20 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

Candidate Z was reproducibly built, validated, installed on
live-GPT-resolved logical `boot2`, and fully read back. The owner subsequently
selected it once, reported a successful boot with the keyboard still working,
typed its watchdog-backed `reboot` command, and observed the automatic return
to Gemian. A changed post-return boot ID and Gemian's
`androidboot.bootreason=wdt_by_pass_pwk` independently corroborate a
watchdog-class reset. The exact marker, prompt, live dispatch output,
individual keys, and countdown timing were not transcribed or retained. See
the [runtime result](results/runtime-candidate-z-attempt-1-20260720.txt).

## Question or hypothesis

Can exact Candidate Y's kernel, DTB, resolved configuration, keyboard support,
font, and clean tty1 policy be retained while making a typed bare `reboot`
unambiguously enter the external hardware-watchdog wrapper?

Candidate Z is designed to change only command dispatch and the wrapper's
watchdog-open control flow. Its distinguishing evidence is not merely a new
marker. Before exposing the shell, the runtime must execute the exact BusyBox
`type reboot` oracle and obtain:

```text
reboot is an alias for /bin/reboot
```

The final interactive shell must inherit that same exported `ENV` contract.
Typing bare `reboot` must then print the absolute-wrapper entry message before
any watchdog open, complete the exact watchdog/ramoops preflight, open
`/dev/watchdog0` only for the foreground function call, send one handoff ping,
hold the descriptor open without later writes, and display the 31-second
countdown. No `reboot(2)`, MediaTek software-reset write, `sync`, or other
fallback is permitted.

The unique marker is
`GEMINI_KEYBOARD_REBOOT_DISPATCH_20260719_Z`; the prompt is `GEMINI-Z#`.
These names identify the exact built and installed candidate.

## Why Candidate Y was rejected

The decisive [Candidate Y pre-boot command-dispatch
audit](../2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/results/preboot-command-dispatch-audit-20260720.txt)
executed the exact static BusyBox binary from Y. It established this standalone
applet collision:

```text
PATH=/bin
type reboot -> reboot is reboot
bare reboot -> BusyBox internal reboot applet
/bin/reboot -> external watchdog wrapper, but not selected
```

Standalone BusyBox applets precede `PATH` lookup, so Y's displayed bare command
would bypass `/bin/reboot` and could re-enter the generic restart path that
appeared to hang under Candidate X. The same audit found that Y's
`if exec 3>/dev/watchdog0` construct exits its noninteractive ash interpreter
when the open fails; the intended `else` refusal cannot run. Open failure still
does not arm the watchdog, but it loses the promised diagnostic and shell
return.

That is a complete pre-boot rejection. Candidate Y was never selected or
booted and has no runtime evidence. See the closed [Candidate Y experiment
record](../2026-07-19-keyboard-typed-watchdog-reboot-diagnostic/README.md).
Y was never booted and is no longer stored on logical `boot2`.

## Exact Candidate Y basis

The immutable foundation was the final Candidate Y artifact, used only as
build input:

```text
artifact:          candidate-Y-keyboard-typed-watchdog-reboot-final-94edd593
artifact manifest: 310ac503b4bbd8c5a3d5c31bcecb473064d5207ff30ad73111325ffe1a1c56a6
boot SHA-256:      94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee
boot size:         6,866,944 bytes
initramfs SHA-256: 11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2
Image.gz SHA-256:  d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41
final DTB SHA-256: bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
config SHA-256:    0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74
patchset SHA-256:  4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4
BusyBox SHA-256:   52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
```

The validated Z container keeps Y's complete kernel field (`Image.gz` plus
DTB), final DTB file, resolved configuration provenance, Android-v0 addresses,
page size, name, command line, input helper, and every unrelated initramfs
member byte-for-byte. Thus Z is an exact-Y kernel/DT/config derivative; it is
not a new kernel build and makes no new hardware-support claim.

Candidate Z now adds one owner-reported successful boot, keyboard-regression,
and typed-watchdog-return result over that unchanged kernel/DT/config basis.
Candidate W remains the last artifact with retained individual key events and
the exact waits through 30 seconds; see its [runtime
record](../2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

## Validated five-member initramfs delta

Relative to exact Y, the archive has exactly four changed
members and one added member:

| Member | Validated delta |
| --- | --- |
| `/init` | Z marker/profile and explicit `ENV`-alias dispatch policy; still no watchdog access or reboot at boot |
| `/bin/local-shell` | Export immutable `ENV=/bin/reboot-dispatch.env`, run the exact dispatch oracle, withhold the shell on mismatch, then expose `GEMINI-Z#` |
| `/bin/reboot` | Record bare-command attribution and use catchable function-call redirection for watchdog ownership |
| `/bin/x-record` | Use the Z marker while retaining serial/kmsg/ramoops-oriented recording and no virtual-console sink |
| `/bin/reboot-dispatch.env` | New regular root-owned mode-`0444` member containing exactly `alias reboot='/bin/reboot'` |

All four changed inherited members are regular root-owned mode-`0755` files
with canonical archive metadata. `/bin/x-probe`, `/etc/inittab`, the exact
BusyBox binary, input helper, fonts, device nodes, and all other members remain
byte-identical to Y.

## Dispatch and open-failure contract

`/bin/local-shell` assigns, makes readonly, and exports
`ENV=/bin/reboot-dispatch.env`. It first launches the exact BusyBox as an
interactive non-login ash with `type reboot`. Only the final exact line
`reboot is an alias for /bin/reboot` permits tty1 setup and the final
interactive shell. Any other result records the actual and expected values,
withholds the shell, and enters a static hold without opening the watchdog.

The `ENV` distinction is deliberate:

- the interactive oracle and final interactive ash source the exported alias;
- the `/bin/reboot` shebang starts a noninteractive BusyBox ash, which must
  ignore `ENV` and therefore cannot recursively alias its own commands;
- without `ENV`, exact BusyBox must continue to report the known baseline
  `reboot is reboot` collision;
- a bare-command probe under the configured interactive environment must reach
  an absolute wrapper and preserve its exit status.

The wrapper moves ownership of fd 3 into a function-call redirection:

```sh
if watchdog_session 3>/dev/watchdog0; then
    # unexpected successful function return: hold safely
else
    refuse watchdog0-open-failed
fi
```

The exact-BusyBox execution gate proved that a failed redirection does not
execute the function body and reaches the `else` branch. It also proved that
an alias to an absolute temporary path ending in `/bin/reboot` invokes the
external wrapper, preserves status 73, and returns control to the parent shell.
This replaces Y's fatal special-builtin `exec` redirection. A successful open
scopes fd 3 to
the nonreturning watchdog session, which sends exactly one `.` handoff byte and
keeps the descriptor open through the countdown and overdue hold.

## Watchdog safety contract

No Z automatic or background boot path may open `/dev/watchdog0`, inspect the
watchdog class for ownership, or invoke any reboot command. Merely reaching the
prompt must leave the watchdog unarmed indefinitely. Only the foreground
external wrapper selected by a typed bare `reboot` may proceed.

Before opening the device, the wrapper requires the live no-IRQ
`watchdog@10007000` node, exact class-to-`10007000.watchdog` association,
`mtk-wdt` platform driver and identity, 31-second timeout, zero or unavailable
pretimeout, `/dev/kmsg`, and the bound `44410000.ramoops` observation channel.
A live `interrupts` or `interrupts-extended` property rejects the request before
open.
A failure must report `manual_reboot=refused`, state
`watchdog_armed=no`, exit nonzero, and return control to the interactive shell.

After every preflight passes, the wrapper ignores catchable terminating and
job-control signals, opens fd 3 through the function call, sends one non-`V`
ping, and sends no later byte. It records elapsed markers at 5, 10, 15, 20, 25,
30, 35, and 40 seconds while keeping fd 3 open. If hardware expiry has not reset
the device by 40 seconds, it holds forever with fd 3 retained. There is no
magic close, descriptor close, software reset, generic reboot, synchronization,
or storage-write fallback.

## Completed implementation and validation

The completed implementation and exact evidence are recorded in:

- [build-validation-20260720.txt](results/build-validation-20260720.txt),
  including exact-Y lineage, two recursively identical complete builds, the
  final hashes, and 32-of-32 LK gates;
- [ash-dispatch-validation-20260720.txt](results/ash-dispatch-validation-20260720.txt),
  the exact BusyBox Linux/aarch64 execution result;
- [validator-mutations-20260720.txt](results/validator-mutations-20260720.txt),
  with 75-of-75 attributable corruption rejections;
- [installer-validation-20260720.txt](results/installer-validation-20260720.txt),
  covering the calibrated wrapper, exact-Y installer foundation, one bounded
  target write, and caller-override rejection;
- [runtime-candidate-z-attempt-1-20260720.txt](results/runtime-candidate-z-attempt-1-20260720.txt),
  preserving the owner report, changed boot-ID hashes, post-return watchdog
  boot reason, and the explicitly unobserved subgates;
- [SHA256SUMS](results/SHA256SUMS), covering all public Z result records,
  including the later runtime record.

The two final artifact trees were recursively byte-identical. Each top-level
build also reconstructed its initramfs, dispatch result, and Android-v0 image a
second time internally. The final artifact is:

```text
artifact:          candidate-Z-keyboard-reboot-dispatch-final-985a6472
artifact manifest: 534484e5362e1e4c73ec8438bd36656b444e88199dbd17724a160c75403dbaaa
boot SHA-256:      985a6472b7fdbfd4c58da4773a8c2cae1e3aa40ea90240eb2b309390ed7674b9
boot size:         6,866,944 bytes
initramfs SHA-256: a21cc6bed9024bba9e01864aeb0c6c3339231d217f77ff5fa733ea33e6a0e7d2
padded SHA-256:    ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40
padded size:       16,777,216 bytes
```

The exact BusyBox execution established the baseline standalone collision, the
configured alias, inherited runtime oracle, noninteractive `ENV` isolation,
external `/bin/reboot` execution despite its applet-colliding basename, parent
shell continuation, and catchable function-redirection failure. The mutation
suite additionally covered automatic local-shell watchdog/reset paths,
`interrupts` and `interrupts-extended`, the three fail-closed hold functions,
single-ping/fd retention, complete artifact provenance, and semantic failure
attribution rather than checksum masking.

## Guarded installation result

The calibrated installer replaced rejected Candidate Y on logical `boot2` on
2026-07-20. The complete public record is
[boot2-write-candidate-z-20260720.txt](results/boot2-write-candidate-z-20260720.txt).

The live GPT resolved `boot2` to `/dev/mmcblk0p30`; the active root remained
`/dev/mmcblk0p29`. The target was exactly 16 MiB, writable, unmounted, absent
from swap, had no holders, and the device was on AC power with a full 100%
healthy battery. Its full prewrite checksum was exact Candidate Y
`dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17`.

The installer preserved a full private mode-0600 backup under
`artifacts/device-partitions/pre-candidate-z-20260720T020807Z`, wrote only the
live-resolved `boot2`, synchronized and flushed it, and required matching full
remote and local readbacks. Both equal the padded Z checksum
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`.
The private seven-entry manifest passed with SHA-256
`7689b571f4482b752cff3b7b2192ac3f1428cac8014213502f26306da2114fab`.
The boot ID stayed `1a84fa78-85c9-45d6-87ea-a0c7348dd637`; no boot slot was
selected and no reboot or shutdown occurred.

## Completed attended runtime gate

The owner manually selected logical `boot2` once. Candidate Z booted, keyboard
input still worked, and the typed watchdog-backed reboot returned the unit to
Gemian. The authenticated read-only post-return capture found a boot ID
different from the installation-time boot ID and recorded
`android_bootreason=wdt_by_pass_pwk` with `powerup_reason=reboot`. It did not
remove remote pstore records, access a partition, or reboot the device.

This passes the boot, keyboard-regression, and typed-watchdog-return gates once.
It does not pass the narrower oracle gates: the exact Z marker and prompt,
45-second idle interval, `type reboot` output, absolute-wrapper entry, one-ping
countdown timing, clean tty1 state, and individual-key coverage were not
reported. `console-ramoops` did not retain a Z marker. Consequently the result
cannot prove each internal dispatch/preflight step or a complete keymap, and it
does not establish repeatability.

## Observations

Candidate Z was built twice with recursively identical complete outputs. The
exact BusyBox dispatch result passed, all 32 LK gates passed, all 75 mutations
were rejected for their intended reasons, the calibrated installer suite
passed, and an independent final audit returned GO. At installation, logical
`boot2` had a full-partition checksum of
`ba21e6424f94c82f14fd51b5681eea68d6cf09e9177e4f9ca2061c9f129abb40`
after write, flush, and complete readback.

The single attended selection then added owner-reported successful boot and
working-keyboard evidence. The changed boot ID and watchdog-class boot reason
corroborate the automatic return after the typed command. No exact Z text or
individual input events survived, so the detailed dispatch, countdown, clean
console, and keymap subgates remain open.

## Analysis

The validated alias is narrow because it changes only interactive command
dispatch while preserving noninteractive script semantics. The runtime oracle
tests the same exported `ENV` that the final shell inherits, so a valid build
alone cannot substitute for live dispatch evidence. Function-call redirection
makes watchdog-open failure catchable without weakening the rule that a
successful session retains fd 3 and never sends another ping.

The completed pre-runtime gates establish exact-Y kernel/DT/config identity,
so the later owner report is a regression result over the same hardware path
rather than a new kernel or keyboard-driver experiment. The result supports
the typed-watchdog workaround as working once. It does not make that workaround
a proper default reboot implementation, prove that bare-command dispatch took
every expected internal branch, or promote the minimal console map to complete
keyboard-layout support.

## Conclusion

`runtime-pass-once`: Candidate Z retains exact Y kernel/DT/config with an exact
five-member initramfs delta and passed every pre-runtime gate. Its one attended
selection booted, retained working keyboard input by owner report, and returned
to Gemian after the typed watchdog command; changed boot-ID and watchdog-class
boot-reason evidence corroborate that return. Detailed command-dispatch text,
countdown timing, individual keys, clean-console state, and repeatability remain
unproved.

## Follow-up

Close unchanged Z. Use its proven typed-watchdog path only as recovery for the
separate, one-variable console-map experiment. Test the photographed printable
and navigation layer there before combining it with any kernel restart change.
A proper default restart remains a separate kernel-priority experiment; do not
mix that kernel delta into the console-map boot.
