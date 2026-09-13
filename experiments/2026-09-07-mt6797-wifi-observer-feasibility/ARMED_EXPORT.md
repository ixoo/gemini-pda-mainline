# Pre-armed maxcpus8 snapshot export

Status: `armed-1` stopped before collection. The subsequent owner-requested
`armed-2` selection completed with both collectors pre-armed: no attributed USB
terminal, retained host-request stop and confirmed changed-boot Gemian.
Queue items: `wifi-export-maxcpus8-armed-1` and `wifi-export-maxcpus8-armed-2`.
The primary integration coordinator was the sole device custodian; custody is
released. This record grants no WLAN
or capture-clear action.

## Question and fixed inputs

The [later maxcpus8 observation](BOOT_CPU_LIMIT.md#later-owner-selection) passed
the CPU0–7 preflight and reached host-request waiting. Its host receiver was
not armed, and no snapshot was exported. The distinguishing measurement now
is one requested snapshot, durable host save and bound acknowledgement, followed
by the matching retained `preserved` marker. Repeating the CPU check alone is
not the purpose of this session.

Reuse the exact [validated image](results/maxcpus8.json) and
[installation](results/maxcpus8-deployment-20260912.json), without rebuilding or
changing its startup effects. Padded SHA-256 remains
`d9334cba2f6ca5870d7004ecbf8c01b4e47b8004e00db3178f5098bdb4f6fb9d`;
session SHA-256 remains
`da877f7b2cfb49e9cd3c5d98fb03909d18047e35ea050cd4433cf1b22fb34779`.
The embedded cycle remains `54efed5a-f015-4a0e-bd83-f59a0fa31097`; this new host
session has separate evidence and must observe a new candidate boot UUID.

A fresh bounded query confirmed running Gemian boot
`db6b8120-0d47-4d05-9519-665e4aa74663`. The owner confirmed that the left USB-C
port is connected to this Mac. The [preparation receipt](results/armed-export-preparation-20260913.json)
pins the private tools and identity evidence. Any changed boot, source, image,
USB attribution or occupied output invalidates preparation.

## Confirmation and arming

The reviewed installer is rebound to that Gemian boot and a distinct receipt
name. Its additional check refuses any installed-image mismatch before staging
or writing. The matching path retains live-GPT resolution, inactive/non-root
device guard, exact size/writability, paired stable-power samples, full checksum,
independent 16 MiB readback and clean shutdown. No write or new backup is planned.
A mismatch selects investigation, not reinstallation. A focused inert-transport
test proves this refusal precedes staging, readback and shutdown; shell syntax,
full ShellCheck and inverse comparison to the reviewed source pass.

The receiver, USB watcher, return collector and classifier retain their reviewed
behavior. Only the preceding Gemian UUID and fixed evidence paths change;
inverse comparisons reproduce their exact original bytes. The validated private
package inventory, checksums, permissions and zero padding pass again.

After image confirmation and clean shutdown, save the pre-selection USB
inventory. Start both fresh collector invocations with exclusive output logs,
verify that both report armed and retain their process handles. Only then tell
the owner to select boot2. Do not spend an already armed window on publication
or installation. Do not arm until the owner is available for the physical step.

The USB watcher requires one newly enumerated, exact-descriptor USB parent and
its unique ACM child, as in the [original attribution protocol](EXPORT_SESSION.md#host-preparation-and-one-request).
It never chooses the first terminal or opens an ambiguous device. Its detection
window is 180 seconds; one selected receiver then has the existing 60-second
request/data/acknowledgement deadline. The independent Gemian collector has one
180-second return window and one bounded console payload read after changed-boot
identity. Native close and filesystem I/O retain their documented limits.

## One selection and result

Reuse the [export-return effects and stop conditions](EXPORT_RETURN.md#changed-startup-and-finite-effects):
one physical selection, at most 21 shell and eight Python records of at most
192 bytes, one immutable 65,536-byte snapshot read, one 52-byte request, one
65,624-byte frame and one 84-byte acknowledgement. Host readback and file/directory
sync precede the acknowledgement. Startup makes at most one normal return
request; the collector reads at most one 65,536-byte retained console payload.
No capture clear, WMT request, firmware load, WLAN cycle or alternate recovery
is included. All timeouts and pre-request refusals consume this host session.

A complete matching snapshot/receipt plus retained `outcome=preserved` and
changed-boot Gemian confirms the exchange. A saved snapshot without that marker
proves preservation only. An attributable stopped marker selects the next
correction. Missing USB, invalid framing, failed save or unconfirmed Gemian
preserves partial evidence and ends collection without a second request,
rearm or restart. Analyze captures privately in the RE VM. No result establishes
Wi-Fi support, coherent firmware teardown or clearing authorization.

Owner action: leave Gemian running during preparation. After the custodian
confirms both collectors are armed, select boot2 once with the left-port cable
connected. A normal return to Gemian is expected after the transfer or a caught
failure; do not make another selection while the result is being collected.

## Initial connection failure

The single confirmation invocation stopped before authentication with an SSH
connection timeout. Its [result](results/armed-export-preflight-20260913.json)
records no partition access, image verification, shutdown, collector invocation,
host exchange or console read. The prior Gemian identity is no longer a current
observation. Preserve the preparation and this failed attempt; establish present
device and transport state before a fresh admission. Do not rerun this session's
installer or collectors. The preparation sequence above is historical.

## Fresh collection using the verified installation

The owner then reported the PDA powered off and explicitly requested reusing
the previous verification and arming the collectors immediately. Session
`wifi-export-maxcpus8-armed-2` reused the existing verified image and deployment
receipt. No new pre-selection identity query, partition access, write or
shutdown was made.
The preceding Gemian binding remained the last authenticated boot `db6b8120…`;
its basis is that observation plus the owner's power-state report, without an
independently refreshed identity. The full identifiers and input digests are in
the [runtime result](results/armed-export-runtime-20260913.json).

The USB watcher and return collector were byte-identical to the reviewed tools,
in a fresh private directory. The classifier changed only its two evidence
paths; inverse byte comparison passed. A pre-selection USB inventory was saved,
both processes reported armed and their live handles were retained before the
owner was directed to select boot2 once. No collection window was spent on
installation or publication. One physical selection was reported.

The native candidate passed the CPU0–7 preflight, completed snapshot acquisition
and reached host-request waiting at `2.840765` kernel seconds. Its stopped stage
appeared at `62.902708`, followed by the matching return marker at `62.905521`
and a normal restart. The 60.061943-second wait and absent host request support
a request-timeout inference; the exception class is not retained. The fresh
candidate boot differs from the last authenticated and returned Gemian boots.

The host watcher completed its 180-second observation window without finding
an attributed ACM terminal. It invoked no receiver and sent no request or
acknowledgement. Before selection the host saw one `0e8d:20ff` MediaTek parent,
matching the inspected charging-mode descriptor pair; the final inventory had
no MediaTek or expected export parent. These two inventories cannot reconstruct
transient descriptors or uniquely identify the device. The retained console
contains none of the selected USB state/function tokens; missing tokens do not
prove missing controller events.

The return collector authenticated changed-boot Gemian and preserved one
65,524-byte console payload, SHA-256
`4ad71cf157fbc8279ef9deed31ccabd05da07bbade36b714a207d42e8d5a2985`.
Private RE-VM classification passed. No host snapshot was preserved; the normal
restart may have changed its original PMSG header. This result rules out an
unarmed host collector for this attempt and selects investigation of native USB
enumeration and host attribution before another physical selection. No repeat,
additional recovery, WLAN cycle or clearing action followed. Custody is released.
