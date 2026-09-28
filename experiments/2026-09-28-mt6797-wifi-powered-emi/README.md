# Powered-CONN EMI range gate for the first WLAN load

The [mainline EMI census](../2026-09-27-mt6797-emi-range-census/results/runtime-1.json)
found regions 18, 19 and 23 empty, with twelve nonzero range words as a
same-boot secure-read control. That sample was taken while CONN was off. The
[guarded delayed-ID boot](../2026-09-28-mt6797-wifi-chip-id-delay/results/runtime-1.json)
subsequently proved one confirmed CONN ON transition and chip ID `0x0279`
after a requested 20-ms wait with CONMCU reset held. It did not read the EMI
ranges in that powered state.

The `mt6797-a53-wifi-powered-emi` profile extends that exact powered sequence
with one read-only snapshot after chip-ID success. It rechecks the modern
domain's ON status and held reset before and after the secure reads. It reads
region 23's range twice around region 1's range and the region-18/19 range
and policy words. Region 1 is a same-boot control because it was nonzero in
the prior authenticated census. The region-23 policy word is also logged, but
the retained read-service audit identifies that offset as a cached value;
only the two direct range reads are used to assess overlap. No EMI write,
remap, reset release, firmware transfer, radio or DMA action is added.

The hypothesis is that region 23 remains empty while CONN is powered, making
a **future same-boot check** of that condition a useful admission gate for a
first WLAN image load. A nonzero or moving region-23 range redirects work to
overlap ownership before any EMI write. A zero region-1 control makes the
readout inconclusive. Failure to reach `0x0279` or to retain ON/held-reset
status produces no EMI snapshot and redirects power/clock diagnosis. Even an
all-zero region-18/19/23 snapshot does not establish writer exclusion,
effective master-domain routing, firmware memory access, or permission to
program region 18. This candidate must not be replayed without a new
decision-changing measurement.

The incremental [format-patch](../../patches/proposals/0039-soc-mediatek-sample-powered-MT6797-EMI-ranges.patch)
has synthetic non-certifying authorship and is not an upstream submission.
The clean pushed commit `f0d0142aef65c917d6964828f1416d4d7fd335c0`
built with `KERNEL_PROFILE=mt6797-a53-wifi-powered-emi
./scripts/build-kernel --backend buildbox`. The validated package digest is
`cf3266d52411b1d51ad71248c872fcb84146ce59c762ab3576091146e36ab0ad`.
The [sanitized candidate receipt](results/candidate.json) pins the private
boot2 image and its predecessor. Assembly reused the exact boot-tested board
DTB and firmware from the delayed-ID boot; the generic compiled DTB was not
substituted. Offline candidate validation and installer generation passed,
including `bash -n` and ShellCheck on the generated installer.

The [first attempt](results/attempt-1.json) installed that image to boot2
through the live-GPT guard, matched the full-partition readback, and shut down
cleanly. A 900-second host watch then saw preloader and MediaTek `20ff`, but
never saw the mainline USB route; the Gemian LAN endpoint was also unreachable
at timeout. The watch made no device SSH attempt. Owner confirmation of physical
boot2 selection and screen state is still pending. There is no mainline boot ID,
kernel log, EMI result, A53 regression result or verified Gemian return for
this attempt. Do not treat the timeout as a failed EMI check or replay the
same image without a decision-changing observation. Private firmware and logs
stay under ignored `artifacts/`.

Because an earlier EMI-census boot exposed its mainline gadget after a
900-second watch expired, one additional [host-only watch](results/late-watch-1.json)
was armed on the existing `20ff` session without requesting another boot or
device action. It saw no transition or mainline route for another 900 seconds;
the USB session ID remained unchanged and Gemian LAN still timed out. The
screen state and physical boot2 selection remain unconfirmed, so this is a
host-route limit, not proof of a kernel failure. An independent image
comparison found the boot-tested board DTB unchanged and only the expected
release-string replacement in the RAM root. Another identical host watch
would not resolve the boot boundary; the next observation must establish the
PDA's physical state or a changed authenticated boot.

## Confirmed boot2 selection and powered result

The owner confirmed the PDA was powered off while the unchanged `20ff` USB
session was present. After the next collector was armed, the owner physically
selected boot2. Its mainline gadget appeared 14 seconds after arming and the
authenticated [runtime result](results/runtime-1.json) bound the installed
candidate to changed boot ID `ea1ef07f-8e63-4926-91ca-0dde769b264f`.
The complete sealed kernel log contains one confirmed-CONN-ON record with
CONMCU reset held, chip ID zero immediately and `0x0279` after the requested
20-ms delay. In that same powered state, region 1's range read returned
`0x44604460`; region-23 range reads before and after the 18/19 reads returned
zero, as did the 18/19 range and policy reads. Region-23 policy logged zero
but its retained read-service path is cached, so it is not a direct policy
register control. The four-section firmware plan was accepted but execution
remained held. The A53 RAM-service regression passed, the reviewed return
reached a changed Gemian boot, and an independent Gemian read found WLAN
carrier 1.

This establishes a positive-controlled, powered **point-in-time** empty-range
observation and validates the read-only gate premise for one boot. A future
first load must repeat the gate in its own boot immediately before effects,
exclude conflicting writers for the effect lifetime, and choose a safe
CONSYS/AP protection-domain policy. This result does not establish region
priority, effective master-domain routing, permission to write EMI policy,
firmware execution or usable mainline Wi-Fi.
