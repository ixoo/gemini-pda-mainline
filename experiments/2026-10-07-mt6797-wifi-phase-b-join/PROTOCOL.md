# First bounded Phase B device test

Status: concrete protocol, reviewed for this candidate; no RF result yet.
This is one authentication/association experiment, not operational Wi-Fi.

## Hypothesis and decision-changing observation

The proven Phase A common-init and channel-40 scan can hand its retained AIS
owner to mac80211, send native management frames through TC4 PIO, and receive
directed responses. The new observations are matched TX-done acknowledgements,
Open System transaction-2 response, association response status and, if accepted,
the separately matched associated-STA activation event. An AP refusal without
an RSN element is useful evidence and does not require credentials.

## Exact artifact

| Item | Identity |
| --- | --- |
| Driver checkpoint | `a709cb82b5a1f648381e0b3644224f0f4ee1c2d8` |
| Clean build input | `a9c1091ec285da55c25190e5e8cf0eaa6b7ce81e` |
| Profile | `mt6797-a53-wifi-phase-b-compile`, 638 selected patches |
| Builder | Buildbox-1, 32 jobs |
| Package inventory | `d4f5add5d0767132468d2fdae268017b190a3f10db5c59a63f6c657be43d5320` |
| Release | `7.1.3-gemini-a53-wifi-phase-b-compile` |
| Candidate receipt | `a0756937bbdf49e55b4614b71f3f5dea43c32afd32c159581d7ae3b59048aa8a` |
| Full padded boot2 | `6ecc057c390e6c9acb3480a52950a7261d7f4678c43da5688dcc1724e2bb778f` |

The [receipt](results/candidate.json) records all six candidate members.
[build-candidate.py](build-candidate.py) starts from the booted Phase A runtime-3
candidate. Its board DT is byte-identical, all 61 RAM-root members are retained
with only the release gate changed, and configuration differs only in release
and `CONFIG_MT6797_STATION_JOIN=y`. PSCI/SMC power-off and `clk_ignore_unused`
are preserved. The parent never had `regulator_ignore_unused`.

The full build, package validation, every inventory checksum, Linux repository
checks and peer/handoff/HIF/rates ASan/UBSan fixtures passed. Ordered patch
replay matched every driver file. These checks do not prove firmware behavior,
kernel races or RF support.

## Effects and finite budgets

- Existing reviewed WMT setup, negotiation and the 285-step common init remain
  unchanged, including their PA-rail and calibration effects. Retained firmware
  and the private board record are unchanged. No storage/calibration write.
- One passive 500 ms requested dwell on permitted non-DFS channel 40 (5200 MHz).
  The script requires the privately designated owner AP in that scan's BSS
  results. No second scan or target substitution.
- One peer: BSS 0, own-MAC 1, BMC WLAN 0, pairwise WLAN 1. Continuous ownership
  from scan through join; no quiet interval or returned credit asserts drain.
- Directed/broadcast RX filter, channel request (at most 9 s), pre-auth STA;
  if accepted, legacy BSS/RLM and state-3 STA plus matched activation response.
- At most one host authentication, association request and deauthentication
  submission. Each descriptor uses fixed OFDM 6 Mbps, attempt count 3 and
  requested 500 ms lifetime encoded as 15 times 32 TU (491.52 ms). Firmware
  retries and automatic received-frame ACKs are distinct from host submissions.
- No data, EAPOL, keys, HT/VHT/WMM, DMA or new HIF interrupt. The ten-second
  join window admits at most 512 polls and 4,096 packets, eight per port per
  tick. Management completion is bounded at 750 ms, command credit at 100 ms.
  Every PID, command sequence and channel token is consumed once without reuse.
- Accepted association immediately queues one driver-owned deauthentication.
  Its actual acknowledged completion and page return precede STA removal,
  channel ABORT and BSS off, with separate page accounting at each step.
  A refused attempt follows healthy cleanup without that deauthentication.
  All slots remain retired even after cleanup.
- Firmware abort, stopped firmware/ownership loss, malformed or unmatched input,
  unknown event, command ambiguity, unexpected credit or deadline failure stops
  the session. No cleanup command follows terminal poison. The bounded known
  debug/sleepy notification policy is retained from Phase A; bodies are private.

## Execution and evidence

1. The laptop Codex is the sole device custodian. Verify live Gemian identity;
   deploy through the reviewed live-GPT boot2 guard, inactive/non-root checks,
   predecessor checksum and stable-power gates. Require full padded readback,
   evidence flush and clean shutdown. The owner physically selects boot2.
2. Verify changed boot identity, exact release, USB SSH, candidate bytes and
   console. Run the existing Phase A retained-memory/WMT capture adapted only
   to this receipt/release. One `wmt_negotiate` trigger; no retry. Require its
   ordered preparation/common-init/firmware/record/regulatory/TC4 success gates.
3. Bind the private mode-0600 AP input using [bind-target.py](bind-target.py).
   Validate the fixed channel and safe shell quoting. Keep identities and the
   bound script in ignored private inputs. Authenticate `EXPECTED_BOOT` through
   the inherited host; [join-once.sh](join-once.sh) then performs one scan and
   connect request, and waits at most 12 s for the driver's terminal record.
   Its `iw event` subscription makes no radio request. Do not disconnect,
   lower the interface or retry while the driver owns cleanup.
4. Preserve complete kernel, userspace, event and transport captures privately.
   Seal the log, run the inherited A53 regression and use the reviewed native
   Gemian recovery path with exact tool/boot identity. Verify changed-boot
   Gemian afterward. Missing identity or evidence defers recovery; a timeout
   supplies no alternate procedure.
5. [classify-join.py](classify-join.py) checks unique submissions/PIDs, actual
   acknowledgements, directed statuses, activation, exact total page return and
   ordered cleanup. Operational Wi-Fi remains false in every result. Publish
   only sanitized stage facts, candidate/boot identity and digests.

## Decision branches

- Missing AP or failed prerequisite: no host RF submission; diagnose the exact
  negative evidence. No identical-artifact retry without a new measurement.
- TX submission without valid TX done, or no directed response: preserve the
  last stage and exact failure, recover, inspect the wire/descriptor/filter
  discrepancy offline before changing or repeating the test.
- Authentication refused: record its status and healthy-cleanup evidence; no
  association proof or persistent connection claim.
- Association refused with acknowledged frames: host management TX/RX path
  demonstrated if all identity/evidence gates pass; this may be expected on
  the selected WPA2 AP without RSN. Continue toward the separately reviewed
  protected data/key admission rather than treating refusal as usable Wi-Fi.
- Association accepted: require BSS/STA activation, one acknowledged deauth
  and complete healthy cleanup. Then implement and review PIO data RX/TX and
  WPA2 keys toward DHCP, ping and sustained SSH. That is the remaining driver
  goal; this first admission is only its prerequisite.
- Any project safety stop condition: preserve evidence and stop device tests.
