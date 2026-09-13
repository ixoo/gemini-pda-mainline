# Reuse USB Ethernet for capture export

The owner requested reuse of the previously validated netcat or SSH connection
after the [pre-armed ACM export timed out](ARMED_EXPORT.md). The
[working mainline baseline](../2026-09-05-owner-away-experiment-preparation/baseline/BASELINE_AUDIT.md)
uses g_ether on a direct IPv4 USB link. Its original netcat shell and later
[authenticated SSH service](../2026-09-05-owner-away-experiment-preparation/baseline/DESIGN.md)
share that transport.

The native diagnostic instead inherited Android USB with standalone g_ether
disabled. ACM was selected to avoid a kernel configuration change, but its
enumeration and export had never been validated on this diagnostic. The capture
exchange itself already accepts a duplex byte stream. Keeping serial introduced
an unnecessary separate transport dependency.

The next build selects the existing native g_ether implementation with ECM and
RNDIS, matching the mainline gadget selection. Android USB is disabled so only
one gadget owns the controller. The source is the already pinned native kernel
revision in [full-kernel-inputs.json](full-kernel-inputs.json); no driver source
patch or controller/charging override is added. The exact configuration closure
and linked gadget functions are checked by the existing Buildbox builder.

This reuses the network method, but the native MU3D controller differs from
mainline MTU3. A successful build does not establish enumeration on this kernel.
The installed ACM image and its evidence remain unchanged.

The intended userspace change is one bounded capture transfer over the direct
USB IPv4 link at 10.15.19.82, using the existing request, digest, private save,
readback and preservation acknowledgement. It needs no interactive shell.
The existing PID1 capture checks, prohibition on other active interfaces and
normal return remain applicable. No Wi-Fi connection is used for export.

This is preparation: the new kernel link, TCP adaptation, private candidate
assembly and hardware test are outstanding. No new candidate is selected by
this record. The next physical test must have its host collector armed before
selection and distinguish Ethernet enumeration, connection, preserved bytes
and confirmed return to Gemian.
