# D2: observe local route and neighbor state, unchanged C10

Predeclared after [D1 succeeded](SSH_D1_RESULT.md). D1 retained the missing
client output but did not reproduce failure, so its earlier-failure stage is
still unknown. No unchanged D1 retry or new kernel candidate. This is one
additional host-only observation, not a fourth unchanged baseline session.

## Hypothesis and missing observation

Hypothesis: an uncached/unresolved laptop neighbor entry can prevent the laptop
from reaching the board's TCP listener while broadcast/group delivery remains
withheld. DHCP and board-originated router pings do not establish that the board
receives the laptop's neighbor-discovery traffic. Earlier failed sessions had
only seven checked PTK deliveries and no accepted server connection; passing
ones had 36 checked deliveries. That is a motivation to measure, not proof of
ARP loss, crypto rejection or causality. No host neighbor state was retained.

Retain the existing single SSH attempt's output as D1 does. Immediately before
it, read the local kernel route (`route -n get` for the already validated leased
IPv4 address) and that address's local ARP entry (`arp -n`). Read that one ARP
entry again afterward. These local queries do not send probes or change entries.
Use the laptop's system tools, numeric address only, bounded 0.5 s per query,
no DNS, cache flush, static mapping, packet capture, privilege change or extra
network traffic. Record query times/results and raw output privately, mode 0600.
Keep exact SSH command/options, readiness/identity/ACK gates and driver limits.

## Decision branches

- A retained client connect error establishes the TCP-connect failure stage.
  An unresolved/absent neighbor before and after is evidence of unsuccessful
  local resolution during that attempt, not proof the board acquired/rejected
  an ARP request. Select a separately bounded ARP/TCP observation if needed.
- A complete entry plus TCP failure requires distinguishing SYN/reply loss or
  route mismatch next; it does not establish a PN/crypto or credit defect.
- A banner/KEX/auth/host-key error selects that actually observed stage. Use
  server logs and RX/TX/credit chronology before attributing driver rejection.
- Success with an initially absent entry shows resolution can succeed in that
  trial; success with an existing entry is compatible with the hypothesis, not
  confirmation. Success/unknown query output leaves previous failure unresolved.

Compare actual client/error stage, route interface, neighbor state before/after,
query overhead and unchanged session duration. Do not label missing query output
as an absent entry. Do not classify unchecked RX frames as zero drops. No
automatic retry, deadline extension, forced cache state, GTK enable or driver fix
follows. If this remains inconclusive, state the precise missing observation
before selecting another experiment; do not repeat the same measurement blindly.

## Admission and boundaries

One fresh boot, custodian, capture and session; original C10 image, leaf,
initial-PTK policy and reviewed seal/quiescence/recovery. The owned helper's child
process group also owns the bounded local query children. Additional host work
can affect the short SSH window; retain its elapsed time and do not hide it by
lengthening any deadline. All D1 output and query files must be sealed before
recovery. Raw outputs can contain network identifiers; publish only reviewed
status/counts/timing/categories. No firmware queries or analysis is needed.

GTK delivery, rekey, key reuse and reconnect stay disabled. No -48 adjustment,
longer transport deadline or new kernel build. Staged 60 s / 2 min / 10 min
lifetimes remain pending; the finite SSH failure must not be misrepresented as
healthy sustained operation. Physical boot2 selection is the owner's action,
after tests, exact-image readback, clean shutdown and host preparation.

## Host implementation and validation

The [D2 session adapter](laptop-session-ccmp10-ssh-neighbor.py) retains original
C10 ownership and selects the [local-state helper](laptop-wifi-ssh-neighbor.py).
It pins and wraps the unchanged D1 observer. USB calls pass through; only the
single Wi-Fi call is surrounded by the three local reads. The D1 outer timing
includes those reads; `local-queries.json` separately records the original SSH
call's start/end and each query's duration. Query failure/timeout is unknown,
never translated into a missing neighbor or allowed to replace SSH identity proof.

Four [focused cases](tests/ssh-neighbor-test.py) reuse D1's actual-source CCMP
fixtures: success with original guarded ACK, retained client failure/no ACK,
query timeout with unknown state, and query execution error with unknown state.
They pass locally; D1's seven original cases remain unchanged. These are host
behavior checks, not hardware enforcement or a D2 runtime result. The system
route/ARP tools are present and executable; no cache read or network action was
performed by these fixtures.

## Local query source check

Apple's [route manual](https://github.com/apple-oss-distributions/network_cmds/blob/main/route.tproj/route.8)
describes `get` as destination-route lookup/display. In the published
[ARP implementation](https://github.com/apple-oss-distributions/network_cmds/blob/main/arp.tproj/arp.c),
the selected default get path searches and prints existing entries; set/delete
are separate operations. Numeric input and `-n` avoid hostname lookup. This
supports the selected observation scope; it is not a firmware or binary-identity
claim. The actual query exit/output and elapsed time remain runtime evidence.

## Verified preparation — await physical selection

Published host input `9820f896`, four focused actual-source cases and repository
checks passed. Original C10 image/receipt/leaf/capture/driver/recovery unchanged;
no new kernel candidate or compilation. Current known-good identity independently
verified as Gemian 3.18.41+/aarch64, boot
`f2211c8d-d200-4d67-8540-8dcadfed4047`.

The reviewed 603-line installer is byte-identical to original C10 under exact
identity/path/hash substitutions only; Bash syntax and ShellCheck passed.
Derived shell SHA-256
`74618ecd4d50165e14808a84fe66b3f6117e991ac5320403a1a4e92983752fdd`,
guard source
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.
One invocation verified already-matching C10 and skipped the partition write.
Independent full 16 MiB readback plus byte comparison matched
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`.
Clean shutdown/unreachability confirmed; no new backup or automatic reboot.

Actual deployment summary 923 bytes, SHA-256
`1112f91f15cbd63a967b5cd7cc85f55abb90bf2d9d34a3d1b0893e10f5a4db78`,
seal-verified and copied byte-exact/mode 0600 into a separate fresh D2 root.
Complete offline preparation through the new D2 adapter passed with helper
key/boot environment unset. Session contains only that summary; capture,
execution claim, helper and observation are absent. No D2 device trial yet.

Owner action: physically select boot2 with USB connected to the custodian laptop
and report startup. Stop until that action. Then verify fresh USB boot/kernel/
C10 installation identity, run one original capture and one D2 session with
unchanged limits, seal all actual client/query files, verify owned-helper/device
quiescence and A53 regression, use the reviewed return once and independently
verify changed-boot Gemian. Record missing observations or a different failure
separately; no silent retry.
