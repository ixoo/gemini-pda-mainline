# Eighth Phase B runtime: the first healthy bounded join

Boot identity: mainline `83288c69-c8ad-4e2e-859c-b0459fecd78e` from candidate
7 (boot2 `820657ed…`, receipt `e3134657…`, compile-12 package `784aef75…`,
input `65c2fa81`), laptop session source `dddb6e93`, returned to a changed-ID
Gemian boot `51e41731-70b9-4767-81cb-b44879b90f5a` through the reviewed native
recovery. Sanitized records: [results/runtime-8.json](results/runtime-8.json)
and the laptop's combined, unchanged
[results/runtime-8-session-result.json](results/runtime-8-session-result.json).
The sealed log is 152788 bytes, 2017 records, SHA-256 `de9e3a1e…`, manifest
`7fd00181…`. Raw evidence and the AP identity stay private.

## Observations (measured)

- Initialization 285/285 with status 0, PA rails off, no BT H1 record. One
  500 ms channel-40 passive scan succeeded (host elapsed 515086 µs, firmware
  management count 15); the owner's BSS matched; NO-IR lifted after the beacon.
  The sampled tuning is consistent but is not atomic RF proof.
- The connect request was acknowledged with errno 0 and the helper exited 0.
- Authentication: TX PID 1, TX done status 0, response status 0, mac80211
  `authenticated`. Association: TX PID 2, TX done status 0, response status 45
  (`WLAN_STATUS_INVALID_RSN_IE_CAP` in the selected header), mac80211 `denied
  association (code=45)`. The request carried no RSN element by construction,
  so the denial is the expected outcome of this open-system attempt against
  the protected AP.
- Cleanup: submissions 0, 1 and 2 each returned one page; then exactly one
  admitted indication, `bss absence: bss=0 absent=0 quota=0 reserved=0`, whose
  body values were measured for the first time and remain metadata; then the
  final line `cleanup: stage=3 credits=returned slots=retired deauth=0`;
  mac80211 then logged the connection loss. Nine pages submitted and nine
  returned. No stopped footer and no refusal record.
- Classifier: `bounded_join_pass=true`, `healthy_cleanup_demonstrated=true`,
  `stage_and_credit_order_verified=true`, `unique_tx_acknowledgements=true`,
  `management_exchange_demonstrated=true`, `refusal_recorded=false`,
  `wifi_operational=false`. A53 regression passed and the reviewed native
  recovery passed; the laptop independently verified the changed Gemian boot.

## What this demonstrates, and its limits

The driver can run one bounded station join end to end against the owner's
protected access point: scan, open-system authentication, association request
and response, and a finite host-owned teardown that returns every page and
retires the BSS and station slots, with every firmware notification on the
path either admitted under a strict contract or refused. This closes the
cleanup question opened in runtime 6.

It is not operational Wi-Fi. The association was denied, as expected without
an RSN element; no key exists, no data frame was sent or received, and the
radio scope stayed one passive scan and one open-system attempt. The
protected association, the key exchange and the data path are the next
development stages, scoped in [PHASE_C.md](PHASE_C.md).
