# Independent canonical freeze

Declared after the design JSON was complete and before construction of the
offline verifier. Canonical JSON uses sorted keys, compact separators and ASCII
escaping, then SHA-256.

| Object | Canonical SHA-256 |
| --- | --- |
| `inputs.json` | `a82211e63b3d84b4114ec4c05109c3f39f173e11a3263a54ce9aaa9ae7d2d80b` |
| `decisions.json` | `f3a5155184ca713c96145bbe1a3d8a3e3639734b527d79b6bd6d29700c15696f` |
| `state-model.json` | `a05217eae1da5f1065048179ae061e1003656cc2a30cf824650c9fb9b8ecdd19` |
| `proposal-map.json` | `2ab26995d3a5407496c7221ba631d51b8722c7769aa3e2901adec71268dff3a8` |

Literal independent expectations used by the verifier:

- repository parent `7daaf3811a95e7187bd378e0ce345bf4b536630c`;
- 42 frozen local inputs, zero additional Linux inspections;
- eight decisions, fifteen states, thirty-two transitions and nine typed
  error rows;
- twelve ordered Wi-Fi proposal entries plus three separately classified
  `0001` companions; and
- zero runtime-ready, upstream-submission-ready or userspace-ABI proposal
  entries.

The freeze does not claim that design prose, compilation or a passing verifier
implements hardware behavior.
