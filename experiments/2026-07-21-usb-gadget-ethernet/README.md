# Experiment: USB gadget Ethernet serviceability

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-21-usb-gadget-ethernet` |
| Status | `running`: built, validated, and installed; attended runtime pending |
| Subsystem | MT6797 MTU3/T-PHY, legacy `g_ether`, IPv4, early userspace |
| Device variant | Current named Gemini PDA unit; exact retail sub-variant not independently established |
| Date(s) | 2026-07-21 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

Can an initramfs-only derivative of exact hardware-passed Candidate AB make its
already built-in USB gadget Ethernet path usable at a fixed address, while
preserving AB's working local console, keyboard map, and kernel-native reboot?

The falsifiable hypothesis is that exact AB already reaches a usable `usb0`
network device and only lacks userspace configuration. Candidate AC will wait
at most 30 seconds for `usb0`, configure `10.15.19.82/24`, and expose a unique
marker followed by an interactive shell on TCP port 2323. A directly attached
macOS host at `10.15.19.1/24` must then pass the following independently
observable gates in order: exact USB identity, fixed-MAC host interface,
carrier, ping, exact AC marker, shell command/response, and preserved reboot.

This is not a new kernel-support claim. Retained Candidate M/N pstore already
shows that the exact inherited T-PHY and MTU3 probes returned zero, the forced
B-device session ran, `g_ether` reported ready with the fixed MAC pair, and
MTU3 logged its gadget pull-up action. Those kernel messages do not prove an
electrical pull-up, host enumeration, carrier, or packet transfer. Candidate
AB separately passed its local console, keyboard, idle, and kernel-restart
gates once, but deliberately recorded `runtime_networking=none`.

## Provenance and environment

- Kernel release: `7.1.3-gemini-observability-L`.
- Kernel patchset SHA-256:
  `efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93`.
- Patch-series SHA-256:
  `124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a`
  (88 entries through patch 0087).
- Resolved configuration SHA-256:
  `0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74`.
- Exact Candidate AB artifact:
  `candidate-AB-mt6797-kernel-restart-final-61c74592`.
- Candidate AB artifact-manifest SHA-256:
  `f7500569b83cf36e2bfcb0c7db3cef33a3c3776e85615c5719acf64e6f2accb0`.
- Candidate AB raw boot-image SHA-256:
  `61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446`.
- Candidate AB full 16 MiB partition SHA-256:
  `b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
- Exact inherited `Image.gz` SHA-256:
  `37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f`.
- Exact inherited final DTB SHA-256:
  `bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f`.
- Exact inherited AB initramfs SHA-256:
  `b57dc3143e7ca7df90d742bcacc692221b4d7b6d346e5192d7bc68acaac00ea7`.
- Exact inherited console-map SHA-256:
  `02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c`.
- Exact inherited static BusyBox SHA-256:
  `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`.
  Direct execution in the AArch64 recovery VM confirms its `ip`, `nc`, and
  `ping` applets; `nc` supports persistent
  `-ll -p PORT -e PROGRAM` service but has no listen-address option.
- Toolchain: GCC
  `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0` and GNU ld 2.42, inherited
  from AB. AC does not rebuild the kernel.
- Boot path: Android boot image version 0 through the retained Planet LK,
  manually selected from logical `boot2`. The live GPT must resolve `boot2`
  for every installation; no partition number is assumed.
- Kernel USB identity remains exact AB because `CONFIG_CMDLINE_FORCE=y`:
  product `Gemini-L-Observability`, serial
  `GEMINI_OBSERVABILITY_20260717_L`, host MAC `42:00:15:19:82:00`, and device
  MAC `42:00:15:19:82:01`.
- Prior local evidence:
  [`Candidate AB runtime`](../2026-07-20-mt6797-kernel-restart-diagnostic/results/runtime-candidate-ab-attempt-1-20260721.txt)
  and
  [`retained MTU3/g_ether evidence`](../2026-07-16-usb-gadget-diagnostic/results/retained-pstore-mtu3-gadget-evidence-20260718.txt).

The inherited USB descriptor identifies the exact AB kernel path, not AC
userspace. The unique AC attribution must come from
`GEMINI_USB_GADGET_ETHERNET_20260721_AC` in pstore, `/run/ac-status`, and the
TCP service banner.

