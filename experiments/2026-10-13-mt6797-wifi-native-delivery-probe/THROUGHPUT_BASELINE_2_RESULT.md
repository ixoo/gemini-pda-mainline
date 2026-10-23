# Baseline 2 consumed: TX measured, RX harness refusal, healthy disconnect

One corrected run from host `910ea7bb`, on unchanged installed kernel
`3da69187ec93fd15b28fda3fbdbf118c37ad55a5`, release
`7.1.3-gemini-a53-private-p2e-delivery`, boot2 SHA-256
`5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd`.
Fresh boot `1877fe6b-b6e1-4f35-9211-f863bdf1efea` verified before firmware
start. Common initialization passed 285/285; join, DHCP, three pings and
public-key SSH authentication succeeded. No build or image change in this run.
See the [predeclaration](THROUGHPUT_BASELINE_2_PREDECLARATION.md).

| Direction | Measured scope | Device CPU | Counts/errors |
| --- | --- | --- | --- |
| TX → host | 5/5 progress-emitting chunks; 1,332,936 received bytes over 51.829942958 s host span: **0.205740 Mbit/s**, rounded **0.206** | Aggregate idle **87.525%**, iowait 0%; before/after device span 51.000 s | 959 TX status completions, 4 nonzero (status 3); netdev TX 1031 packets/drop 0/errors 0, RX 972 packets/dropped 84/errors 0 |
| Host → RX | **Not measured**: first receive chunk hit `File size limit exceeded`, exit 153; shell exit 38 | No final sample; unavailable | Harness refusal, not a link result; no delivered-byte or rate claim |

The five device TX chunks each reached the planned netcat timeout, exit 143.
No SSH idle timeout recurred. The host spans include chunk transitions and
socket drain; completion counts use the half-open device interval
[24.210,75.210) s with 10 ms clock resolution. Four failed packet completions
are retained, not recast as successful delivery. Ordinary packet failure did
not poison this driver's existing finite lifetime.

The RX temporary file inherited `ulimit -f 256` from the authenticated USB
ancestor: the pinned BusyBox uses 512-byte units, hence 128 KiB. Writing a
planned 1 MiB chunk into that regular file violated the harness limit. The host
BrokenPipe result reported zero because the old endpoint accumulated its count
only after a chunk; **that zero is not evidence that no RX bytes arrived**.
This invalidates RX, not the separately completed TX measurement.

The offline correction counts `timeout nc | wc -c` through a pipe, preserving
the timeout status with BusyBox pipefail. No payload file or limit increase.
Endpoint counts now accumulate as sends/receives succeed, including before an
exception. An actual generated-counter fixture passes a known 1 MiB stream
under the unchanged 128 KiB regular-file limit; all eleven measurement fixtures,
shell syntax and ShellCheck pass. This correction was **not used on hardware**
in baseline 2. No repeat of this consumed run is authorized by that correction.

## Prompt disconnect, delivery and ledger

The tagged remote group and host endpoints were quiescent. One standard
disconnect was accepted at PM+61.800853076 s, completed PM+62.150853076 s,
5.24 s after observed remote EOS. Data ended with reason=disconnect,
elapsed 61684 ms. No firmware monitor-loss notification or driver fail-stop.

Reserved PID 127 completed **TRANSMITTED/status 0/class 2**, internal
PM+61.945222696 s; phase=completion and phase=cleanup lines agree. The
submission log was PM+61.920218 s, outside the previously observed blocking
window; this does not narrow that window or establish encryption/air ACK.

PM abort, pairwise removal, group removal, station removal and BSS disable
were credited. **Whole-ledger stage 3 passed**, credits returned and slots
retired, deauth=1. Ordinary allocations/completions both 1051, pending=0,
unowned=0, wraps=8; 1047 ordinary status-0 completions and 4 status-3 completions.
This is the standard-disconnect result; it does not fix or retest the
[independent connection-loss waiter candidate](LOSS_PATH_TEARDOWN_AUDIT.md).

## Preservation and scheduling conclusion

All 75 pre-recovery seal entries independently rehashed; seal SHA-256
`abfd3fd23e3873612ab6e856d1abcf0faa572b92d13920f445fa2e77f546afca`.
Complete kmsg: 924284 bytes, 6317 contiguous records (0–6316), SHA-256
`be54bc4afac50200e008a6625bf3ab29ecc4cb9c66b1c1d05daa7a4ce7253a36`.
Quiescence and A53 RAM-service regression passed. Reviewed return succeeded;
independent strict LAN SSH confirmed 3.18.41+/aarch64 and changed Gemian boot
`5044c0d9-617b-4030-8e59-1ba3b1147a72`. Raw evidence stays private under
`artifacts/wifi-throughput-baseline-2/`; [sanitized scalars](results/throughput-baseline-2.json).

The source audit confirms the scheduling ceiling: data enqueue requests
`schedule_delayed_work(..., 0)`, while selection requires no in-flight frame
and no page debt; each running worker then schedules its next tick at
`msecs_to_jiffies(20)`. A new enqueue does not accelerate an already pending
delayed work item. Submission and completion/credit processing span multiple
ticks, so one frame at a time costs repeated polling delays. The observed
roughly 20 frames/s is consistent with this **driver scheduling ceiling**.
The code imposes the wait; the pump comparison will measure its cost. Aggregate
87.5% idle over eight CPUs can hide one busy CPU, so it does not independently
exclude CPU saturation on the service CPU or establish a physical transport
ceiling. It supplies no evidence for a DMA throughput fix.

The owner selected a bounded immediate-pump comparison next, preserving depth,
credit accounting, PID ownership, deadlines and admission. **DMA is deferred**:
its possible justification is CPU headroom, not throughput; this measurement
does not support DMA as a throughput fix. If the pump changes TX by an order
of magnitude, investigate link rate/aggregation next. Reconnect remains closed;
the dormant safeguards remain dormant.
