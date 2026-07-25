# Experiment: typed hardware-watchdog reboot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-19-keyboard-typed-watchdog-reboot-diagnostic` |
| Status | Rejected by pre-boot command-dispatch audit after build/install; never booted; do not boot |
| Subsystem | Early userspace serviceability and MT6797 TOPRGU reset |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-19 to 2026-07-20 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can the owner-reported working Candidate X session and its serial-only tty1
policy remain available without a timer, while a typed `reboot` returns to
Gemian through the already proven single-stage MT6797 hardware-watchdog expiry
instead of Linux's hanging generic restart path?

Candidate Y is a narrow initramfs-only derivative of exact Candidate X. It
keeps X's complete kernel field, final DTB, resolved configuration, Android
header contract, static BusyBox, input helper, independent probe, font,
keyboard, and serial-only kernel-console policy byte-for-byte. Exactly four
initramfs members change: `/init`, `/bin/local-shell`, `/bin/reboot`, and
`/bin/x-record`.

The unique marker is
`GEMINI_KEYBOARD_TYPED_WATCHDOG_REBOOT_20260719_Y`; the prompt is
`GEMINI-Y#`. No watchdog is opened at boot. Y intended bare `reboot` to reach
the foreground `/bin/reboot` wrapper, but the exact BusyBox standalone-shell
contract resolves the name to its internal reboot applet before `PATH` lookup.
That bypasses the wrapper and defeats Y's distinguishing observation.

## Provenance and environment

The immutable foundation is the final Candidate X artifact:

```text
artifact:          candidate-X-keyboard-manual-reboot-final-bf400387
artifact manifest: a37a774527385e93709bfeab8d93cc0797d908cdc596d046e16e934958218e52
boot SHA-256:      bf4003871daaba1faa293f2b128021d3a67d41ebf3ddff1c42463409803b9296
initramfs SHA-256: b54ce3cd75e7947ed867165e31abbf6ee6cbac7d41d171435f99bba7825bc769
Image.gz SHA-256:  d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41
final DTB SHA-256: bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f
config SHA-256:    0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74
patchset SHA-256:  4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4
```

Candidate X's attended attempt is recorded in
[its runtime result](../2026-07-19-keyboard-manual-reboot-diagnostic/results/runtime-candidate-x-attempt-1-20260719.txt).
The owner reported that X booted and worked, then appeared to hang after typing
`reboot`. No X line survived the subsequent power-key recovery, so the internal
failure boundary was not established dynamically. Static source evidence
places the leading boundary in the kernel restart chain: arm64 quiesces the
machine, PSCI `SYSTEM_RESET` runs before `mtk_wdt`, and the MediaTek restart
handler loops forever writing software-reset if reset does not assert.

This experiment does not claim to fix generic `reboot(2)`. It avoids that path.
Candidate W independently proved the exact retained no-IRQ `mtk-wdt` device,
31-second timeout, one userspace handoff ping, held file descriptor, automatic
Gemian return, and `wdt_by_pass_pwk` boot reason; see the
[Candidate W runtime record](../2026-07-19-keyboard-wrrd-diagnostic/results/runtime-candidate-w-attempt-1-20260719.txt).

## Safety assessment

The builders and validators create and inspect regular files only. They have no
device, partition, SSH, fastboot, MediaTek download, or flashing path. The
installer was calibrated only after two complete builds and exact raw/padded
hashes were independently established. It derives from the hash-pinned,
previously audited Candidate X installer. Its inherited gates resolve logical `boot2` from
the live GPT, require the exact current full-partition X checksum, exclude the
active root, mounts, swap and holders, require exact size/writable/power state,
make a private full backup, perform one bounded write, flush, and demand full
readback equality. It never selects `boot2` or reboots. Primary `boot`, `boot3`,
preloader, NVRAM, GPT, and whole-device writes remain outside scope.

