# Keyboard console ownership repair

## Observed problem

Candidate R's [disconnect result](../2026-09-07-keyboard-boot2-session/results/candidate-r-disconnect-result.json)
is still inconclusive: its export exited 1 without output. The old boot is no
longer live, as established by the [Gemian identity receipt](../2026-09-07-keyboard-boot2-session/results/gemian-resume-20260908.json).
Neither the failed predicate nor preservation of the old remote partials can
be reconstructed from that empty output.

Source inspection identifies a concrete incompatible contract. The
[exporter](../2026-09-05-owner-away-experiment-preparation/keyboard/disconnect.py)
rejects any console/tty0/tty1 descriptor in any process before emitting any
of the four evidence files. The baseline init did not close inherited console
stdio before starting the logger, USB service and BusyBox init. A console
handle is not itself proof of active input consumption, but the strict scan
cannot pass while those handles remain. Scan refusal also prevents evidence
preservation. This is a source-level failure path, not attribution of the
historical runtime refusal to a particular process.

## Pinned BusyBox source check

The candidate shell package is Ubuntu `busybox-static_1.36.1-6ubuntu3.1_arm64.deb`,
as pinned by the existing userspace builder. Source archives from the
[Ubuntu package pool](https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/)
matched the SHA-256 entries in `busybox_1.36.1-6ubuntu3.1.dsc`:

- `busybox_1.36.1.orig.tar.bz2`: `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314`.
- `busybox_1.36.1-6ubuntu3.1.debian.tar.xz`: `1c7d785cf1e1d5d09ddc22fe755e14327fb3799878a5d840fc611044ff05f022`.

In `init/init.c`, `console_init()` honors the `CONSOLE` environment variable;
without an override it sanitizes rather than replaces already open stdio.
The sole downstream patch touching this file, `init-console.patch`, skips
inittab actions whose named terminal is absent; it does not alter this behavior.
The `run()`/`open_stdio_to_tty()` path opens an explicitly named action terminal
independently of PID 1's standard descriptors.

## Small successor change

After baseline identity checks and before starting background services, init
sets `CONSOLE=/dev/null` and redirects its three standard descriptors to
`/dev/null`. This also prevents BusyBox init from reopening a console inherited
through the environment. The existing `tty1::once:/bin/console-status` action
still opens its named terminal, shows the status screen, and exits. SSH stderr
still goes to its existing RAM log; kernel capture still uses its existing
bounded RAM file. CPU, kernel, DT, keymap and input protocol are unchanged.

The exact-shell fixture now starts with a conflicting `CONSOLE=/dev/tty1` and
checks the inherited descriptor types/device numbers and environment of all
three service branches. Existing console and early-boot refusal cases remain
required. These mocks test shell inheritance, not a real PID-1 boot or hardware
reader release. A successor must still verify the console worker has exited
and the strict reader scan passes before keyboard capture.

## Refusal diagnostics

The successor exporter installs an exit trap before its identity check and
assigns fixed stage names to identity, RAM, attempt paths, outer exit, process
and descriptor checks, and each fixed file. A shell-controlled nonzero exit
emits only the stage and original status on writable stderr, then explicitly
exits with that status. A killed shell or broken transport can still leave an
incomplete diagnostic; missing output remains inconclusive. It does
not print process names, IDs, paths obtained from the device, or file contents.
Successful stdout framing and all pass/refusal conditions are unchanged. Raw
transport stderr was already retained by the host runner.

Seven local disconnect fixtures pass, including actual shell exits at identity,
RAM and a symlinked attempt path. The initial trap draft lost an implicit
`set -e` failure status on the host shell; an explicit final exit repaired that
observed defect. The same seven fixtures also passed under the exact ARM64
BusyBox on Buildbox.
The legacy binding stays disabled and its consumed admission is not reused.

## Validation and next boundary

Buildbox validated and exported the userspace package. Its 25 exact ARM64 shell
cases and 61 session-shell cases passed; the new diagnostic separately passed
all seven fixtures under the same pinned ARM64 BusyBox. The historical kernel
foundation audit, two identical private image assemblies, independent candidate
validation, derived-installer syntax/ShellCheck, 11 host installer methods and
49 remote gate/staging cases passed. Exact identities and receipt hashes are in
[validation.json](validation.json). No kernel rebuild was needed.

The new private authentication bundle makes this a new candidate; it is never
represented as Candidate R. The [session packet](SESSION.md) defines the next
observation. It is not deployed and has no hardware result. The original
disabled disconnect binding remains disabled.

Preservation must not depend on a passing reader scan. The existing reviewed
fixed-file preservation helper provides a separate component to consider for
the successor; this init change alone does not repair evidence export or prove
Dropbear cancellation. Review that integration after the focused shell result,
without building a resident supervisor merely to recover RAM from an ended boot.

The conditional test after that baseline is prepared in [NEXT_SESSION.md](NEXT_SESSION.md).
Its package and source checks are in [next-session-preparation.json](next-session-preparation.json);
execution still requires the actual first-session result and a fresh boot admission.