## Safety assessment

Candidate AC keeps exact AB's storage-disabled kernel and initramfs policy. It
must not enable or access MMC, MTD, SCSI, ATA, USB mass storage, ConfigFS,
another gadget function, another network-device family, host or dual-role USB,
VBUS control, Type-C policy, charging, IPv6, DHCP, a default route, forwarding,
bridging, NAT, or Internet sharing. It opens no block device, discovers no
partition, mounts no persistent filesystem, and invokes no sync operation.

The TCP service is deliberately an unauthenticated root shell. BusyBox `nc`
cannot bind the listener to one local address, so `nc -ll` listens on all
configured local addresses. This is acceptable for this bounded experiment
only because the exact kernel exposes no other external network-device family
and the host is connected directly over the single `usb0` link. Use a trusted
host and known data cable. Never bridge this interface, enable Internet
Sharing, or attach it to an untrusted system. The listener remains available
until reboot so a disconnected diagnostic session can be re-established.

AC preserves AB's exact `/bin/reboot`, reboot-dispatch environment, local
shell, `x-record`, and no-userspace-watchdog policy. No AC process may open,
ping, configure, or otherwise own `/dev/watchdog0`; no timeout may reset the
device. Failure to find or configure `usb0` ends only the background network
worker. The local tty1 shell remains available, and only an owner-typed bare
`reboot` may request the already proven kernel restart path.

Candidate generation is filesystem-only and has no device interface.
Installing to `boot2` is state-changing and may occur only through the
repository's guarded procedure: exact live GPT identity, non-active and
unmounted target, stable power, mode-0600 full backup, size check, exact
padding, one synchronized write, flush, and matching full-partition readback.
The expected predecessor is exact padded AB
`b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350`.
Any mismatch defers the write. Primary `boot`, `boot3`, preloader, NVRAM, GPT,
and whole-device writes remain outside scope. Installation never selects a
boot target and never reboots automatically.

Stop immediately after unexpected heat, a battery or charging anomaly, an
automatic reset, a console/keyboard/reboot regression, storage discovery or
I/O, an unexpected host route or interface, an uncertain physical port or
cable, a non-AB `boot2` predecessor, or any failed write/readback check. Return
to the known-good OS using the established manual selection/recovery path.

## Associated code

The planned implementation is confined to this experiment and exact AB
inputs:

- `initramfs/init`: an audited transform of exact AB `/init`; it launches the
  USB network worker without blocking PID 1 or tty1.
- `initramfs/ac-record`: AC-specific `/run/ac-status`, `/dev/kmsg`, and serial
  attribution. It does not write tty1.
- `initramfs/usb-net`: bounded `usb0` discovery, fixed-address setup, state
  recording, and persistent TCP listener.
- `initramfs/usb-shell`: unique banner, reboot-alias self-check, and remote
  interactive shell.
- `bin/ip`, `bin/nc`, and `bin/ping` archive symlinks: exact links to the
  inherited static `/bin/busybox`.
- `scripts/build-initramfs.sh`, `validate-initramfs.py`, and
  `test-initramfs-mutations.py`: deterministic construction, exact archive
  delta validation, direct BusyBox applet execution, and 13 focused mutation
  cases.
- `scripts/build-candidate-ac.sh`, `validate-boot.py`,
  `validate-final-artifact.py`, and `test-container-mutations.py`: two-copy
  Android-v0 construction, exact inherited payload validation, 32 LK gates,
  complete artifact replay, and six coherent container mutations.
- `scripts/derive-installer.py`, `calibrate-installer.py`,
  `install-candidate-ac-boot2.sh.in`, and `test-installer-static.py`: exact AB
  predecessor derivation and the calibrated guarded live-GPT installer.

The only permitted archive delta is changed `init` plus new `ac-record`,
`usb-net`, `usb-shell`, and the three BusyBox symlinks. Exact AB
`local-shell`, `reboot`, `x-record`, `x-probe`, `inittab`, BusyBox, keymap,
console helpers, and input helper remain byte- and metadata-identical.