That guarded operation completed on 2026-07-20. It live-resolved `boot2` as
`/dev/mmcblk0p30` while root was `/dev/mmcblk0p29`, backed up exact X, and
verified the full padded Y readback. The device stayed in Gemian with an
unchanged boot ID; no reboot or shutdown was performed. A post-write audit
corrected only two inherited one-letter labels in the private deployment
summary and preserved the original manifest and correction record. Candidate
bytes, predecessor bytes, write, flush, and readback values never changed, and
the identical image was not rewritten.

Inside `/bin/reboot`, the intended preflight requires:

- the exact live no-IRQ `watchdog@10007000` description;
- exact class-to-`10007000.watchdog` association;
- `mtk-wdt` platform driver and identity;
- the proven 31-second timeout and zero/unavailable pretimeout;
- `/dev/kmsg` plus the exact bound `44410000.ramoops` observation channel.

Any pre-open preflight failure records and displays a refusal, does not open the
watchdog, and returns to the shell. After a successful open, signals are
ignored, fd 3 remains open, exactly one non-`V` userspace handoff ping is sent,
and no later write or software-reset fallback exists. A visible countdown runs
in the foreground; kmsg/ramoops markers are emitted at 5, 10, 15, 20, 25, 30,
35, and 40 seconds. If expiry has not reset the device by 40 seconds, the
wrapper holds forever with fd 3 retained and no further ping. A separate audit
found that watchdog-open failure at `if exec 3>/dev/watchdog0` exits the exact
noninteractive ash interpreter, so its `else` refusal path is unreachable. The
watchdog still is not armed on open failure, but the intended refusal marker and
shell return would be absent.

## Associated code

- `initramfs/init`: exact X policy with the Y entry marker/profile and explicit
  typed-only watchdog ownership.
- `initramfs/local-shell`: exact Y prompt and marker, plus the rejected bare
  `reboot` instruction.
- `initramfs/reboot`: watchdog-expiry wrapper that exists but is bypassed by the
  displayed bare command under exact BusyBox standalone-shell dispatch.
- `initramfs/x-record`: Y marker while retaining X's recorder pathname to keep
  the archive delta narrow.
- `scripts/validate-x-baseline.py`: exact X artifact, package provenance,
  Android container, Image.gz, DTB, initramfs, helper, inventory and mode gates.
- `scripts/build-initramfs.sh` and `scripts/validate-initramfs.py`: deterministic
  overlay and an independent newc parser requiring exactly four changed
  members plus typed-only watchdog semantics.
- `scripts/build-boot-from-x.py` and `scripts/validate-boot.py`: preserve the
  exact X kernel field and header, changing only ramdisk size, ramdisk bytes,
  canonical ID, and consequent zero padding.
- `scripts/build-keyboard-typed-watchdog-reboot-candidate.sh`: immutable input
  snapshots, two independent initramfs/container assemblies, standard 32-gate
  LK analysis, flat output manifest, atomic handoff, and post-handoff validation.
- `scripts/validate-final-artifact.py`: final inventory/mode/manifest validation
  and fresh execution of every component validator plus the LK analyzer.
- `scripts/test-validator-mutations.sh`: positive controls and rejection tests
  for runtime-contract, component, archive, race, symlink and final-artifact
  corruption.
- `scripts/install-candidate-y-boot2.sh`, `scripts/derive-installer.py`, and
  `scripts/test-installer-static.sh`: calibrated exact-X installer derivation
  and non-device static checks.

All build and validation commands are unprivileged. Only the separately
calibrated installer uses SSH and passwordless sudo on the named device.

The durable public evidence is the [final build
reproduction](results/final-build-reproduction-20260720.txt), [35-case mutation
result](results/validator-mutations-20260720.txt), [restart-path source
audit](results/restart-path-audit-20260720.txt), and [guarded logical-`boot2`
write/readback](results/boot2-write-candidate-y-20260720.txt). The decisive
[pre-boot command-dispatch audit](results/preboot-command-dispatch-audit-20260720.txt)
supersedes the earlier readiness interpretation.

## Completed build and installation

