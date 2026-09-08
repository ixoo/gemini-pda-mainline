# Exact harmless disconnect-proof protocol

## Hypothesis and scope

On the exact authenticated baseline candidate, losing one no-PTY Dropbear
client while the separately built harmless probe child is live causes the
monitor and child to become terminal and reaped within the scaled 500 ms
lifecycle bound. Their four bounded files remain in RAM, and one independent
reconnect can export them after a complete process/descriptor scan establishes
that no monitor, observer, tty1 or input reader survives.

This proof opens no evdev node or VT and produces no keyboard result. It uses
the fixture-only child already frozen in enabled package
`0baad6b85ae68770b783245e2f1dcd7eeb4ef40d93c19e0b30e1f89f8adc3065`:

- monitor SHA-256 `4363a7d61d818bc443d5cfd76455ac38fc2cea35178d44a2dc81c229ff97b67f`;
- harmless probe SHA-256 `560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`,
  66,760 bytes;
- source revision `93e2b8526daa683c2ba848011fac757a398a13dd`.

## Current Candidate R admission state

The current admission is rebound to Candidate R: raw boot image
`3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c`, exact
16 MiB boot2 image `29f59c7f21a25b47d63d653857db9d7d0760d9a00f7193e098219699235f16f1`,
and candidate manifest `62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d`.
It is tied to fresh baseline admission `d10dcd8b-d67e-4311-ab7e-3f8c3078a88e`
and its reviewed supplemental chain (`1eae36...`, auth `947681...`, preserve
`31206d...`, request `33367f...`, confirm `74c1be...`). The enabled package,
monitor and probe identities above remain unchanged.

The fixed
[`disconnect-execution-binding.json`](../2026-09-05-owner-away-experiment-preparation/keyboard/disconnect-execution-binding.json)
contained the sole enabled proof admission
`c14f6469-5c0a-4a83-9909-6789b3586c36` for fresh Candidate R boot
`bbad1c49-ecdd-4f40-b1e0-c53f707106d1`. Its exact SHA-256 is
`47a1698639f3831e3da486b64e4b98c35653cb976a579b012ca2f40665904da4`.
The gate read and exactly compared that complete admission before preparation,
claims or transport. Binding preparation alone performed no disconnect action.
Final Astra acceptance and publication both completed before the one admitted
execution. After that attempt consumed its budget inconclusively, the binding
returned to disabled/null with SHA-256
`aa10351e1b5fc85515f790c0e38cf0f42e07ed14fe72fee11d7973f0b5775872`.

The kernel/DT/config hypothesis is the exact Candidate R composition above. The
older raw candidate
`a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf` and
manifest `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179`
are retained in historical readiness records only; they are not current
admission inputs and are not rebuilt or replaced by this protocol.

## Admission and exact effects

[`disconnect.py`](../2026-09-05-owner-away-experiment-preparation/keyboard/disconnect.py)
accepts a proof-specific admission rather than a future capture receipt. Before
any claim or packet, the enabled binding must match the complete Candidate R
admission. That admission reparses the complete authenticated baseline/recovery
archive, exact candidate and credentials, enabled package inventory, current
source closure, fresh mainline boot ID and six affirmative custody facts. The
local USB interface and direct route must also pass the existing read-only host
gate. Missing retained baseline bytes refuse before device contact. Any input
other than the single exact enabled admission refuses at this first boundary.

After those checks, the fixed effect budget is:

1. Create one local claim for exactly one probe connection, one independent
   export connection and zero retries.
2. In the first no-PTY connection, recheck boot/release/initramfs, Dropbear and
   administrator-shell identities plus RAM-only paths. Create the once-only
   `/a53-keyboard-disconnect` tree, deliver only the 66,760-byte probe, and run
   it against its dedicated `run` child directory in the fixture's explicit
   `ignore` mode. That child ignores TERM, so cleanup is either a direct
   process-group HUP or the monitor's bounded TERM/KILL branch; a TERM-terminal
   child is not a possible accepted outcome for this selected mode.
3. After the exact `fixture-child=<pid>` marker is received and all command
   bytes have entered the SSH client, kill that local SSH process group with
   `SIGKILL`. The measured marker-to-kill interval must be at most 100 ms. A
   missing, extra or late marker refuses. An early marker, incomplete stdin or
   over-limit diagnostic is retained as a non-pass rather than raising inside
   the runner, allowing the separately bounded export to preserve remote
   partial evidence.
