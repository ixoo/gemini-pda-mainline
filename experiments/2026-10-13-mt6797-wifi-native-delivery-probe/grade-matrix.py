#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Grade one measurement boot's lifetimes from the artefacts, not from memory.

Reads a session directory and prints one row per lifetime: the testcfg
configuration the driver applied, the harness's per-direction chunk
rates from the receipt, and the driver's link-level facts. A lifetime is
graded on what the link actually carried, because the software-frame
refusal count is not an air measure: boot AU refused 204-292 per
lifetime while the link moved 16-32 Mbit/s.

Usage:
  grade-matrix.py <session directory> [--band-tx Mbit/s] [--band-rx Mbit/s]

The bands are per association width, from THROUGHPUT_SERIES_RESULT: at
20 MHz the boots AA3/AA4 best of 22.6 transmit and 20.5 receive, at 40 MHz
boot AV's fixed MCS5 of about 30 and 36. The boot's width is the control
lifetime's, from its applied line (rxbw=, or bw= before 0331); a boot
without driver lines is graded at 20 MHz. --band-tx and --band-rx
override the table. The percentages and the control check use the
boot's band, so a 40 MHz regression shows; a lifetime is void only below
VALID_FRACTION of the 20 MHz band, the floor that says the link worked at
all. The rules are stated, not applied silently.
"""
import argparse
import json
import re
from pathlib import Path

VALID_FRACTION = 0.5          # below this share of the band a lifetime is void
# Transmit and receive bands (Mbit/s) by association width (MHz).
BANDS = {20: (22.6, 20.5), 40: (30.0, 36.0)}


def boot_width(driver):
    """The control lifetime's association width from its applied line."""
    for index in sorted(driver):
        m = re.search(r'\b(?:rx)?bw=(20|40)\b', driver[index].get('rest', ''))
        if m:
            return int(m.group(1))
    return 20


def receipt_lifetimes(session):
    """Per-lifetime directions from the receipt, in cycle order."""
    path = session / 'ccmp-session-result.json'
    if not path.exists():
        return {}
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    receipt = document.get('wifi_ssh_receipt') or {}
    measurement = receipt.get('throughput_measurement') or {}
    per_cycle = measurement.get('per_cycle') or {}
    if not per_cycle and measurement.get('directions'):
        # The throughput harness measures one configuration, not a cycle matrix.
        per_cycle = {'1': measurement}
    out = {}
    for cycle, entry in per_cycle.items():
        try:
            index = int(cycle)
        except (TypeError, ValueError):
            continue
        directions = entry.get('directions') or {}
        row = {}
        for name in ('TX', 'RX'):
            chunks = [c.get('Mbit_s') for c in (directions.get(name) or {}).get('chunks') or []
                      if c.get('Mbit_s')]
            row[name] = chunks
        out[index] = row
    return out


def driver_lifetimes(session):
    """testcfg lines from the kernel log: configuration and link facts."""
    log = None
    for candidate in session.glob('kmsg.log'):
        log = candidate
        break
    if log is None:
        return {}
    applied, stats = {}, {}
    for line in log.read_text(errors='ignore').splitlines():
        if 'testcfg:' in line and 'lifetime=' in line:
            m = re.search(r'lifetime=(\d+) entry=(\d+) config=(\S+)(.*)', line)
            if m:
                applied[int(m.group(1))] = {
                    'entry': int(m.group(2)),
                    'config': m.group(3),
                    'rest': m.group(4).strip(),
                }
        elif 'testcfg stats:' in line and 'lifetime=' in line:
            m = re.search(r'lifetime=(\d+) config=(\S+)(.*)', line)
            if m:
                fields = dict(re.findall(r'(\w+)=(\S+)', m.group(3)))
                stats[int(m.group(1))] = {'config': m.group(2), **fields}
    out = {}
    for index in sorted(set(applied) | set(stats)):
        out[index] = {**applied.get(index, {}), **stats.get(index, {})}
    return out


def mean(values):
    return sum(values) / len(values) if values else 0.0


def grade(session, band_tx, band_rx):
    receipt = receipt_lifetimes(session)
    driver = driver_lifetimes(session)
    if not receipt and not driver:
        print(f"{session}: no per-lifetime data (throughput harness or sealed away)")
        return 1
    width = boot_width(driver)
    band_tx = band_tx or BANDS[width][0]
    band_rx = band_rx or BANDS[width][1]
    print(f"{session.name}: graded against the {width} MHz association's band")
    header = (f"{'life':5}{'config':16}{'TX chunks':22}{'RX chunks':22}"
              f"{'TX %':>7}{'RX %':>7}{'rate words':>22}{'refused':>9}  verdict")
    print(header)
    print('-' * len(header))
    for index in sorted(set(receipt) | set(driver)):
        tx = receipt.get(index, {}).get('TX') or []
        rx = receipt.get(index, {}).get('RX') or []
        d = driver.get(index, {})
        config = d.get('config') or '-'
        tx_share = 100 * mean(tx) / band_tx if tx else 0
        rx_share = 100 * mean(rx) / band_rx if rx else 0
        shares = [s for s in (tx_share, rx_share) if s]
        if not shares:
            verdict = 'unmeasured'
        elif min(s * b / f for s, b, f in zip((tx_share, rx_share), (band_tx, band_rx), BANDS[20])
                 if s) >= 100 * VALID_FRACTION:
            verdict = 'valid'
        else:
            verdict = f'void (<{int(100 * VALID_FRACTION)}% of the 20 MHz band)'
        print(f"{index:<5}{config:16}"
              f"{','.join(f'{v:.1f}' for v in tx) or '-':22}"
              f"{','.join(f'{v:.1f}' for v in rx) or '-':22}"
              f"{tx_share:7.0f}{rx_share:7.0f}"
              f"{d.get('rates', '-'):>22}{d.get('rx_refused', '-'):>9}  {verdict}")
    print()
    print(f"bands: TX {band_tx:.1f}, RX {band_rx:.1f} Mbit/s; a lifetime is void "
          f"below {int(100 * VALID_FRACTION)} % of either 20 MHz band "
          f"({BANDS[20][0]:.1f}, {BANDS[20][1]:.1f}).")
    # The band says whether the link worked at all; the control leg says whether
    # this boot's air can support a comparison between its other lifetimes.
    control = None
    for index in sorted(receipt):
        if (driver.get(index) or {}).get('config') in ('default', '-') or index == min(receipt):
            control = index
            break
    if control is not None:
        tx = receipt.get(control, {}).get('TX') or []
        rx = receipt.get(control, {}).get('RX') or []
        shares = [s for s in (100 * mean(tx) / band_tx if tx else 0,
                              100 * mean(rx) / band_rx if rx else 0) if s]
        if shares and min(shares) < 80:
            print(f"air below band: control lifetime {control} ran at "
                  f"{min(shares):.0f} % of its band; compare this boot's lifetimes "
                  f"with each other only, not with the standing band.")
        else:
            print(f"control lifetime {control} is within the band; this boot's "
                  f"lifetimes are comparable with the standing band.")
    print("The software-frame refusal count is printed for the record and is not a"
          " gate: it tracked 204-292 per lifetime on a link at 16-32 Mbit/s (boot AU).")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--band-tx', type=float, default=None)
    parser.add_argument('--band-rx', type=float, default=None)
    args = parser.parse_args()
    raise SystemExit(grade(args.session, args.band_tx, args.band_rx))
