# ND3 installation and CLI preflight — not a runtime result

The sole laptop custodian reported one guarded installation of the
[real ND3 candidate](results/native-delivery-candidate-3.json) using frozen
runtime source `d37d1e2af23f32e54016aa518fdd914644f648ce`. Those executable,
receipt and runtime pins remain unchanged. This record does not replace the
private deployment receipt or claim a native-mode observation.

## Custodian-reported installation evidence

- Actual Gemian `8dc27f98-f95e-4f74-9c4d-d57fd96a613a` verified before write.
- Live-GPT target boot2 p30 `179:30`, distinct from root p29 `179:29`;
  reviewed identity/inactive/unmounted/root/size/writability guards passed.
- Stable power observation `1|100|Good|1`.
- Full predecessor ND2
  `306ca76fb3136ec96f369bdce72ccbce52a10bd4b05d99f5b763938e551bc533` matched.
- Write, sync/flush and independent full 16 MiB readback matched ND3
  `7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06`.
- Clean shutdown confirmed; owner-operated physical boot2 selection requested.
- Derived installer
  `5d14b7bea446cc9e3a915cde34142d997fa569d4422fdf9d1c07e6cd243cffc8` passed
  custodian syntax/ShellCheck/normalized guard review.
- Real deployment receipt
  `7c26f6c7c4bb5764213ba3ddd68e39bd99f32ecfb5acf558f19d74b5033ec0dd`
  independently validated by the custodian and byte-copied to session-nd3.

The implementation author received these sanitized facts and identities, not
the raw private deployment receipt. No replacement receipt is fabricated.
Workers performed no device operation, credential access or private publication.

## Preflight, distinct from capture/session

Actual capture and session CLI preflights with the real receipt both exited
zero, without consuming either one-attempt claim. The fresh private runtime
root and strict `candidate-e25c1fa387f2be84908363a4e65f7e4b70ffea541684bccd991a4736f44980a6`
directory matched the bindings. This validates setup, not hardware Wi-Fi.

At this installation checkpoint, no ND3 capture/radio/session had run and no
fresh mainline boot identity was available to the author. The custodian must
verify that new identity before exactly one admitted capture/session, preserve
evidence, quiesce/seal, run regression and perform the one reviewed recovery
within its gates. Native firmware mode remains untested; installation and
preflight PASS are not runtime PASS. Later observations belong in a separate
attributable result, preserving this installation chronology.