4. In one new no-PTY connection, wait at most two seconds for the retained outer
   exit, require value 2, then scan at most 512 processes and 4,096 descriptors.
   Any inaccessible inventory item, surviving deployed probe or observer
   command/executable (including a deleted executable), tty0, tty1, console or
   input descriptor refuses. Both the monitor and its forked child retain the
   deployed probe executable identity and are therefore covered. Export the
   exact four retained files with per-member limits. Remote evidence is never
   removed.
5. Reparse the export locally and run the semantic prerequisite verifier over
   all seven fixed mode-0600 evidence files before writing a passing receipt.

The tracked binding is disabled/null after the exact admission consumed both
connections. Astra accepted its complete hash and fresh boot-specific evidence
for one harmless proof, and commit `8c38024168fc626e2ae407d207383e517567fab6`
published it before execution. That authority is exhausted and cannot be reused.

## Decision branches

- **Pass:** marker-to-kill is at most 100 ms; the monitor reports cancelled or
  forward-close cleanup, terminal/reaped child, permitted signal/timing/order,
  no late state and exact byte counts; outer exit is 2; export is complete; and
  the reader scan is empty. The receipt may populate only the same boot's later
  capture admission.
- **Fail:** retained evidence proves a contradictory, late, nonterminal,
  non-reaped or surviving-reader result. Stop the keyboard session and recover;
  no retry and no keyboard claim.
- **Inconclusive:** either connection, export, inventory or framing is
  incomplete. Preserve every available local and remote partial, stop, and
  recover; absence of evidence never becomes a pass.

Every branch leaves physical boot selection and recovery with the owner. No
automatic reboot, shutdown, storage access, keyboard read or reader process is
part of this proof.

## Current stop

The fresh Candidate R baseline/recovery chain is the dependency for the sole
proof admission: baseline admission `d10dcd8b-d67e-4311-ab7e-3f8c3078a88e`
and supplemental phase records `1eae36...`, `947681...`, `31206d...`,
`33367f...`, `74c1be...` are retained in the private authenticated archive.
The older missing-archive and old-candidate findings remain historical
readiness evidence and do not transfer to Candidate R. The separately admitted
identity connection passed for fresh boot
`bbad1c49-ecdd-4f40-b1e0-c53f707106d1`; binding and admission verification passed
offline. The first proof connection then received the complete fixture marker
and deliberately killed its client at a rounded 0 ms with empty stderr. The
independent export connection exited 1 after 0.439 seconds with empty stdout and
stderr. Without the four retained files or reader scan, the result is
inconclusive: monitor/observer termination and reader release are not proven.
Both connections are consumed, retry is prohibited, keyboard capture stays
disabled, and the current stop is preservation followed by separately reviewed
recovery.

A bounded strict-host-key LAN check at `2026-09-07T22:14:15Z` established that
the named device is reachable in known-good Gemian release `3.18.41+` with boot
ID `2b2a317f-94ff-43b3-a51f-2fa6c5ba0bf9`. The final root-source subcommand was
rejected by a quoting error and was not retried; it is not needed for the OS
identity conclusion. This observation does not select boot2 or repair the
missing private baseline archive.

One separately bounded read-only live-GPT preflight then resolved logical
`boot2` as inactive, unmounted `/dev/mmcblk0p30`, confirmed its exact 16 MiB
size, no holders, stable external power and unchanged Gemian boot ID, and read
its full-partition checksum once. The result is
`08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2`,
the retained consys-passive candidate—not the required baseline padded checksum
`a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`.
No partition write or power action occurred. Therefore the keyboard candidate
must be reconstructed and byte-validated before the standing guarded boot2
installation can be used; the existing partition must not be relabelled or
treated as that candidate.

## Host validation in this revision

Six disconnect tests cover deliberate process-group loss, early-marker refusal,
complete export framing, semantic receipt acceptance and contradictory lifecycle
refusal, absence of evdev/VT paths from the first command, and binding refusal
ordering/mutation cases.
The six prerequisite tests add a rehashed 101 ms transport refusal; the six
capture tests still pass. Python compilation and whitespace checks pass. No
Buildbox or kernel action was performed by the offline tests. The one later
identity connection used the reviewed bounded path and created no remote state.
Execution remains NO-GO after the single admitted proof ended inconclusively.