Building requires the AArch64 recovery VM but no elevated host privilege or
hardware access. The guarded installer requires authenticated device SSH and
passwordless device sudo. The macOS test temporarily adds one host IPv4 alias
with host sudo, then removes it explicitly.

## Procedure

### Preboot decision statement

Before any device boot, record this exact hypothesis and decision tree:

- Kernel, DTB, gadget identity, console, keyboard map, and reboot remain exact
  hardware-passed AB; the only boot-critical variable is AC early userspace.
- The inherited descriptor is kernel attribution. The exact AC marker is the
  independent `/init` attribution path.
- A local AB console plus AC marker but no `usb0` isolates failure before
  userspace interface configuration. A configured `usb0` without a host
  descriptor isolates the host/cable/port/electrical/configuration boundary.
  Later ordered gates refine the boundary further.
- A console, keyboard, idle, or reboot regression rejects AC even if USB
  networking succeeds. Restore exact AB rather than adding a workaround.
- Do not repeat an identical candidate unless the next attempt adds a new
  decision-changing observation, such as a separately proven cable/port or an
  alternate host driver.

### Construction and static validation

1. Require the exact Candidate AB directory and re-run its final validator.
   Reject any identity, manifest, mode, inventory, package, or repository
   provenance mismatch.
2. Reconstruct AB's canonical initramfs, replace only `/init`, add the three AC
   scripts and three BusyBox symlinks, normalize all archive ownership and
   timestamps, and serialize deterministically.
3. In the recovery VM, execute the exact BusyBox to prove `ip`, `nc`, and
   `ping` applet availability and the required `nc -ll -p PORT -e PROGRAM`
   contract. A symlink alone is not an applet-availability proof.
4. Require exact device address `10.15.19.82/24`, exact TCP port 2323, exact
   marker, exact `usb0` name, a 30-second interface wait, and worker exit on
   failure. Require `nc -ll -p 2323 -e /bin/usb-shell` exactly once.
5. Require the remote shell to export the exact AB dispatch environment and
   withhold the shell unless `type reboot` resolves to exact `/bin/reboot`.
6. Reject DHCP, route creation, forwarding, bridging, NAT, IPv6, DNS, another
   listener, another interface, storage access, sync, watchdog access,
   automatic reboot, reboot fallback, and any inherited AB-member change.
7. Exercise coherent semantic mutations, including altered baseline hashes,
   inherited scripts, address/prefix, interface, port, marker, wait bound,
   listener flags, reboot dispatch, watchdog/storage tokens, extra archive
   members, symlink targets, and rewritten checksum manifests. Every mutation
   must be rejected for its semantic cause.
8. Build the initramfs and complete Android-v0 candidate twice in independent
   directories. Require recursively identical files and modes, exact inherited
   kernel and DTB segments, all 32 LK gates, canonical headers, and matching
   independent host/VM hashes.
9. Calibrate and statically test the guarded installer against exact padded AB.
   Resolve logical `boot2` from the live GPT, perform the guarded backup/write/
   flush/readback sequence, record all hashes, and do not reboot.

### Attended device and macOS test

The first AC image receives one attended attempt. Stop at the first missing
gate rather than continuing later probes.

1. Use a known data-capable cable directly between the macOS host and the
   documented Gemini gadget port. Disconnect any UART cable from that port.
   Do not enable Internet Sharing, bridging, or another host address on the AC
   subnet.
2. Before manually selecting `boot2`, save the existing interface list and
   begin watching for the exact inherited USB serial:

   ```sh
   BASE_IFACES="$(ifconfig -l)"
   ioreg -p IOUSB -w0 -l | grep -F GEMINI_OBSERVABILITY_20260717_L
   ```

   Enumeration is gate 1. Record the observed USB product, serial, and time;
   do not treat it as AC `/init` evidence.
3. Manually boot logical `boot2`. Confirm the unchanged local console reaches
   `GEMINI-AB#`, the exact keymap still works, and no automatic reboot or
   countdown occurs. From the local shell, `cat /run/ac-status` must show the
   exact AC marker, bounded `usb0` result, address result, and listener result.
