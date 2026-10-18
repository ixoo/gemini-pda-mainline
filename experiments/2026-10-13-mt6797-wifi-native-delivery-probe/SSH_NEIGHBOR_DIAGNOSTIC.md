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
