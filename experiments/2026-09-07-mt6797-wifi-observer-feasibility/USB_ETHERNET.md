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
The preceding ACM attempt remains recorded in its own evidence. The
[Ethernet session](USB_ETHERNET_SESSION.md) owns the replacement installation
and physical test.

The userspace change is one bounded capture transfer over the direct
USB IPv4 link at 10.15.19.82, using the existing request, digest, private save,
readback and preservation acknowledgement. It needs no interactive shell.
The existing PID1 capture checks, prohibition on other active interfaces and
normal return remain applicable. No Wi-Fi connection is used for export.

The explicit `export-tcp-return` action reads its immutable snapshot while all
interfaces are down. It requires the built-in g_ether, no Android gadget owner,
an inactive Ethernet `usb0` and disabled IPv4 forwarding. It disables IPv6 on
usb0 with one checked write, then runs the existing BusyBox `ip` twice: add the
fixed IPv4 address and bring up usb0. Each child has a five-second timeout; a
failure stops without retry. No DHCP, DNS or route configuration is used.
The runtime's network exception is enabled only after this setup and only for
this action: every other interface must stay down, IPv4 forwarding must remain
disabled and usb0 IPv6 must remain disabled. Other actions retain the original
all-interfaces-down check.

PID1 binds one TCP listener to both usb0 and `10.15.19.82:2323`. Accept, request,
the 65,624-byte frame and its 84-byte preservation reply share one 60-second
deadline. The listener closes after its first connection; no shell or second
client is served. Existing capture checks surround sending. Success retains
the accepted descriptor for the normal return; a caught failure closes it and
uses the same stopped-marker return. The existing limitations for blocked
kernel I/O, file synchronization and pre-PID1 failures still apply. TCP does
not authenticate or encrypt the private bytes; the host must attribute the
direct USB interface before connecting. No Wi-Fi or routed export is intended.

The full native link passed at `d037e48b3a09c6b9a02f0db2f1e44ca295af42ab`.
The [receipt](results/usb-ethernet-build.json) records all eleven verified
package files, exact configuration closure and gadget symbols. The inherited
69 section-mismatch count and native compiler's `-w` limitation remain.
Sixteen stream, twenty-eight startup and seven bridge tests passed on the host
and exact packaged ARM64 runtime. These include a real local TCP transfer and
acknowledgement, injected network setup/failure, and refusal of forwarding,
IPv6 or another active interface. No hardware effect occurs in those tests.

The [private candidate receipt](results/usb-ethernet-candidate.json) records the
assembled 16,220,160-byte boot container, with 557,056 bytes spare before exact
16 MiB padding. Its 723-member filesystem changes only the three transport and
startup sources plus session metadata. All runtime and retained input bytes
match the previous image. The native DTB is byte-identical. Independent parsing,
reassembly, seventeen container mutations and six input refusals passed.
The header supplies the previously used local USB MAC pair and the synthetic
serial `GEMINI_WIFI_EXPORT_TCP_1` for host attribution; neither identifies a
physical unit by itself.

Host collector preparation and guarded installation have now passed under the
[selected session](USB_ETHERNET_SESSION.md). Both collectors were armed before
the owner handoff. Hardware validation remains outstanding; its result must
distinguish Ethernet enumeration, connection, preserved bytes and confirmed
return to Gemian.
