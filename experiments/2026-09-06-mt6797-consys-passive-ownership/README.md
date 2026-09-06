# Experiment: passive Gemian CONSYS ownership snapshot

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-06-mt6797-consys-passive-ownership` |
| Status | complete; live attempt consumed once |
| Subsystem | MT6797 CONSYS/WLAN reserved memory and OS-visible ownership |
| Device variant | Named project Gemini; Gemian model preflight `MT6797X` |
| Date(s) | 2026-09-06 UTC |
| Investigator(s) | `/root`, sole device custodian; Codex-assisted review |
| Tracking issue | [Wi-Fi issue 25](https://github.com/ixoo/gemini-pda-mainline/issues/25) |

## Question or hypothesis

Can the running known-good Gemian system expose the actual connectivity
reserved-memory descriptor and the OS-visible owners of the WLAN/CONSYS
platform resources through passive kernel metadata? A coherent reservation
and bound-owner result will narrow the first shared-manager implementation.
Unavailable metadata is inconclusive and redirects work to retained-source
analysis; it never authorizes register reads or a firmware start.

## Provenance and environment

- Repository: `99831dc50f93577c4535ae96d56adfc774985a3f`.
- Preflight release: `3.18.41+`; boot ID:
  `ce741f2c-462f-424e-aa90-49bada3a116f`; model: `MT6797X`.
- Transport: known-host, dedicated-key `gemini` SSH alias.
- Prior contract: [shared owner implementation](../2026-09-05-mt6797-wifi-contract/SHARED_OWNER_IMPLEMENTATION.md).
- No patch, configuration, profile, package or boot candidate is selected.

## Safety assessment

The collection is read-only. It uses named kernel metadata files and symlinks;
it issues no `devmem`, debug ioctl, sysfs write, mount, sudo, service, network,
radio, firmware, calibration, reset, clock, regulator, DMA or power command.
One SSH collector attempt is allowed, with a ten-second remote deadline and
64 KiB output ceiling. Identity is checked at the start and end. Any mismatch
or need to widen effects stops the session. SSH traffic may traverse the stock
radio; this is not a radio-silence claim.

## Associated code

- `collect.py`: exact SSH wrapper with a 15-second host deadline, streaming
  64 KiB combined-output cap, strict known-host authentication and remote
  ten-second `timeout`.
- `remote-collect.sh`: fixed allowlist executed by a remote POSIX shell. It
  refuses an identity mismatch before metadata and rechecks identity afterward.
- `test_collect.py`: nine hardware-free identity, framing, size, process-status
  and timeout refusal fixtures.
- `SESSION.md`: exact finite budget, classification and stop conditions.
- `results/observation.json`: sanitized identity, DT metadata, bound-driver
  observations, result classification and executed-collector identities.

## Procedure

1. Review both scripts for effect-free interfaces, exact identity enforcement
   and active host bounds; run the nine refusal fixtures.
2. Execute `python3 -B collect.py` once. Its remote script checks the frozen
   preflight identity before any metadata read.
3. Keep the wrapper's strict authenticated SSH, remote and host deadlines, and
   combined-output cap unchanged.
4. Require matching end identity and classify each requested observation as
   present or unavailable.
5. Record a bounded sanitized result and consume the attempt regardless of
   pass, failure or inconclusive outcome.

## Observations

The first draft was refused before collection because its identity and budget
limits existed only in prose, it omitted DT cell-width context, and two shell
constructs were not portable. The revised collector implemented those limits,
recorded root/reserved-memory address and size cells plus `ranges`, distinguished
missing/unreadable/read-error metadata, removed the module listing and labelled
the WLAN parent as an attribution cross-check. Shell syntax, ShellCheck, nine
refusal fixtures and additional subprocess overflow/deadline checks passed.

The single admitted collection completed in 0.7 seconds with stable start/end
identity. Root and reserved-memory address/size cell properties each decode to
two cells; reserved-memory `ranges` is present and empty. The live
`consys-reserve-memory` node has `no-map`, lacks `reusable`, and lacks `reg`, so
it is a dynamic descriptor but does not expose its allocated base or extent.
`/proc/iomem` was unreadable. The platform bus binds `18070000.consys` to
`mtk_wmt` and, as an attribution cross-check, `180f0000.wifi` to `mt-wifi`.
The observed `10001000.*` devices and `11000000.ap_dma` were unbound; every
queried platform `resource` file was missing.

The SSH client emitted a post-quantum key-exchange advisory, a remote locale
warning, and an unsuccessful attempt to update its host-side `known_hosts`.
None changed device state. The committed wrapper now sets `UpdateHostKeys=no`
while retaining strict host-key checking; the collector was not rerun. The
result records hashes of the exact pre-fix scripts that executed.

## Analysis

The observation corroborates a dynamic no-map connectivity reservation and
identifies the two running vendor drivers that must inform a shared-manager
boundary. It does not supply the live dynamic allocation, because `reg` is
absent and `/proc/iomem` is unreadable. Missing platform resource files also
prevent a complete runtime resource map. These absences are inconclusive, not
evidence of no allocation or exclusive ownership. Metadata cannot establish
electrical ownership, firmware quiescence, safe MMIO access, remap contents,
MPU policy or DMA idleness.

## Conclusion

The hypothesis is partially supported. Passive metadata confirms the live
descriptor form and the `mtk_wmt`/`mt-wifi` bindings, but not the allocation's
base or extent. The result narrows retained-source analysis of the shared
manager; it does not admit any active connectivity operation.

## Follow-up

Use retained vendor-source and already captured evidence to bound the dynamic
reservation contract and the split between `mtk_wmt` and `mt-wifi`. Do not
repeat this artifact merely to obtain the same metadata. Any future privileged
observation of the live range needs a separate decision-changing protocol.
Keep active CONN transitions, EMI protection, copying, START and AP-DMA as
separately admitted effects.
