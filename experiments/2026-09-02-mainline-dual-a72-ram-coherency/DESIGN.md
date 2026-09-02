# Dual-A72 RAM coherency design

## Parent boundary

Exact patch `0481` has two fresh-boot passes on the named unit. Each spent one
controller trigger, brought CPUs 8 and 9 online, advanced both `/proc/stat`
lanes, retained successful terminal records, issued no CPU_OFF or retry, and
returned automatically to a new Gemian boot with `boot2` unchanged.

## Child hypothesis

On a third pristine boot, the same one-shot result can support one independent
post-online observation: CPU8 and CPU9 have distinct core IDs in one package,
accept exact affinity masks, execute on their selected CPU, and exchange the
candidate's fixed BusyBox payload through RAM-backed rootfs without a byte
change in either direction.

## Exact pass predicate

The attempt passes only if all of the following are true in one boot ID:

1. the inherited pristine and one-trigger parent classifies
   `cpu8-cpu9-online-accounting-advanced`;
2. the child opens exactly one netcat session and never retries;
3. CPUs `0-9` are online and the offline set is empty;
4. the root source and type are both `rootfs`, `/run` has no separate mount,
   and `/proc/mounts` contains no `/dev/*` source;
5. CPUs 8 and 9 report core siblings `8-9`, thread siblings `8` and `9`, one
   package ID, and distinct core IDs;
6. affinity lists and executing-processor fields are exactly 8 and 9;
7. CPU8 and CPU9 each hash `/bin/busybox` to the pinned payload SHA-256;
8. CPU8 writes file 8 and CPU9 reads it, then CPU9 writes file 9 and CPU8
   reads it; all four file hashes match the pinned SHA-256 and both sizes are
   exactly 1,914,704 bytes;
9. both scheduler-accounting vectors advance monotonically by a positive
   amount; and
10. both RAM files are absent after cleanup, with no partition read, storage
    write, CPU_OFF request, retry, or reboot request.

Changed-ID Gemian recovery, terminal retained proof for both A72 CPUs, and an
unchanged full `boot2` checksum close the complete attempt.

## Decision map

- Full live plus recovery pass: record bounded topology/affinity/RAM integrity
  and design one finite concurrent multi-cacheline child.
- Parent failure: stay at CPU online/accounting; do not run the RAM probe.
- Topology or affinity mismatch: investigate scheduler/topology description;
  do not increase load.
- Checksum or size mismatch: stop and isolate the first failed direction; do
  not repeat the full probe unchanged.
- Accounting non-advance: retain checksum evidence but do not claim independent
  scheduling; design a changed per-CPU execution oracle.
- Incomplete transport, unchanged boot ID, missing recovery, or conflicting
  evidence: inconclusive; improve attribution before another device boot.

## Safety and claim boundary

This is a short userspace observation over volatile RAM. It does not run CPUs 8
and 9 concurrently against the same cacheline and cannot establish general
cache coherency, stability, performance, idle, CPU_OFF, hotplug, DVFS, thermal,
suspend, or default-profile readiness. Those remain separate gates.
