# Gemian Wi-Fi reference kernel

Status: full Buildbox kernel link and offline boot2 container review passed. No
device execution has yet validated this kernel.

The known-good Gemian 3.18 kernel brings up the MT6797 Wi-Fi hardware. Its
normal console output does not establish which CONSYS clock mode was selected
or whether the region-18/19/23 secure EMI protection requests succeeded. Those
are decision-changing inputs for the mainline shared-owner design. This
experiment builds a reusable Gemian reference kernel from public source commit
`59e00a9144d782e148332009a835b99c43382467`, the hash-pinned live Gemian
configuration, and the same pinned GCC 6.3 toolchain used by the established
Gemian Buildbox lane. The tracked [patch](patches/0001-diagnostic-record-Gemian-Wi-Fi-setup-decisions.patch)
records the co-clock argument at WMT initialization and CONSYS register
control, plus the arguments and raw secure-call result of selected EMI MPU
requests. It preserves the wrapper's return behavior and adds no register,
radio or firmware operation. Tracing is compiled in but disabled by default;
function and function-graph tracing may be enabled only during a later bounded
diagnostic session.

The first boot hypothesis is that the working Gemian stack will execute these
paths and provide an attributable clock-mode choice and EMI request/result
record. Unique evidence is one complete kernel log, the exact boot2 image
checksum, kernel release and changed boot ID, along with Wi-Fi link state.
If all records appear and Wi-Fi works, compare the recorded setup with the
mainline cold handoff before designing its owner. If Wi-Fi works but records
are absent, the compiled functions are not proved to be the active setup path;
use bounded function tracing or inspect the alternate caller. If the image
fails to boot or Wi-Fi regresses, preserve available evidence and return to the
known-good boot; do not repeat the same image without a new measurement. A
secure-call success establishes only the observed call result, not exclusive
ownership or a safe mainline power-on sequence.

Build only from a clean pushed project commit with
`./scripts/buildbox build-gemian-wifi-reference`, then fetch with
`./scripts/buildbox fetch-gemian-wifi-reference`. The validated bundle is
ignored under `artifacts/buildbox/<commit>/` and contains `Image.gz-dtb`,
`vmlinux`, `System.map`, final config, logs and SHA-256 inventory. The bundle
alone is not a boot image. A boot2 candidate requires separate offline Android
container assembly from the hash-pinned known-good Gemian boot image, exact
partition padding and review. Install only from verified Gemian through the
reviewed live-GPT boot2 guard and full readback, then shut down cleanly; the
owner selects boot2 physically. Primary boot is never a target.

Buildbox linked project commit `bf079c8be55e623b9fb5bc0e51a6a3feaed55f94`.
The [build receipt](results/build.json) pins the exact bundle inventory and
kernel field. The final config has function, function-graph and dynamic ftrace
enabled, with MTK default tracing disabled. The sole diagnostic is the same
69-section-mismatch modpost warning present in prior baseline builds. The
8.2 MiB kernel field contains release `3.18.41-gemini-wifi-ref+` and the
three diagnostic call sites are linked.

The [candidate recipe](build-candidate.py) reuses the hash-pinned Android-v0
assembler and known-good Gemian boot input, changing only the kernel field.
The [offline candidate receipt](results/candidate.json) records the unchanged
ramdisk checksum, 14,995,456-byte raw image and exact 16 MiB padded image.
The padded image SHA-256 is
`138e35e41fa12a3a0cdeca3660e42e291b5268814167c2857a7ad67cffe594b2`.
The private image stays ignored under `artifacts/gemian-wifi-reference/`.
The [installer preparation](prepare-installer.py) pins the reviewed guard and
installer derivation, the image inventory, and the expected predecessor
checksum. It generates a private shell script that rechecks the live GPT,
root/target device identity, power and full readback before clean shutdown.
