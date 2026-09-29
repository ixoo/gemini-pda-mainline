# Passive region-19 private export

The [passive predecessor](../2026-09-29-mt6797-region19-mainline-observe/results/runtime-2.json)
found 267 nonzero bytes across 110 pages before CONN power. That count does
not identify the bytes, a writer or whether WMT's first-343-KiB clear would
discard a record. Arm64 `/dev/mem` read rejects the no-map reservation.
[Patch 0047](../../patches/proposals/0047-soc-mediatek-export-passive-MT6797-region19.patch)
therefore lets root read exactly the second 512 KiB of the validated boot
reservation from the passive CONSYS owner. The sysfs file is read-only, and
the DT still excludes all active CONN, EMI, firmware and radio probes.

The one-boot hypothesis is that two authenticated reads in the same mainline
boot return a complete, stable pre-power window. The unique observation is
the exact padded boot2 readback and changed boot ID, two bounded private
captures with hashes and equality, one complete kernel log, A53 regression,
and a confirmed changed-boot Gemian Wi-Fi return. Matching captures admit
private layout analysis in the RE VM. Missing or differing captures, failed
identity/log/regression, or a failed return stop this candidate; none permits
a region-19 clear or firmware START. Raw memory, logs, firmware and credentials
stay under ignored private artifacts. Only aggregate results may be published.

The named `mt6797-a53-wifi-region19-export` profile built from clean pushed
commit `b489c1cd9fa91c63a6119ee2c009ca951373489b` on Buildbox. Its
validated package inventory is
`b86589f1ff1245d539e81cb5713d75c435040114dccbb24d022d11aedb0fa3dd`.
The compiled Gemini DTB is byte-identical to the prior profile's built DTB;
the effective configuration differs only in its release suffix. The new
kernel contains the read-only binary attribute. The private RAM root changed
only its release gate. [Candidate receipt](results/candidate.json) pins the
checked LK boot container and full 16-MiB padded image SHA-256
`99d1f2db38ae01049aaa5346eb9c45d519dea675f8188db88ce9370b1f939430`.
No device installation or boot has occurred for this candidate.

The [guarded installer](install-passive.py) accepts only the preceding passive
boot2 checksum, uses the live GPT and project device guard, requires a matching
full readback, and then shuts down cleanly. The owner physically selects
boot2. The 900-second [watcher](watch-boot.py) pre-arms the direct USB route
and runs the [bounded private capture](capture-private.py) once when mainline
appears. After both reads are preserved, [the session collector](passive-host.py)
seals the complete log, runs the A53 regression and uses the reviewed return
to Gemian, checking that its boot ID matches the capture. A capture failure
preserves available evidence and requires diagnosis before any recovery step.
