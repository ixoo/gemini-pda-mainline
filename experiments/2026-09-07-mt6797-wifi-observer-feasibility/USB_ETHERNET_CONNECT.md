# Restore the diagnostic gadget connection

The [completed Ethernet session](USB_ETHERNET_SESSION.md) reached its TCP
listener but never appeared in the host USB inventory. Its retained console
contains 51 `connection_work` rate-limit summaries from kernel seconds 3.258328
through 63.258325, accounting for 356 suppressed callbacks. This is positive
evidence of the native readiness wait, not an inference from missing debug text.

At pinned native revision `59e00a9144d782e148332009a835b99c43382467`, the
selected `drivers/misc/mediatek/mu3d/drv/mt_usb.c` has exactly one rate-limit
call in `connection_work()`, inside `!is_usb_rdy()`. It reschedules after 100 ms
and returns before the device-role and cable checks. `lib/ratelimit.c` prints
the suppression summary independently of the MU3D debug mask, which disables
the accompanying `K_INFO` message. The selected configuration enables this
MU3D driver and disables `CONFIG_FPGA_EARLY_PORTING`.

The cause is in `drivers/usb/gadget/udc/udc-core.c`: this native tree comments
out `usb_gadget_connect()` after successful gadget bind and UDC start. Its
comment explains Android's later userspace-controlled connection. The
standalone g_ether configuration disables Android and supplies no replacement.
`usb0` registration and the TCP listener therefore succeed without enabling
the USB connection.

The exact tested ELF confirms that successful `udc_start` proceeds directly
to `kobject_uevent`, with no pullup call. Its `connection_work` instructions
call the rate limiter only on the false-readiness branch. The existing
`musb_gadget_pullup(..., 1)` sets the MU3D-local readiness flag through
`set_usb_rdy()`. This flag is distinct from similarly named PMIC/other USB
driver state. The [source and linked receipt](results/usb-ethernet-connect.json)
binds these observations to the tested kernel.

The four-line [native experiment patch](patches/usb-ethernet-connect/0001-usb-connect-the-native-diagnostic-Ethernet-gadget-after-bind.patch)
restores the existing post-bind connection only when the diagnostic and
Ethernet are enabled and Android is disabled. Failed bind or UDC start still
returns before it. Other configurations retain their previous behavior.
This is assistant-generated experimental code without DCO certification;
it is not an upstream submission.

The call uses the controller's existing pullup callback, including runtime
power references, soft connection, readiness, battery-worker wakeup and its
existing delayed connection work. Role and cable/charger policy still belong
to the native driver. No readiness assignment, forced role, charger override,
DT change, radio request or capture clear is added. This normal USB connection
is the missing effect required by the already scoped Ethernet export test.

The complete native build adds only this final patch to the existing 47-patch
sequence. The USB fragment, CPU policy and other inputs remain fixed; canonical
upstream series and profiles are unchanged. Patch application and strict Linux
7.1.3 Checkpatch pass, with sign-off checking disabled for this explicitly
non-certifying archive. The complete build passed at
`ef966869758e6f6b5751e36f0053ea935932efd8`; all eleven package files passed
remote and fetched verification. Configuration is byte-identical. The inherited
69 section mismatches and native compiler's `-w` limitation remain. RE VM
inspection confirms the added pullup call with argument one after successful
UDC start, its failure-path exclusion and the MU3D callback binding.

The corrected candidate tests whether this connection permits attributed USB
enumeration and the existing bounded, acknowledged capture transfer. Reuse the
[Ethernet protocol](USB_ETHERNET_SESSION.md) with a new cycle and exact build,
package and deployment identities. Arm both collectors before the owner's one
physical selection. A preserved snapshot plus retained preserved marker and
changed-boot Gemian completes export. If enumeration still fails, preserve the
console and distinguish readiness from later controller/cable policy before
another change. Absence of suppression messages alone will not prove readiness
or enumeration.

## Corrected session

The [candidate receipt](results/usb-ethernet-connect-candidate.json) records the
validated image, unchanged DT, and 723-member filesystem with only session
metadata changed. Independent reassembly and the existing seventeen container
mutations and six input refusals pass. The runtime and startup code are unchanged;
their prior ARM64 tests remain applicable.

The [session receipt](results/usb-ethernet-connect-session.json) binds cycle
`1070b099-11c0-4861-896f-7fd1fe6d9909`, the new image and both collectors to
verified Gemian boot `b2b6b2a3-2001-4ef0-a1c0-bc010f6ecfcf`. This session uses
the preceding Ethernet protocol's 60-second device exchange, 600-second host
arming windows and one console read after authenticated changed-boot return.
The original console is already preserved. No host network changes are needed.

The installer changes only the five identity/destination fields of its reviewed
parent; inverse derivation, Bash syntax and ShellCheck pass. Existing live-GPT,
boot/root identity, inactive/unmounted, size, power and full-readback checks are
retained. A successful installation ends with clean shutdown. The primary
coordinator holds sole device custody and must observe both collectors armed
before requesting the owner's one physical boot2 selection. The [deployment receipt](results/usb-ethernet-connect-deployment.json) now
confirms the live-GPT boot2 write, matching full readback and clean shutdown.
Both collectors were subsequently observed live before the owner handoff,
then exhausted their 600-second windows. The
[first window result](results/usb-ethernet-connect-window-1.json) records no USB
inventory change, receiver invocation, capture frame or verified changed-boot
Gemian return. No physical-start report had arrived during that window, so its
silence did not establish a failed boot. Hosted checks for the published
candidate record also passed.

## Physical test result

After the owner returned, both fresh collectors were armed before the reported
boot2 selection. The verified installation was retained without another write
or repeated preboot verification. The
[second window result](results/usb-ethernet-connect-window-2.json) binds the
corrected session to candidate boot `fda14d31-1e61-4c17-b06b-c44066dae46e` and
returned Gemian boot `258eff5c-a742-4379-89e7-60e885eaf797`.

The retained console records CPU0–7 preflight passing, snapshot and USB setup
entry, then the host-request wait from kernel seconds 3.161565 to 63.223507.
The 60.061942-second wait ended in one attributable `stopped` return marker,
followed by normal restart. No targeted fault token appeared after the marker.
The unchanged runtime reaches this wait only after checked interface setup,
device/address binding and listening; the stop is consistent with its accept
timeout, although the exception text was not retained.

No matching gadget appeared and no receiver, capture request or acknowledgement
ran. Host inventory changed once: one nonmatching USB device disappeared, with
no new or changed remaining entry. This removal has no attributed cause. After
authenticated changed-boot Gemian returned, the return collector saved one
65,524-byte console and completed. The exact Ethernet collector was then
stopped; no final inventory was taken. The snapshot was not exported, and
console preservation does not establish snapshot preservation.

The previous 51 readiness-loop suppression messages did not recur. This is a
changed observation, but absence alone cannot prove readiness or identify which
later branch ran. Existing debug filtering leaves the native role, charger and
cable decisions unobserved. Do not repeat the unchanged image or infer a cable
fault from host silence. The next useful measurement is bounded logging of
existing readiness, role and cable decisions, using already obtained values
without new hardware reads or policy overrides. The
[bounded diagnostic](USB_ETHERNET_DIAGNOSTICS.md) is now source-prepared;
compilation and candidate admission remain separate. This physical session is complete, its budget is
consumed, both collectors are stopped and device custody is released in Gemian.
