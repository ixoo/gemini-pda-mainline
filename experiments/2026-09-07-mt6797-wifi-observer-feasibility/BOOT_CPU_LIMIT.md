# Native export diagnostic initial CPU limit

Status: correction and complete container validated; selected for publication,
guarded installation and one physical boot. No runtime result exists for this
new session. The preceding [HPS-off session](HPS_BOOT_POLICY.md#device-result)
is consumed and remains a CPU-online refusal.

## Cause boundary and correction

That boot observed HPS disabled and CPU0–4 online. Its early command line and
initial SMP log had already wrapped out of the retained console, so the exact
boot-limit cause remains an inference. The
[historical LK handoff](../../docs/hardware/gemini-gemian-baseline.md#boot-handoff-and-storage-boundary)
and the freshly checked source explain a narrow candidate correction.

At LK revision `f4988d74bb70a0a15d7f362f412afba7e7fcda46`, the non-FPGA
[default command line](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/platform/mt6797/include/platform/mt_reg_base.h)
ends in `maxcpus=5`. The pinned `mt_boot.c` appends the boot image's command
line afterward, then passes the resulting string as bootargs. Its append
function adds a space and the complete string, without removing repeated keys;
overflow of its 1,024-byte buffer is a refusal. No bootloader rewrite is needed.

The selected native kernel parses early arguments in order. Each `maxcpus`
handler calls `get_option()` with `setup_max_cpus`; a later nonzero value
replaces the earlier one. Linked ARM64 inspection confirms that destination
in the actual 47-patch kernel. `smp_prepare_cpus()` and `smp_init()` apply the
result to initial CPU activation. HPS later makes remaining CPUs present,
but its disabled hotplug algorithm does not supply the missing online CPUs.
The [receipt](results/maxcpus8.json) pins all inspected sources and binary input.

The [assembler](build-export-container.py) now appends `maxcpus=8` only for
`export-return`. [Startup](startup.py) requires exactly the ordered values
`5`, `8`, refuses `nosmp` and `nr_cpus`, then retains the HPS-zero and actual
CPU0–7 checks. Missing, reversed, repeated or additional limits refuse at
`boot-cpu-limit`. An eight-CPU argument never substitutes for the online mask.
The return path can preserve this new refusal stage without extra log records.

The changed hardware effect is initial native activation of A53 CPUs 5–7
before driver initialization, through the existing CPU-on implementation.
The kernel bytes, HPS default-off change, A72 refusal, PPM/EEM, idle policy,
frequency/voltage tables and recovery path remain as previously reviewed.
Startup makes no hotplug write. This remains a private native diagnostic;
neither a passed CPU check nor successful export demonstrates Wi-Fi support.

## Exact candidate and validation

Cycle `54efed5a-f015-4a0e-bd83-f59a0fa31097` reuses the Buildbox kernel from
`aa404d3e65fabff058269cde55631214ff0fb042`, SHA-256
`4fc02b373433bba5ca2ee8dc00990ea8698ad2d817ed7f7aa2e9fc7e08cda06b`.
The new filesystem has 723 members; only startup and session metadata change.
The compact runtime and private inputs match. Session SHA-256 is
`da877f7b2cfb49e9cd3c5d98fb03909d18047e35ea050cd4433cf1b22fb34779`.
The complete native container remains 16,300,032 bytes, with 477,184 bytes spare
in boot2. Padded SHA-256 is
`d9334cba2f6ca5870d7004ecbf8c01b4e47b8004e00db3178f5098bdb4f6fb9d`.

All 26 startup, five bridge and fourteen stream tests pass on the host. The
exact packaged ARM64 Python passes the startup and bridge tests with hardware
effects and restart injected. These include nine invalid argument sequences
and a five-CPU refusal despite correct arguments. Container reconstruction
matches exactly and rejects seventeen container and six input mutations.
Full fetched-package inventory/checksums, native header/load-address and
reserved-memory checks pass. No kernel rebuild or DT change was needed.

The private installer differs from the reviewed HPS installer only in five
exact identity substitutions; inverse comparison, shell syntax and ShellCheck
pass. Fresh inspection verified preceding Gemian boot
`0b7bd62b-20b3-4e28-aa9b-3ff92455678d` with systemd running. Publication and
hosted checks precede installation. The installer must recheck live GPT,
inactive non-root boot2, power, predecessor and full-partition readback, then
shut down cleanly. No fresh backup or alternative partition is selected.

## One physical session

Hypothesis: overriding the inherited five-CPU limit establishes CPU0–7 with
HPS disabled, allowing the unchanged export to reach its next stage. The
decision-changing observations are the exact argument preflight, actual online
mask, then either acknowledged export or the next attributable refusal.

Reuse the [export-return protocol](EXPORT_RETURN.md#changed-startup-and-finite-effects)
and all of its finite effects and recovery limits. There is one physical
selection, at most 21 shell and eight Python records of at most 192 bytes,
one immutable 65,536-byte snapshot read, one request/frame/acknowledgement
within the shared 60-second transport deadline, and one normal return request.
The host watcher and return collector each have 180-second windows; the latter
reads one retained console payload of at most 65,536 bytes. There is no capture
clear, WMT request, firmware load or WLAN cycle.

After verified installation and owner readiness, take the pre-selection USB
inventory and arm both exact-session collectors before requesting the physical
boot. The sole custodian preserves all outputs and verifies a changed-boot
Gemian return. A snapshot plus matching preserved marker passes export; a
snapshot alone proves preservation only. A caught refusal selects the next
correction. Missing attribution/return preserves uncertainty and does not
permit an unchanged retry or an alternate recovery action. Standing project
authorization covers this reviewed test; physical selection remains the owner
action.