4. Find the host interface by its exact locally administered MAC rather than
   guessing `enN`:

   ```sh
   find_gemini_if() {
     for interface in $(ifconfig -l); do
       mac=$(ifconfig "$interface" 2>/dev/null |
         awk '/^[[:space:]]*ether / {print tolower($2); exit}')
       case "$mac" in
         42:00:15:19:82:00) printf '%s\n' "$interface"; return ;;
       esac
     done
   }
   IFACE=$(find_gemini_if)
   test -n "$IFACE"
   ```

   The exact fixed-MAC interface is gate 2. If it is absent, compare against
   `$BASE_IFACES`, record the first missing gate, and stop without modifying a
   different interface.
5. Configure only the resolved direct interface and inspect its status:

   ```sh
   sudo ifconfig "$IFACE" up
   sudo ifconfig "$IFACE" alias 10.15.19.1 netmask 255.255.255.0
   ifconfig "$IFACE"
   ```

   Active carrier is gate 3. Do not add a gateway or DNS server.
6. Bind the probe to the direct interface and source address:

   ```sh
   ping -b "$IFACE" -S 10.15.19.1 -c 3 -W 2000 10.15.19.82
   ```

   Successful fixed-address ICMP is gate 4 and the first packet-transfer
   evidence. If it fails, do not attempt TCP.
7. Connect to the diagnostic service:

   ```sh
   nc -4 -b "$IFACE" -s 10.15.19.1 10.15.19.82 2323
   ```

   The first service output must include
   `GEMINI_USB_GADGET_ETHERNET_20260721_AC`; that exact banner is gate 5 and
   proves AC `/init` plus TCP service, unlike enumeration alone.
8. At the remote prompt, run these bounded checks:

   ```sh
   uname -r
   printf '%s\n' GEMINI_AC_COMMAND_OK
   cat /run/ac-status
   type reboot
   ```

   Require exact kernel release `7.1.3-gemini-observability-L`, the exact
   command token, AC status, and `reboot is an alias for /bin/reboot`. This is
   gate 6. Do not inspect block devices or change kernel state.
9. Wait until at least 45 seconds after boot with no automatic reset, then type
   bare `reboot` from the remote shell. The TCP connection should drop
   immediately, the device should reset without a countdown, and Gemian should
   return. This is gate 7 and the AC regression check for exact AB reboot.
10. After return, remove the temporary host address if the interface persists:

    ```sh
    sudo ifconfig "$IFACE" -alias 10.15.19.1
    ```

11. Collect retained pstore and changed-boot-ID evidence read-only. Preserve
    exact AC entry, `usb0`, address, listener, session, and reboot attribution;
    redact personal identifiers. Never remove remote pstore records.

## Observations

Candidate AC was built twice cleanly in the AArch64 recovery VM after a
pre-selection builder-cleanup defect was found and fixed. Authoritative builds
3 and 4 are recursively byte- and mode-identical and contain no private
construction workdirs. Both produce the 7,378,944-byte boot image SHA-256
`3491c119d19b7b0af2ac2342659648227182ead0e32bb4c39a66fa22cadfb39d`;
the AC initramfs SHA-256 is
`166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3`.
The exact AB `Image.gz`, DTB, keymap, local shell, and reboot path are retained.
ShellCheck passed, the initramfs suite rejected 13/13 mutations, the container
suite rejected 6/6 coherent mutations, all 32 LK gates passed, and both final
validator outputs are identical. See the
[build result](results/build-validation-ac-20260721.txt) and
[installer result](results/installer-validation-ac-20260721.txt).

The calibrated installer then resolved live-GPT logical `boot2` as the
unmounted `/dev/mmcblk0p30` while the known-good OS remained rooted on
`/dev/mmcblk0p29`. It required exact padded AB, preserved a private mode-0600
full backup, wrote only `boot2`, synchronized and flushed it, and obtained an
exact full local/remote readback at padded SHA-256
`318f418a5e67042ecdd1c98a8767c104c8cfc68c3d56cd7c0d13cb3c5fad8a84`.
It did not reboot or select a slot. See the
[write/readback result](results/boot2-write-candidate-ac-20260721.txt).

In attended attempt 1, the owner reported AC booted and directly connected to
the Mac. macOS observed exact inherited product `Gemini-L-Observability`, exact
serial `GEMINI_OBSERVABILITY_20260717_L`, and fixed host MAC
`42:00:15:19:82:00` on active `en7` at 100baseTX full duplex. After adding only
`10.15.19.1/24`, the route to `10.15.19.82` resolved to `en7` and three sourced
pings returned with zero loss and 0.483 ms average RTT.

