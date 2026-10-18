# C10: mask-only control comparison

Built and privately composed, 2026-10-18 UTC; no installation or runtime result.
The [comparison design](MASK_ONLY_COMPARISON.md) records the hypothesis,
resource scope and decision branches before implementation. C9 is consumed.
This is an availability comparison, not a proven RX-group contract or a fix for
length refusal. Full ordinary secure Wi-Fi acceptance remains incomplete.

## Validated kernel inputs

Clean pushed input `0d1f51194d7001fc9c6b9219726935ede36bc828`, profile
`mt6797-a53-wifi-ccmp-mask-control`, 32 jobs on Buildbox, modules off.
The standard build entrypoint completed and validated its package at
`2026-10-18T02:39:23Z`. No VM/local kernel build. The
[build record](results/ccmp10-build-validation.json) pins the exact cross-toolchain,
configuration, patchset and applied source files.

- Inventory: `1ef1141b3e78647d072cced777965b79492f8193e310bf4011e1d026b26d9dd0`, 852 members, 123 DTBs.
- Image.gz: `dcc58eb67eef79e8a7463350ffb0b5e5c06e832fad3e9ab288faf13feca01f42`.
- Config: `005d81ad9c877c8b5d1dd721452c6c08e0c87ec0a04af27eec2b3e880ab9bb31`.
- Patchset: `93eab8c4a5dee069b051f6763425f04e3c8914e9b1171fb9a75ecbc25b32eb9c`.

The generated configuration equals C9 plus exactly
`CONFIG_MT6797_CCMP_MASK_CONTROL=y`. All budgets, crypto, clock, CPU and other
board settings are unchanged. The selected series is C9's ordered 694 plus
0200; 26 inherited fragments plus the one-option fragment. All 33 profile
checks pass. Six applied driver files match the tested source snapshot; the
linked kernel contains the new helper and one fixed submission format string.
This verifies compilation/selection, not execution of the control on hardware.

Linux ASan/UBSan actual-source validator/HIF/MAC and RX comparisons pass,
including both ports, all five mismatches, partial transfer/deadline poison and
no second I/O. A GCC warning in a generated test assertion was corrected with
parentheses; warning checks were retained. The earlier private fixture-copy
preparation left the copy unpatched and was caught by exact reversal, before
compilation. Neither issue changed kernel behavior or caused a device retry.
Strict checkpatch, fed the patch on stdin rather than its tracked file path,
reports one missing truthful DCO sign-off, zero warnings and zero checks.
The internal non-certifying archive does not invent that certification.
No DT change was authored; ordinary DTB compilation passed, no new schema claim.

## Real composition

The [compositor](build-ccmp-candidate-10.py) consumes only that real validated
package and the exact private C32 parent. Its
[receipt](results/ccmp-stable-monitor-candidate-10.json) is byte-identical to the
[runtime receipt](runtime-ccmp10/results/candidate.json), SHA-256
`807c8fb9f886ce0209688740f67193626a86311b76e02d198a66b7d749b2b11c`.
It explicitly records `mask_control=true`, ordinary DHCP bootstrap, no GTK RX,
no key reuse and physical admission false.

Raw boot is 12673024 bytes,
`fbe72c31ced5efd7c81317d23e3336141bf44eaf8a8a9e02b682353822112d45`.
Exact 16 MiB padded boot2 is
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`.
All six actual private members pass size/hash/mode-0600 checks. DT and the
64-member private RAM root are byte-identical to C9; only Image/config change.
The actual-config oracle passes six changed-parent refusals and five child
configuration differences. No placeholder receipt or fabricated image identity.

Release and the inherited USB names remain
`7.1.3-gemini-a53-wifi-ccmp-stable-monitor`; those historical strings do not
identify C10 or prove monitor mode. Installation provenance, the new helper
symbol, fresh boot and mask submission observations must bind the runtime.

## Fresh tooling and remaining gates

New [prepare](prepare-ccmp10.py), [installer](install-ccmp10.py),
[capture](laptop-capture-ccmp10.py), [host](passive-host-ccmp10.py) and
[session](laptop-session-ccmp10.py) adapters keep completed tools unchanged.
They retain real-receipt checks, new capture/session namespaces, the no-scan
failure route, original recovery/installer pins and separated historical-source
versus credential roots. The installer additionally requires the new profile
and mask flag. The expected predecessor is C9 full boot2
`851a465efddff08895b726767b95d74a59a690ab648222c2dc67a936a06f6f61`;
that historical identity must be verified by the actual guarded deployment.

All five offline binding/config/source-routing fixtures pass locally. Six exact
historical public source files were independently found by digest in Buildbox's
existing Git objects for the Linux fixture inputs; no credential or Linux source
tree was copied there. Linux tooling checks, the actual derived installer review,
full offline host preparation and guarded live-GPT installation remain pending.
No helper has started; there is no deployment receipt or C10 capture/session.

After all gates pass, the owner physically selects boot2 following verified
readback and clean shutdown. The admitted runtime remains one capture, one
session and one reviewed return, with unchanged limits. Require actual network,
transport and cleanup verdicts independently; a different failure is a separate
result. No unchanged retry, metadata bypass, length exception, deadline extension
or promotion to maintained Wi-Fi follows from build/composition success.