The top-level builder ran twice in the QEMU guest. Both builds internally
reproduced the initramfs and Android-v0 container, their complete output trees
matched recursively, and both final manifests have SHA-256
`310ac503b4bbd8c5a3d5c31bcecb473064d5207ff30ad73111325ffe1a1c56a6`.
The 6,866,944-byte raw image has SHA-256
`94edd593924c52f0224f1ba2134120b54516e622aee3c52de2781a4ec8e889ee`;
the initramfs SHA-256 is
`11b0a8ecb144ebde0c9802e0cf7357b2d74b95e8ba44fbf6007a9f4d0d8bf3e2`.
Both final validators and all 32 LK gates passed, and all 35 intended mutations
were rejected.

The exact padded 16 MiB image has SHA-256
`dab4a5217ddffe32062819febc3160f0a12eb97ac8afbf0bc4f068ce3c72cb17`.
The installer backed up predecessor X whose full checksum was
`e89d71f15465b544db163b5f0b90b456e913c38ba4d2ed49aa7bde345148c855`,
then wrote, synchronized, flushed, and fully read back exact Y. This establishes
stored bytes only, not runtime behavior.

## Pre-boot rejection: do not boot

Do not manually select Y from `boot2`. In the exact BusyBox binary, standalone
applets take precedence over `PATH`; `type reboot` reports exact
`reboot is reboot`. The displayed bare command therefore invokes BusyBox's
internal reboot applet rather than `/bin/reboot` and can re-enter the same
generic restart path that appeared to hang under X. Explicit `/bin/reboot`
exists, but it is not the displayed/operator-tested contract and cannot rescue
this already-built artifact's attribution design.

No device boot is needed to distinguish this outcome. Candidate Y is
superseded by [Candidate Z](../2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md),
whose exact-BusyBox validation makes command dispatch an input and whose
function-call redirection makes watchdog-open refusal reachable.

## Observations

Candidate Y was built, validated, exported, installed on logical `boot2`, and
fully read back before Z replaced it there. Its two complete builds are
recursively identical, all 32 LK gates and 35/35 mutation rejections passed,
and its historical full-partition readback matches the exact padded image. The
later command-dispatch audit rejected Y before boot. Y has never been selected
or booted, has zero runtime evidence, and must not be booted.

## Analysis

The exact X kernel already contains the built-in no-IRQ MediaTek watchdog and
the MT6797 AUTO_RESTART policy used by the hardware-proven W expiry path.
Reusing exact X would have isolated explicit userspace ownership only if the
displayed command reached the external wrapper. Exact BusyBox dispatch disproves
that prerequisite.

Opening watchdog0 activates userspace ownership. With the retained 31-second
timeout equal to the driver's maximum hardware heartbeat, the watchdog core
does not schedule an active-userspace keepalive worker. One explicit handoff
ping defines the observable start of the expiry interval. Keeping the fd open
and sending no further byte avoids both a magic close and the close-time extra
ping.

The pre-boot rejection makes PSCI, watchdog-expiry runtime, tty1, and keyboard
behavior under Y untested. Valid artifact and partition checks do not offset a
failed operator-command attribution gate.

## Conclusion

`rejected-preboot`: Candidate Y was reproducibly built, installed, and fully
read back but must not be booted. Its displayed bare command bypasses the
watchdog wrapper, and the wrapper's watchdog-open failure refusal is
unreachable. Y is superseded by validated, installed, but unbooted Candidate Z.
Candidate X remains the last owner-tested candidate; Candidate W retains the
last detailed keyboard events and proven watchdog-expiry return.

## Follow-up

Do not boot Y. Candidate Z preserves the exact hardware foundation while
making bare-command dispatch and watchdog-open refusal independently testable
and statically enforced; its build, validation, and guarded write/readback are
recorded in the [successor experiment](../2026-07-19-keyboard-reboot-dispatch-diagnostic/README.md).
Treat generic `reboot(2)` as a separate kernel experiment; do not mix it into
Y's closed record.
