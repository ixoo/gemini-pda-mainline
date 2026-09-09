# Console-ownership successor session

Status: **completed; observation budgets consumed; changed-ID Gemian confirmed**.
The [result](RESULT.md) records the passing console observation and preserves
the incomplete native SSH-disconnect witness separately.
The candidate and validation identities are frozen in [validation.json](validation.json).
No result, budget or admission from Candidate R is reused.

## Hypothesis and distinguishing observation

The four-line init change removes inherited console standard descriptors from
PID 1 and background services while the explicit tty1 status action remains
readable. On the new candidate, one authenticated baseline observation must
retain CPU0–7 serviceability, CPUs8–9 offline, input/map identity, USB access and
separate bounded logging. A single supplemental metadata query must identify
all three PID-1 standard descriptors as the null character device. This is a
new measurement of the console-ownership repair, not another boot marker.

The kernel Image, board DT and configuration are unchanged from the audited
PWRAP foundation. The fresh private authentication bundle and changed init make
this a new candidate. No keyboard capture, disconnect probe, storage-content
read, thermal sample, load, CPU admission or radio action belongs in this boot.

## Exact candidate and deployment

- Raw boot image: `7dfc3b1f771a12b8e711f699cf8fcfd2678aedc15bc9d8bcc98554f9c6654cdb`.
- Exact 16 MiB padded image: `7d9eb0e20f145594ba5b9e56bbb809998c813d2517ce2f43b17074828459ea2a`.
- Private manifest: `907c0c107eb71e0335c52d6b0f20bbb9cf6742d3603ff3e690a11cc9d7202ec1`.
- Source revision: `0541b8471b83f8105d2e150e0aa84643f9e6b081`.
- Installer used for this completed deployment: `95f85db37dafdd431516331fafc6918419a741044a0d54db3cd6edcfc12f21fe`.
  The later tool-only revision is recorded in DEPLOYMENT.md; no reinstallation is needed.

Use the existing validated baseline installer with the default baseline receipt
namespace. At execution it must recheck known-good Gemian identity, live GPT
logical boot2, the shared block-device guard, inactive/unmounted/non-root state,
exact size, writable state, stable power and private tmpfs staging. Preserve the
predecessor digest, skip a matching partition, otherwise require full readback.
It must clean staging and shut down after verification. The owner selects boot2
only after the resulting deployment receipt and clean-shutdown handoff.

## Finite observation sequence

Reuse the existing baseline collector and finishing helpers with a **new**
admission and the exact candidate/deployment hashes. The historical
[baseline protocol](../2026-09-05-owner-away-experiment-preparation/baseline/SESSION.md)
remains consumed; its implementation and limits are the reusable parts.

1. One owner physical selection after verified installation.
2. One baseline observation, at most 45 seconds and the existing output limits.
   The owner confirms the actual status screen is readable.
3. One supplemental PID-1 metadata query, at most 12 seconds, 1 KiB stdout and
   16 KiB stderr. Before sending, preserve its exact generated command and one-use
   local claim. Reuse `session_steps.identity_script()` with this candidate and
   the just-observed boot ID, then `ram_guard_script()`. Query only
   `stat -L -c '%F|%t:%T' /proc/1/fd/0`, `/proc/1/fd/1` and `/proc/1/fd/2`,
   prefixing them with `pid1-fd-0=`, `pid1-fd-1=` and `pid1-fd-2=` respectively.
   End with a fresh boot-ID equality check and the literal line
   `__A53_PID1_STDIO_END__`. Require exactly those three numbered
   `character special file|1:3` records, a complete final marker, unchanged boot,
   empty stderr, exit zero and complete host transport. This inspects metadata;
   it never opens a console or input device. An absent or conflicting result is
   not a pass and is never retried in this boot.
4. If baseline and metadata pass, run the existing three authentication probes
   within their existing 15-second per-connection limits. If either observation
   fails, omit dependent probes and preserve available evidence instead.
5. Preserve and seal the existing logger once, within its 600-second lifetime,
   2 MiB cap and existing 30-second export budget. Review completion before the
   single reviewed native recovery request; confirm changed-ID Gemian afterward.

All helper phase admissions retain their existing source, candidate, custody,
raw-evidence and one-use checks. No extra connection follows a failed phase
without reviewing the retained outcome and admitting its specific preservation
or recovery purpose. The supplemental metadata query cannot authorize recovery
or substitute for baseline log preservation.

## Decision branches and handoff

- Complete baseline, three null descriptors, actual readable screen,
  authentication, preserved logs and confirmed recovery establish this
  successor's scoped baseline. Then prepare a fresh, separately admitted
  harmless disconnect proof on matching inputs; keyboard capture remains later.
- A descriptor other than null, console/USB regression or identity mismatch
  rejects the relevant successor claim. Preserve the exact result and diagnose
  that observation before another candidate; do not broaden the scan or repeat.
- Missing transport, output, owner confirmation or recovery is inconclusive.
  Preserve local partials and follow the existing recovery rules. If USB is
  absent, physical recovery remains the owner's action.

This does not establish a complete reader scan, Dropbear cancellation, keyboard
coverage or ten cold boots. The original disconnect execution binding stays
disabled. If the owner is unavailable, retain this packet and keep Gemian
available for already-authorized investigation while advancing offline roadmap
work; do not shut it down solely to wait for an absent owner.
