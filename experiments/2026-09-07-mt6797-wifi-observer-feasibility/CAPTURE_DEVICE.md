# Capture-mode device export

[capture-device.py](capture-device.py) connects the preserved pstore snapshot
to the [bounded serial exchange](CAPTURE_EXPORT.md). Startup schema 2 selects
either `export` or the existing `cycle` action explicitly. The export action
does not open the detector, initialize capture, arm recovery, clear memory or
start a radio cycle. After one transfer it parks PID1 with the serial descriptor
open. There is no command receiver or automatic transition to the cycle action.
This is an implemented preparation step, not a selected device session.

## Acquisition and USB ownership

After the existing startup identity, source and private-input checks, export
requires root PID1 and the explicit export action. It checks runtime identity,
capture mode, zero interference count and the exact ramoops parameters. Both
split DT reservations and the empty PMSG `no-map` property must match. It
requires one read-only pstore mount and exactly `pmsg-ramoops-0` among PMSG
files, then reads exactly 65,536 bytes and repeats the capture checks. It reads
the backend's initial old-log copy, never `/dev/mem` or a new physical mapping.
These checks rely on the separately verified candidate; they do not attest
arbitrary kernel code or independently prove current retained bytes.

Before its first USB control write, the bridge requires an unconfigured,
disabled Android gadget with zero ACM instances and no selected ACM port.
It checks the first serial node against its sysfs major/minor identity, selects
one ACM instance and the `acm` function, checks those values, then enables the
gadget once. An existing owner, unexpected value or partial operation causes
refusal without a configuration retry or automatic restoration.

The source initializes ACM before the other generic serial function, and its
allocator chooses the first free line; the selected configuration excludes the
standalone serial gadgets. The bridge therefore uses `ttyGS0`, with a runtime
major-number check rather than a hard-coded major. The opened descriptor must
match that identity and be a terminal. The [source receipt](results/capture-device.json)
pins the inspected Android gadget, ACM, serial, preceding function initializers
and pstore reader. This is source evidence, not observed USB enumeration.

After the host requests the selected session, the bridge requires USB state
`CONFIGURED`, rechecks USB ownership and capture state, sends the snapshot and
checks capture state again. It retains the successful descriptor: a write's
return only establishes queuing, so an immediate close could discard bytes.
Failure closes the descriptor and parks startup. The inspected native close
can wait up to 15 seconds for its transmit queue; the userspace deadline is
not a hard bound on all kernel calls. No gadget disable or reset follows.

## Raw-reader correction

The native `ramoops_pstore_read()` calls the text crash-header parser for every
record type. An arbitrary raw PMSG prefix such as `====1.2-C` followed by a
newline therefore supplies a compressed flag and fabricated timestamp. The
caller only decompresses DMESG and ignores that flag for the PMSG filename;
this does not demonstrate changed PMSG payload bytes. The earlier raw copy is
not guaranteed NUL-terminated before parsing, so a numeric raw prefix can also
make the text parser read beyond its supplied raw extent. Raw snapshot export
must not depend on retained contents being a terminated crash-log string.

[Patch 0011](patches/pstore/0011-pstore-preserve-raw-capture-PMSG-read-metadata.patch)
bypasses that parser only for capture-mode PMSG. It supplies zero time and
uncompressed metadata while preserving the exact raw bytes. Ordinary PMSG and
crash-log parsing remain unchanged. The
[native-body test](test-capture-reader.py) reproduces the parent's metadata
confusion and verifies the correction, the unchanged other paths and allocation
failure with retained input preservation. Strict Checkpatch passes, excluding
the explicitly synthetic archive sign-off. The original 3.18 Checkpatch cannot
run under the installed Perl; Linux 7.1.3 Checkpatch supplies the style result.
The [46-patch full build](results/full-kernel-link-46.json) now passes. Inspection
of the final linked reader confirms that the capture-PMSG branch bypasses both
text-parser calls and stores zero time and compression metadata.

## Validation and remaining work

Four device-test groups use the existing synthetic startup fixture. They cover
complete snapshot acquisition, layout/boot/interference/mount/size refusals,
ambiguous files and existing USB ownership. A real duplex pseudo-terminal test
runs the bridge and host receiver with injected USB controls and device identity;
it preserves all synthetic bytes and observes exactly the three selected USB
control writes. It does not operate a PDA gadget or prove kernel resource
ownership. The stream tests and startup preflight tests remain separate.

The earlier assembly's `0-9` CPU expectation is not appropriate for this native
configuration: its first patch rejects CPU8/9 before platform or firmware
CPU-on. The [third assembly](STARTUP_ASSEMBLY.md#export-filesystem) uses `0-7`;
that source expectation is still not an observed successful boot. It binds the
seven startup files and schema-2 manifest to the validated 46-patch kernel.
Complete the boot/recovery and physical USB-export protocol next. Clearing remains absent
and requires separate owner approval after its implementation and preserved
predecessor are reviewable.
