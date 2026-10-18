# Unchanged C10 baseline — run 2 prepared, awaiting owner selection

Owner-directed after the [sealed C10/C11 comparison](CCMP11_RESULT.md#sealed-c10c11-comparison-and-ssh-boundary).
No new candidate, kernel build or runtime code change. The original C10 pass
counts as run 1 of at most 3. C11 is a separate observation, not a C10 repeat.

Hypothesis: the original C10 boot-bound SSH pass is repeatable without C11's
observer. Each run measures transport, DHCP, individual pings, SSH stage, host
cleanup and planned versus actual data duration separately. A short session is
not a duration pass. Retain the original diagnostic limits. One custodian,
one capture/session/reviewed return per fresh boot; no silent retries. Re-arm
and reconnect stay disabled, requiring a physical selection for each session.

| Run | Boot ID | Transport | DHCP | Pings | SSH | Host cleanup | Data duration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C10 run 1 | `c80f93fe-ea39-4d6e-86b8-bfec0254c65c` | Pass | Bound | 3/3 | Authenticated, fresh boot matched | Stage 3, debt 0 | 6.210 s / 6.200 s planned |
| C11 | `e86a098f-c62a-4b48-a1c6-153627abbef2` | Pass | Bound | 3/3 | Exit 255; no accepted server connection observed; exact TCP/KEX/auth stage unknown | Stage 3, debt 0 | 6.175 s / 6.156 s planned |
| C10 run 2 | Pending physical boot | Not run | Not run | Not run | Not run | Not run | Not run |

## Run 2 guarded restore and handoff

Exact retained C10 image and original runtime tools, with kernel input
`0d1f51194d7001fc9c6b9219726935ede36bc828`. Raw image SHA-256
`fbe72c31ced5efd7c81317d23e3336141bf44eaf8a8a9e02b682353822112d45`,
full 16 MiB boot2
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`,
candidate receipt
`807c8fb9f886ce0209688740f67193626a86311b76e02d198a66b7d749b2b11c`.

Fresh strict LAN identity verified Gemian 3.18.41+/aarch64, boot
`795d2999-8793-46ac-a4b5-b8a6bc69321b`. The existing reviewed installer was
bound privately to that identity, the actual C11 predecessor and a new run-2
evidence directory. No candidate, runtime or guard change. The generated
603-line shell is byte-identical to the original C10 installer under exactly
those identity/path/hash substitutions; Bash syntax and ShellCheck passed.
Derived shell SHA-256
`2ebfc660b4a79cefd7d0f671e2bd1e88987a701776328300e6e9b46ff4c8a8d4`.
Guard source remains
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.

One guarded installation completed with both live device gates, stable power,
sync/flush and independent full readback plus byte comparison. The predecessor
matched C11; final readback matched the exact C10 full image above. No fresh
backup or automatic reboot. Clean shutdown and unreachability were confirmed.
The actual 944-byte deployment summary, SHA-256
`0c90978b2e6bd14bd322d8bc8ef328ed60bbf533489e463a095d5edd73235872`,
was seal-verified and copied byte-exact/mode 0600 into the fresh run-2 root.
Complete offline host preparation passed using the original pinned sources,
with helper key/boot variables unset. Only the deployment summary exists in
the session directory; no capture or execution claim yet.

Required owner action: physically select boot2 with USB connected to the
custodian laptop and report startup. Stop here until that action. Then verify
fresh mainline boot and candidate identity before the single admitted capture
and session, seal evidence, perform reviewed recovery and verify changed-boot
Gemian independently. Record any different failure as a separate result.

## Decisions after baseline

Consistent C10 SSH passes select C11-specific observer diagnosis. Intermittent
C10 failures select an independent SSH investigation: first establish TCP/KEX/
auth stage, then evaluate legitimate-frame crypto/PN rejection, TCP stalls or
drops and RX/credit accounting. Specify one bounded diagnostic with hypothesis
and decision branches before implementing. Do not infer a cause from missing
client output. After baseline, review 60 s, 2 min and 10 min lifetimes and report
the first failure point. These extensions have not been built or admitted yet.

GTK delivery, rekey, key reuse and reconnect remain disabled. No -48 adjustment,
longer transport deadlines or unresolved-callback reverse engineering without
a specific test need. Full Wi-Fi acceptance remains incomplete.
