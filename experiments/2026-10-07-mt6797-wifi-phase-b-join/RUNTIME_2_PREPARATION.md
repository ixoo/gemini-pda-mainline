# Second Phase B deployment, physical boot pending

Status: installed and fully read back; device cleanly powered off. No mainline
boot, host RF transmission or join result has been observed for this
candidate. The owner must physically select boot2; the laptop remains the sole
custodian.

The [guarded deployment receipt](results/deployment-2.json) pins candidate 2:
receipt `f19dffdb…`, full padded boot2
`03a6d78caf8d38eca3d46015dc053defa8677d6e75ab40454593fe8155590bf4`, written,
synced and flushed, with an independent whole-partition stream digest and byte
comparison matching. The installer was prepared offline from the
[compile 7](COMPILE_7.md) package through `install-passive.py` at revision
`450951ed` (generated installer SHA-256 `c544d590…`) and executed once under
the standing boot2 authorization. The live boot2 guard passed: target
`179:30`, root `179:29`, exact Gemian boot
`9b0bb289-0931-4521-ae0a-acaadf4672a1`, stable power. The predecessor matched
the installed runtime-1 candidate `6ecc057c…`. No fresh predecessor backup was
made; the verified project-wide backup remains the recovery foundation. Native
Gemian power-off was requested after the evidence flush, the SSH session ended
with status 255, the device was confirmed unreachable, and nothing was
rebooted.

Runtime-2 preparation state on the laptop: the fresh evidence root holds
`wifi-phase-b/session-2` with the true deployment summary; `capture-2` is
absent, as the inherited capture requires. The offline `laptop-session.py`
preparation passed. The offline `laptop-capture.py` preparation also passed but
exited 1, because this experiment's capture `main()` checked the not-yet-claimed
capture log even without `--execute`; that status bug is fixed in this
revision, with the execute branch unchanged.

The next action is the owner-operated boot2 handoff followed by the exact
[bounded protocol](PROTOCOL.md) under the
[runtime 2 bindings](README.md#runtime-2-bindings-2026-10-06). The first
decision-changing observation is the common-init result: a repeat of the
runtime-1 step-5 failure now prints the interrupt cause in the failure footer;
a pass reaches the join path for the first time. Raw installation evidence,
AP inputs and later captures stay private.
