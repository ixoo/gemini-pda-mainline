# Bounded delayed MT6797 CONSYS chip-ID probe

The [first powered chip-ID read](../2026-09-28-mt6797-wifi-chip-id-probe/results/runtime-1.json)
returned zero after 30 µs while the CONN domain was confirmed ON and CONMCU
reset stayed asserted. The selected Gemian source retries misses at 20-ms
intervals, so that single sample does not establish a persistent zero.

The named `mt6797-a53-wifi-chip-id-delay` profile keeps the prior isolated
power and chip-ID probe. Its incremental [patch](../../patches/proposals/0038-soc-mediatek-bound-delayed-MT6797-CONSYS-chip-id.patch)
takes at most two additional read-only samples after 20 and 40 ms, stopping
early on `0x0279`. It confirms dual-status CONN ON and held CONMCU reset before
each read. It does not release reset, write the CONSYS window, execute
firmware, operate the radio or power off. The synthetic patch author is not
DCO-certified.

Before boot, require a clean pushed Buildbox build, exact package and boot2
candidate validation, guarded live-GPT installation with full readback, and a
fresh finite collector. The hypothesis is that one delayed sample returns
`0x0279`, identifying a settling window. A persistent zero at 40 ms directs
the next diagnosis to clock, bus-protection and power-control readback without
permitting reset release. An ON/reset recheck failure stops further MMIO;
a bus fault preserves available evidence and uses reviewed Gemian recovery.
Any unexpected ID also stops progression. None of these outcomes alone
demonstrates firmware execution or working Wi-Fi. Do not repeat this exact
candidate without a new decision-changing measurement.

## Prepared candidate

The clean Buildbox build of pushed commit
`4de4921dc919ee2e23291e162c6464937b085a60` produced validated package
`53e534c4b6c7893775dd7bd32504019d9fc94adbf575d88f5d775d73ec66e8ba`
with release `7.1.3-gemini-a53-wifi-chip-id-delay`. The compiled Gemini DTB is
byte-identical to the preceding validated profile; the private boot container
retains the exact boot-tested chip-ID board DTB. The
[checksum-only candidate receipt](results/candidate.json) pins the package,
parent boot image, private 52-member RAM root and full boot2 padding. Its
full 16-MiB boot2 SHA-256 is
`f218eaf4837a8e6025927b5d10425e4f2fb0de86259d49bdc6aefe484781feb1`.
Private firmware and image bytes remain ignored. The guarded installer passed
offline generation, shell syntax and ShellCheck with the preceding chip-ID
image pinned as its only predecessor. Synthetic classifier checks accepted
20-ms and 40-ms `0x0279` traces, classified a three-sample zero trace as a
valid negative result, and rejected a missing delayed sample. No device
action or delayed-ID hardware observation is claimed by these checks.

## Hardware result

The guarded boot2 installer matched the full-partition readback and shut the
PDA down. The owner selected boot2. In changed mainline boot
`95af79c4-c3ee-4cb7-9ebc-870da332b880`, the complete sealed kernel log
recorded one confirmed CONN power-on with CONMCU reset held, chip ID
`0x00000000` at the first read, then `0x00000279` after the requested 20-ms
sleep. The probe stopped there; no 40-ms sample was needed. The four-section
firmware plan passed without executing firmware. The A53 RAM-service
regression passed. Reviewed recovery reached changed Gemian boot
`9e57b63b-13de-42b4-8b90-e8c57cd371d7`, and an independent bounded read
found `wlan0` carrier 1. The [sanitized runtime receipt](results/runtime-1.json)
pins candidate, boot identities and complete private-log checksum.

The USB watcher found the mainline route but its first collector launch used
a relative candidate path under a different working directory and refused
before device action. The same authenticated collector was immediately
launched with the absolute path in that mainline boot, preserving the complete
log and completing recovery. The shared watcher now resolves the candidate
path before changing directories. No repeated boot was used.

The contrast between the initial zero and delayed `0x0279` supports settling
in this boot. It does not establish a minimum delay or repeatability. No
CONMCU reset release, firmware execution, EMI handoff or Wi-Fi operation was
tested; those require separate resource-ownership and runtime evidence.
