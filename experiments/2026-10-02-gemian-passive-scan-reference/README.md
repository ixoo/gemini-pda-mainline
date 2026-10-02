# Gemian channel-40 scan reference

Status: one reference scan consumed; three recent BSS results returned, but
actual passive firmware execution is unverified.

The owner requested a Gemian comparison with the
[mainline tuning-sample scan](../2026-10-02-mt6797-scan-tuning-sample/README.md).
The hypothesis was that a similar standard-interface channel-40 scan would
supply a positive receive reference or expose a difference in scan behavior.
A positive fresh result would prioritize differences in mainline initialization,
filtering and receive processing; a failed or empty reference would leave the
radio environment and reference comparability unresolved. A missing firmware
counter log would not be interpreted as a zero count.

## Bounded protocol and result

Verify the known-good release and boot identity, existing managed interface,
channel permission and carrier. Use the same validated Debian `iw` 5.19 and
libraries as mainline, temporarily staged with per-file checksum verification.
Take a cache dump and bounded kernel-log snapshot, then issue exactly one:

```sh
iw dev wlan0 scan freq 5200 passive
```

The scan command has a twelve-second timeout and an exclusive pre-request
claim. Do not retry after timeout or failure. Collect results and the log delta,
verify unchanged boot and connection, preserve private evidence, and remove only
the uniquely named reproduced tool stage. No interface, connection, logging,
filter, regulatory, calibration or power-save setting is changed.

The [runtime receipt](results/runtime-1.json) records success, three results at
5200 MHz reported as last seen 20 ms earlier, and two additions relative to the
one-entry prior cache. The existing entry's reported TSF changed. The host uptime
interval was approximately 380 ms. The same-boot associated link and carrier
remained present; temporary tools were removed. No scan-completion counter was
visible in the captured kernel-log delta. No RF dwell or independent frame
capture was obtained.

## Comparison boundary

All three results identify their information elements as originating from probe
responses. The pinned public vendor
[AIS scan source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/mgmt/ais_fsm.c)
maps an empty-SSID online/ordinary scan to active wildcard scanning when
`CFG_SUPPORT_AIS_PASSIVE_SCAN` is disabled. Its pinned
[configuration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/config.h)
disables that option. Exact running-binary equivalence is not established.
This supplies a concrete source-level reason to doubt passive equivalence;
probe-response metadata alone does not identify who transmitted a probe.

Gemian was already associated and had connection-manager/supplicant processes
running. Reported cache freshness supports a positive standard-interface receive
reference, with concurrent reception still possible. It does not establish that
the mainline passive candidate should return identical results or justify adding
probe transmission without its own reviewed protocol. Mainline reception,
association and traffic remain unproved. Preserve this observation and continue
with a distinct measurement of its receive path; do not repeat this reference
merely to obtain another positive result. Raw peer information stays private.
