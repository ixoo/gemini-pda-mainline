# Experiment: current-DT USB observation restoration

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-16-mainline-current-dtb-usb-observation` |
| Status | exact candidate installed and fully read back; device shut down for one attempt |
| Subsystem | MT6797 USB gadget, Device Tree, Planet LK handoff |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-16 America/New_York |
| Investigator(s) | repository owner and Codex |
| Tracking issue | current-mainline observable boot prerequisite to CPU8 work |

## Question or hypothesis

Did the stopped current-DTB GAEL attempt lose the established observation DT
rather than prove an LK or arm64 entry failure? Keep the exact current kernel,
package DT, initramfs, Android-v0 layout, CPU policy, and all hardware-facing
nodes unchanged except the three existing USB PHY/device `status` properties
needed for the direct gadget console.

An exact current-kernel identity over the restored netcat path proves that the
current DT is serviceable without the other Stage-27 DT differences. Mainline
USB enumeration without netcat localizes after kernel USB initialization but
before the service endpoint. No mainline USB observation followed by a changed
Gemian return remains a bounded negative at or before this observation path;
it is not evidence of absent Image entry.

## Provenance and environment

- Exact Buildbox package from repository commit
  `98996fdfbf09f8de2a6b86e488defef22fcc7968`, profile
  `da921x-modules-arm64-entry-ledger`, release
  `7.1.3-gemini-entryled-a`.
- Exact current package DTB SHA-256
  `61ea34a4f780afe04da1257f8c3655be7f8490a7c3af2df727dd8592bb6e6285`.
- Exact serviceability initramfs SHA-256
  `e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f`.
- Runtime-proven control: current Image plus Stage-27 DTB, documented by the
  [LK handoff DTB control](../2026-08-16-mainline-lk-handoff-dtb-control/README.md).
- Public Planet LK source-contract reference commit
  `f4988d74bb70a0a15d7f362f412afba7e7fcda46`; it is not claimed to be
  byte-identical to the installed loader.
- No kernel compilation is needed. No native VM build is permitted or run.

## Safety assessment

This candidate adds no hardware write path, regulator operation, CPU admission,
or storage access from Linux. It changes only three existing DT strings from
`disabled` to `okay`: the USB T-PHY, its USB2 port, and the MTU3 peripheral
controller. The xHCI child stays disabled, the role stays peripheral, and the
speed stays high-speed. CPU8 and CPU9 remain offline.

Any installation is limited by standing policy to the one live-GPT-resolved,
inactive, unmounted, writable 16 MiB logical `boot2` partition. Record the
predecessor but create no new backup; the project-start device backup is the
recovery source. Require stable power, exact padding, write/sync/flush, and a
matching full-partition readback, then shut down cleanly. Never reboot or select
boot2 automatically. Stop on every identity, target, power, or readback error.

## Associated code

- `scripts/build-usb-observation-dtb.sh`: exact-input, three-property DT
  derivation with fixed output identity and retained peripheral-only policy.
- `scripts/build-candidate.sh`: source-pinned reuse of the validated GAEL
  assembler, two raw assemblies, two padding constructions, and an extended
  candidate manifest.
- `scripts/test-candidate.py`: independent candidate inventory, manifest, DT,
  Android-v0, gzip, initramfs, identity-map, and mutation validator.
- `scripts/install-boot2.sh`: source-pinned guarded boot2 installer with exact
  candidate and manifest identities, full readback, and clean shutdown.
- `scripts/collect-runtime.sh`: pre-armed USB/interface observer with
  source-pinned read-only identity/service probes and changed-Gemian fallback.
- `results/lk-sensitive-dtb-audit-20260816.txt`: LK callback, DT lineage, and
  minimal-repair selection evidence.
- `results/offline-candidate-validation-20260816.txt`: exact candidate
  identities and independent validation results.
- `results/predeployment-hypothesis-20260816.txt`: unique USB-attached live
  decision map declared before deployment.
- `results/deployment-1-20260816.txt`: live GPT, predecessor, exact write,
  independent full readback, and confirmed clean-shutdown evidence.

The exact generated candidate remains under the ignored `artifacts/` tree.

## Procedure

1. Map Stage-27/current semantic DT differences to every public-LK callback
   that can observe them before the final arm64 branch.
2. Correct the DT lineage comparison: distinguish the package base DT from the
   frozen enabled serviceability DT reused by the Stage-27 candidate line.
3. Derive the current DT twice with only the three USB `status` changes and
   require byte identity plus the exact output hash.
4. Assemble the unchanged current kernel and initramfs twice, construct 16 MiB
   padding by two methods, run all 32 LK gates, and reject structural mutations.
5. Commit and push the candidate definition and identities before deployment.
6. With the USB cable attached and host observation armed, install only the
   exact validated payload to logical boot2, verify it fully, and shut down.
7. Select boot2 once. Classify exact netcat identity, mainline USB enumeration
   without netcat, or no mainline USB before a changed Gemian return. Do not use
   screen color or returned empty ledger slots as a negative oracle.

## Observations

The offline audit is complete. The public loader reference ignores the overlay
return, tolerates absent CPU `clock-frequency`, finds `/chosen` in both DTs,
and checks reserved-memory conflicts from identical `reg` ranges rather than
the three changed compatibility strings. None of those audited differences
supplies a strict stop unique to the current DT.

The important lineage difference is outside those callbacks: Stage 27 did not
boot its package DTB. It reused a frozen Gate-3 serviceability DT with USB and
other observation nodes enabled. The stopped GAEL candidate instead used the
new package base DT directly, where the three existing USB nodes are
deliberately disabled. Its lack of USB therefore did not establish an LK or
Image-entry failure.

An offline derivation of the exact current package DT changes only the three
selected `status` properties in decompiled semantic form. Its SHA-256 is
`e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331`.

The exact raw Android-v0 container SHA-256 is
`a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be`;
the exact 16 MiB boot2 payload SHA-256 is
`fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87`.
Two assemblies and two padding constructions are byte-identical. All 32 LK
gates pass, all four entry-ledger markers remain present, the extended manifest
passes, and six independent structural mutations are rejected.

Guarded deployment 1 resolved the sole live GPT `boot2` as
`/dev/mmcblk0p30`, distinct from the active Gemian root on
`/dev/mmcblk0p29`. The inactive partition's predecessor matched the exact
Stage-27 control payload. With stable 100% battery and external power, the
installer wrote, synchronized, flushed, and independently read back all 16 MiB.
The readback matched the candidate byte-for-byte and by SHA-256. No fresh
partition backup was created. The device then powered off cleanly and remained
unreachable; it was not rebooted automatically.

## Analysis

The positive Stage-27-DTB control remains valid, but it proved the current
Image with a broad serviceability DT, not that LK rejected the package DT.
Restoring only the already-described peripheral USB path is the smallest way
to make the package DT observable while leaving every unrelated Stage-27
difference on the current side.

## Conclusion

Confirmed offline and installed for one guarded attempt: the stopped GAEL attempt
omitted the candidate-time USB observation DT used by the serviceable lineage.
Its missing USB was therefore not a clean boot-failure result. The exact
three-property derivative passes every declared offline candidate gate;
hardware behavior remains untested. The exact boot2 write and full readback are
verified, and the device is shut down. CPU8 and CPU9 remain closed.

## Follow-up

Physically select boot2 once with USB already attached and classify it using
the predeclared decision map. The ordered project action remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
