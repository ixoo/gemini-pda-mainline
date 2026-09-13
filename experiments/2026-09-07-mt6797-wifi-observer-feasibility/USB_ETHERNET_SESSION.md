# One USB Ethernet capture and normal return

Status: installed with matching full readback and clean shutdown. Both collectors
were observed live before the owner was told to select boot2, then exhausted
their 600-second windows. The [window result](results/usb-ethernet-window-1.json)
records no USB inventory change, attributed Ethernet gadget, receiver invocation
or verified changed-boot Gemian return. Physical selection of this Ethernet
candidate has not been reported; this is not a confirmed failed boot. Both
collectors are stopped, and current device state awaits the owner report.
The [deployment receipt](results/usb-ethernet-deployment.json) retains the
installation and initial handoff. The
[candidate](results/usb-ethernet-candidate.json) is the independently validated
USB Ethernet image that replaces the preceding ACM image.
The [preparation receipt](results/usb-ethernet-session-preparation.json) binds
the current tools and preceding authenticated Gemian boot. Preparation,
installation and physical results are recorded separately.

## Hypothesis and decision

Replacing Android ACM with the native standard g_ether implementation can
provide the same USB network transport used by the validated mainline netcat
and SSH sessions. This tests a different gadget implementation on native MU3D;
it does not assume mainline MTU3 validation proves native enumeration.
The CPU policy, capture patches, runtime and byte-identical DT remain fixed.

One selection distinguishes these outcomes:

- A new attributed Ethernet gadget, direct host route, complete saved snapshot,
  matching acknowledgement, retained `outcome=preserved` and changed-boot Gemian
  demonstrate this export and return. Analyze the snapshot privately next.
- Ethernet enumeration without the expected host address/route identifies a
  host network prerequisite failure. The collector sends no capture request.
- No Ethernet enumeration leaves native controller readiness unresolved. The
  retained startup stage distinguishes failure before setup from an accept
  timeout; do not force a charging/role control or repeat unchanged inputs.
- A saved frame without its preserved marker establishes host preservation
  only. A stopped marker, partial files or silence retain the existing
  [export-return limitations](EXPORT_RETURN.md), including possible loss of the
  unretrieved snapshot when Gemian changes PMSG metadata.

Require the exact cycle and session digest. The frame's candidate boot must be
nonzero and different from preceding and returned Gemian boots. No result
authorizes clearing, a WLAN cycle or a Wi-Fi support claim.

## Finite effects and collectors

The [TCP implementation](USB_ETHERNET.md) retains one 65,536-byte immutable
snapshot read, one usb0 IPv6-disable write, two bounded BusyBox network commands,
one accepted connection, one request/frame/acknowledgement and one normal native
restart. The device exchange still has its 60-second deadline. There is no WMT
request, firmware load, calibration write or host-issued restart.

The [host collector](collect-ethernet.py) observes for at most 600 polls within a
600-second window; an in-flight local inventory may add at most three five-second
command timeouts. This longer arming window allows time for physical selection
without extending native execution. Each poll reads only host USB, interface
and route inventories. Descriptor/child changes are retained. It requires a new
single USB parent with VID/PID `0525:a4a2`, product `RNDIS/Ethernet Gadget`, and
synthetic serial `GEMINI_WIFI_EXPORT_TCP_1`, plus one descendant Ethernet
interface with the selected protocol MAC. These are attribution selectors, not
cryptographic device authentication.

The existing host route checker requires unique `10.15.19.1/24`, active carrier
and an unconflicted direct route to `10.15.19.82` on that same interface. The
saved Mac service already supplies that address for the fixed protocol MAC.
No host network modification, ping or exploratory connection is performed.
The collector then invokes the pinned receiver once, under a 70-second outer
limit. Its bounded TCP startup wait sends no application request until one
connection succeeds; request/data/acknowledgement are never replayed.

The existing Gemian return collector uses the same 600-second arming window,
the newly bound preceding boot, and otherwise unchanged identity/capture logic.
It polls the established Gemian LAN endpoint with at most one attempt per
five-second interval, then reads at most one 65,536-byte retained console after
verifying changed-boot Gemian. The console command has its existing 25-second
bound and before/after boot checks. Preserve private outputs and partial evidence
before deciding any further action. A timeout supplies no new boot or recovery
permission.

## Installation and handoff

The adapted existing installer changes only candidate/package identities,
evidence destination and preceding Gemian UUID. Inverse derivation exactly
reproduces its reviewed parent; Bash syntax and ShellCheck pass. Live GPT,
inactive/unmounted/non-root guards, size, writability, stable power, predecessor
checksum, sync/flush and full readback remain intact. A matching partition skips
the write. No fresh partition backup is made. Successful verification is
followed by clean shutdown, and the owner selects boot2 physically.

The primary integration coordinator is the sole device custodian. Standing
[project authorization](../../docs/SAFETY.md#standing-project-device-authorization)
covers this reviewed test and return. Before the owner handoff, retain the
installation receipt, arm both collectors and observe their live process
handles and readiness messages. Do not request boot2 while preparing them.