The first TCP session printed exact marker
`GEMINI_USB_GADGET_ETHERNET_20260721_AC`, reported `usb0` carrier 1 and UDC
`11271000.usb` state `configured`, returned exact kernel release
`7.1.3-gemini-observability-L` and token `GEMINI_AC_COMMAND_OK`, and resolved
bare `reboot` to the exact inherited `/bin/reboot`. A second connection at
250.35 seconds uptime returned `GEMINI_AC_RECONNECT_OK`, confirming the
persistent listener and no preceding automatic reboot. Physical console and
keyboard preservation await the owner's report; native reboot has not been
invoked without explicit authorization. See the partial
[runtime result](results/runtime-candidate-ac-attempt-1-20260721.txt).

## Analysis

Interpret one attempted boot at the first missing ordered gate:

| Observation | Narrow interpretation and next action |
| --- | --- |
| Local console or exact AB keymap regresses | Reject AC as an initramfs integration regression; restore AB and inspect only the AC archive delta. |
| AB console works but exact AC marker is absent | AC `/init` execution or attribution is unproven; do not infer USB behavior from kernel logs. |
| AC marker survives but `usb0` is absent after 30 seconds | Failure is before userspace address setup; inspect retained T-PHY/MTU3/`g_ether` and netdev evidence without repeating registration-only probes. |
| `usb0` and address setup pass but the exact USB identity is absent on the host | The observable boundary remains descriptor enumeration; verify the recorded physical port and known-data cable before changing software. |
| USB identity appears but the fixed-MAC host interface does not | Isolate host ECM/RNDIS binding or USB configuration selection; do not claim carrier or IP failure. |
| Fixed-MAC interface appears but carrier is inactive | Isolate the selected USB configuration/link boundary; do not attempt or interpret ping. |
| Carrier is active but ping fails | Isolate fixed-address configuration, source-interface selection, or ICMP transfer; record host routes and both interface states without adding a gateway. |
| Ping passes but the AC TCP marker is absent | Kernel gadget and IPv4 passed; isolate listener startup, TCP, or `nc -e` execution. |
| AC marker appears but command/response fails | TCP and AC `/init` passed; isolate remote-shell stdin/stdout or dispatch setup. |
| Marker and command/response pass but reboot regresses | USB serviceability passes, but AC as a whole is rejected for breaking the exact AB recovery path. |
| All seven gates pass | Confirm USB gadget Ethernet serviceability once for this exact image, host, cable, port, and named unit; do not infer hotplug repeatability, another host OS, host mode, Type-C, VBUS, charging, or production security. |

`g_ether ready`, the fixed MAC logs, and MTU3's software pull-up line remain
corroborating kernel evidence only. The inherited USB serial is stronger host
enumeration evidence but still does not prove AC `/init`; the AC TCP banner is
the required userspace discriminator.

## Conclusion

`confirmed in part`: USB gadget Ethernet serviceability is confirmed once for
this exact Candidate AC, named unit, Mac, direct port, and cable through host
enumeration, fixed-MAC interface, active carrier, IPv4 packets, exact AC TCP
marker, command response, and persistent reconnect. The complete hypothesis
remains open until physical console/keyboard preservation and the exact AB
native reboot path pass their regression gates. This result does not establish
hotplug/cold-boot repeatability, another host OS, or production security.

## Follow-up

After a completed attempt, add a sanitized result below `results/` with exact
artifact, padded partition, host OS, cable/port, timing, ordered gate, pstore,
and cleanup evidence. Update `docs/HARDWARE_SUPPORT.md`, `docs/ROADMAP.md`, and
the USB hardware record only for gates actually observed on this named unit.

If all gates pass, repeat disconnect/reconnect and another cold boot before
claiming repeatability. Replace the laboratory `nc` root shell with an
authenticated administrative service only as a separately attributable
hardening change. Keep host mode, VBUS, Type-C role switching, charging,
additional gadget functions, persistent storage, and distribution SSH outside
this experiment.
