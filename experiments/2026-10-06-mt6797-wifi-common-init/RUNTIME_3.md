# Phase A runtime 3: common init completes and a passive scan sees a BSS

Status: consumed, 2026-10-07. The laptop device custodian ran one boot of
candidate 3 under [PROTOCOL.md](PROTOCOL.md). It was not repeated. The
sanitized results are
[runtime-3-scan-result.json](results/runtime-3-scan-result.json) and
[runtime-3-session-result.json](results/runtime-3-session-result.json). The
sealed log contains RF calibration data and stays private.

| Item | Value |
| --- | --- |
| Candidate padded boot2 SHA-256 | `827a6582b8913d5130704be38a347beceda2a133b8b86a4033e6fa06df892ce9` |
| Candidate receipt SHA-256 | `28e6b6df119c30c8c9e91ab9bd7c08cbaaef64504167265d6d74e7bde6aa4f1c` |
| Kernel package | `3013daa6…` from input `097c113c`, with patches 0120 and 0121 |
| Mainline boot ID | `a4e42f30-47f6-4b3b-876e-eae821e0ac3b` |
| Complete sealed log | 150642 bytes, 2024 records, SHA-256 `150126d64e521ca5bc7bd12066ccfef46db27bea9d437e2158d1dd8cb8e9547d` |
| Returned Gemian boot ID | `efd5f643-f459-44d7-97e7-93f7e23685ac` |

## Observations

- WMT preparation and negotiation passed. Common init returned 0 with all 285
  steps completed and both PA rails off afterwards. The ROM patches, LTE
  coexistence, RF calibration and antenna mode all completed.
- The classifier found every prerequisite once, in protocol order, and admitted
  the scan.
- One CONSYS-bound wiphy registered. One passive scan of channel 40, with a
  500 ms requested dwell, completed through standard `iw` after 534862 µs.
  It returned a standard 5 GHz BSS result.
- The firmware reported a version-3 management processing count of 15. The
  host saw one native management frame, a validated beacon, one matching done
  header, returned runtime credit and a retired wire lifetime.
- The A53 regression passed. One reviewed native recovery returned to
  changed-ID Gemian.

## Interpretation

This is the first management frame and the first BSS result received by a
mainline kernel on this device. Every earlier scan
([tuning-sample record](../2026-10-02-mt6797-scan-tuning-sample/results/runtime-1.json))
ran without common init and saw a management count of zero. This scan used the
same scan path, so the result supports the Phase A hypothesis: common init was
what the receive path lacked.

Limits:

- One channel and one passive scan only. No association, transmit data,
  packet DMA or traffic was tested, and `wifi_operational` is false.
- RF tuning and effective dwell are not independently verified
  (`rf_tuning_verified` and `effective_rf_dwell_verified` are false).
- Calibration content is not checked. The classifier records only the
  framing metadata of the calibration reply.
- This was a diagnostic profile, not a clean product profile.

## Session exit code

The inherited WMT host counts an obsolete marker name. The Phase A kernel logs
"one-shot CONSYS after WMT: prepower admission passed", so that host exited 1
although every condition held. The Phase A host now applies its own success
condition on the ready path. When the inherited exit is 1, it re-derives
success from the session's own records: regression, provider, recovery, a
complete log, the setup marker once, the renamed CONSYS marker once, and a
demonstrated passive scan. Any other inherited exit code is left unchanged.
[test-host-select.py](test-host-select.py) covers success and each failing
condition offline. No new build or device test was needed.
