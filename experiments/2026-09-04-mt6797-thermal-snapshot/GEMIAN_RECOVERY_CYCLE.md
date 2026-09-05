# Recovery cycle from the observed Gemian boot

The [exact recovery shell suite](results/recovery-exact-shell-pass.json) passed,
but the [starting-state check](results/recovery-cycle-start-state.txt) found
Gemian rather than the consumed mainline session. This adapter changes only
cycle provenance and host entrypoint; it does not change the candidate or the
bounded recovery program. It supersedes the old-mainline cycle preparation in
[RECOVERY_PROTOCOL.md](RECOVERY_PROTOCOL.md). No old-mainline receipt is invented.

## Hypothesis, limits and decision

Use candidate SHA256
`666961b636b21b8598a64999e9dbf72af280ad99f07a6b745045320f24ca361b`, release
`7.1.3-gemini-thermal-snapshot`, and the same exact A41 record. The independent
measurement is the reported per-slot temperature after the finite owned workers
have completed and a bounded two-second interval has elapsed. A decrease,
unchanged value or increase remains observational; none establishes conversion
freshness or erases the previous thermal rejection. The three snapshots,
three inherited frequency boundaries, two ordinary reads, four-round workload,
one CPU admission and one CPU9 down/restore remain exactly as specified in
[the recovery design](RECOVERY_DESIGN.md).

The full baseline comparison is not evaluated because the writers-waiting
thermal sample is absent. Shared-boundary rejection stays nonzero even if
reported temperature later decreases. Absolute bounds, stage timing, CPU/RAM
integrity, child quiescence and cleanup remain mandatory. No broader hotplug,
clock/OPP change, forced conversion, idle/suspend, longer stress or default
integration is admitted.

## Known-good-OS preparation

The [installer adapter](scripts/install-recovery-boot2.sh) retains the validated
source-pinned live-GPT installer and adds one exact source-boot guard:
`5d45171e-6c70-4fe4-99b6-715ac22ca826`. A different Gemian boot refuses before
the partition gate. All architecture/kernel, active-root, unique boot2 GPT,
size/writability, mount/holder/swap and stable-power checks remain intact.
Matching full-partition identity skips the write. Otherwise only the admitted
inactive boot2 is written, synced and flushed. Both branches require the final
full checksum and independent 16 MiB host readback/byte comparison, removal of
the temporary readback, durable evidence and clean shutdown/unreachability.
No fresh backup or automatic reboot is created. Build/repackaging is unnecessary.

After publishing the adapter's full validation result, run exactly:

```sh
bash experiments/2026-09-04-mt6797-thermal-snapshot/scripts/install-recovery-boot2.sh --execute \
  --target gemini@192.168.1.50 \
  --candidate-dir artifacts/thermal-snapshot-composition/candidate-c2ddeea9 \
  --evidence-dir artifacts/device-install-evidence/thermal-snapshot-deployment-recovery-gemian-1
```

The required ignored key and repository SSH options are inherited unchanged.
The new evidence directory is exclusive. A partial or failed installation is
not a cycle receipt and cannot admit a workload. Never delete evidence to retry.
The owner physically selects boot2 only after the complete receipt validates.
Expect the existing potentially absent visible console and USB/netcat service
at `10.15.19.82:2323`; this experiment makes no new display claim.

## Receipt and runtime entrypoint

The [Gemian recovery runner](scripts/run-gemian-recovery.py) pins the previous
recovery runner and its complete dependency set plus this installer adapter.
It requires exactly the mode-0600 summary and manifest in the mode-0700
installation evidence directory. It checks the manifest, exact receipt fields,
candidate/readback match, stable-power predicate, skipped-image predecessor
where applicable, completed shutdown/unreachability and exact source Gemian
boot. Unexpected files, symlinks, modes, duplicated or missing fields refuse.
The published attribution classification is still pinned as historical evidence.

Validate the resulting receipt offline:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-gemian-recovery.py
```

After owner selection and USB readiness, execute once:

```sh
python3 experiments/2026-09-04-mt6797-thermal-snapshot/scripts/run-gemian-recovery.py --execute
```

The exclusive runtime capture is
`artifacts/runtime-captures/thermal-snapshot-recovery-gemian-1`. It saves the
receipt and original attribution classification, verifies a new exact pristine
frame, then durably saves the generated program and request marker before
transport. All consumed boots, including the source Gemian boot, are refused.
At most three shell sessions are used: pristine state, bounded workload, final
state. Pre/post outer limits stay 20 s and workload 125 s. The core supplies
unchanged connection/idle limits and final-state equality checks. Structurally
complete comparison rejection receives the one declared postflight and stays
nonzero; incomplete execution receives no extra device request. Every outcome
retains a manifest and cannot reopen its capture.

## Validation and admission

The adapter has host fixtures for write/skip receipts, per-field mutations,
evidence directory boundaries and the actual one-shot runner under injected
USB. The installer derivation passes Bash syntax and ShellCheck. The complete
`--suite gemian-recovery` exact-candidate BusyBox validation must be published
before the preparation command above is selected. The underlying program's
prior exact-shell pass does not alone validate this new host adapter.


## Initial-state precision review

The [first adapter exact-shell run](results/gemian-recovery-shell-c50c340b.json)
passed its fixtures on `c50c340b`, but a review found that initial temperature
precision was enforced by the thermal assessor only after execution. Its
inherited pristine gate already checked range; the adapter now also rejects
non-100-mC values before program creation and request publication. A new
preflight mutation proves that no workload request follows this refusal.
This earlier pass does not admit device preparation. Revalidate the corrected
published revision under the exact candidate shell before selection.


## Final adapter admission

The [corrected full exact-shell suite](results/gemian-recovery-final-shell-pass.json)
passes on clean published revision `ec05d52173e69bf0eaceec5ba9e256f9a6b0c7e5`,
including the pre-admission precision refusal and all 15 Gemian host/restart
cases. The same exact candidate BusyBox and initramfs hashes were verified;
temporary binary, artifact copy and Git checkout were removed. No device
operation or kernel build was part of validation.

Publication of this result selects the exact guarded installation command
above on the named Gemian boot. Reuse the existing candidate, skip a matching
image, require full readback and complete shutdown evidence, then validate the
receipt offline before asking the owner to select boot2. The runtime remains
gated on that receipt and a fresh pristine mainline frame. No additional
thermal snapshot or workload is permitted on any consumed session.


## Prepared device cycle

The [deployment receipt](results/recovery-Gemian-deployment.txt) and
[preparation record](results/recovery-cycle-preparation.txt) now validate.
Live-GPT boot2 already matched the exact candidate, so no write occurred.
The independent full-partition readback and byte comparison passed under stable
power, temporary readback was removed, and Gemian shutdown/unreachability was
confirmed. The new runner's receipt-only check passes without device access.
No new mainline boot or recovery workload is claimed yet. Physical boot2
selection is now required before the exact pristine gate and single run.
