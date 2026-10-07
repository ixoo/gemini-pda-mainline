# Third Phase B deployment, physical boot pending

Status: candidate 3 installed and fully read back; device cleanly powered
off. No mainline boot, host RF transmission or join result has been observed
for this candidate. The owner must physically select boot2; the laptop remains
the sole custodian.

The [guarded deployment receipt](results/deployment-3.json) pins candidate 3:
receipt `00f6c619…`, full padded boot2
`84f65eae0a5ddc63f1c271ba78873d54e61bec30ec6e8ae176cb8394098f0adc`, written,
synced and flushed, with an independent whole-partition stream digest and byte
comparison matching. The installer was prepared offline from the
[compile 8](COMPILE_8.md) package through `install-passive.py` (installer code
unchanged between a46cd57e and `75c850d9`; generated installer SHA-256
`318f6dc9…`) and executed once under the standing boot2 authorization. The
live boot2 guard passed: target `179:30`, root `179:29`, exact Gemian boot
`1b7e766a-ab22-47ec-a0a5-6b3efe7bc34d`, stable power. The predecessor matched
the installed candidate 2 `03a6d78c…`. No fresh predecessor backup was made;
the verified project-wide backup remains the recovery foundation. Native
Gemian power-off was requested after the evidence flush, the SSH session
ended with status 255, the device was confirmed unreachable, and nothing was
rebooted.

Runtime-4 preparation state on the laptop: a fresh evidence root holds
`wifi-phase-b/session-3` with the true deployment summary; `capture-3` is
absent, as the inherited capture requires. The join script was rebound from
the unchanged private target, and both offline preparations passed.

Hypothesis for the boot: initialization and the passive scan repeat runtime 3,
and the first connect either prints the refused-condition bitmask from
proposal 0143 (`one-shot WLAN join peer refused: reasons=…`, optionally
preceded by `one-shot WLAN join channel refused: …`) or proceeds into an
actual management exchange. Either outcome is decision-changing; an identical
retry is not. The bounded protocol and the reviewed native recovery are those
of runtime 3 under the [runtime 4 bindings](README.md#runtime-4-bindings-2026-10-07).
