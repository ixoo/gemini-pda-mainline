#!/usr/bin/env python3
"""Compare the recovered MT6797 formula with Linux's generic V1 formula.

The defaults are the sanitized calibration values recorded in the experiment
and contain no device identifier.  This is arithmetic only; it never reads
the device or a source tree.
"""

from __future__ import annotations

import argparse


DEFAULT_VTS = (155, 138, 133, 133, 129)
DEFAULT_RAWS = (500, 1000, 2000, 2500, 3000, 3500, 4095)


def cdiv(numerator: int, denominator: int) -> int:
    """C integer division (truncate toward zero), unlike Python //."""

    if denominator == 0:
        raise ZeroDivisionError("thermal formula denominator is zero")
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def vendor_raw_to_mcelsius(raw: int, vts: int, adc_ge: int, adc_oe: int,
                           degc_cali: int, slope: int) -> int:
    """MT6797 vendor raw_to_temperature_roomt(), in milli-degrees C."""

    if raw == 0:
        return 0

    g_ge = cdiv((adc_ge - 512) * 10000, 4096)
    g_oe = adc_oe - 512
    g_gain = 10000 + g_ge
    x_roomt = cdiv(
        cdiv((vts + 3350 - g_oe) * 10000, 4096) * 10000,
        g_gain,
    )
    format_1 = (degc_cali * 10) >> 1
    format_2 = cdiv((((raw - g_oe) * 10000) >> 12) * 10000, g_gain)
    format_3 = cdiv((format_2 - x_roomt) * 15, 18)
    denominator = 1663 + slope * 10
    format_4 = cdiv(format_3 * 1000, denominator)
    format_4 -= 2 * format_4
    return (format_1 + format_4) * 100


def mainline_v1_raw_to_mcelsius(raw: int, vts: int, adc_ge: int,
                                 degc_cali: int, cali_val: int,
                                 slope: int) -> int:
    """Linux auxadc_thermal.c raw_to_mcelsius_v1(), in milli-degrees C."""

    raw &= 0xFFF
    tmp = 203450520 << 3
    tmp = cdiv(tmp, cali_val + slope)
    tmp = cdiv(tmp, 10000 + adc_ge)
    tmp *= raw - vts - 3350
    tmp >>= 3
    return degc_cali * 500 - tmp


def parse_int_list(value: str, expected: int | None = None) -> tuple[int, ...]:
    values = tuple(int(item, 0) for item in value.split(",") if item)
    if expected is not None and len(values) != expected:
        raise argparse.ArgumentTypeError(
            f"expected {expected} comma-separated values, got {len(values)}"
        )
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adc-ge", type=int, default=587)
    parser.add_argument("--adc-oe", type=int, default=516)
    parser.add_argument("--degc-cali", type=int, default=55)
    parser.add_argument("--slope", type=int, default=0)
    parser.add_argument("--mainline-cali-val", type=int, default=165)
    parser.add_argument(
        "--vts",
        type=lambda value: parse_int_list(value, expected=5),
        default=DEFAULT_VTS,
        help="five VTS values, comma separated (default: sanitized live values)",
    )
    parser.add_argument(
        "--raws",
        type=lambda value: parse_int_list(value),
        default=DEFAULT_RAWS,
        help="raw ADC values, comma separated",
    )
    args = parser.parse_args()

    maximum = 0
    print(
        "calibration="
        f"GE={args.adc_ge},OE={args.adc_oe},DEGC={args.degc_cali},"
        f"slope={args.slope},VTS={','.join(map(str, args.vts))}"
    )
    print("raw sensor vendor_mcelsius mainline_v1_mcelsius delta_mcelsius")
    for raw in args.raws:
        for sensor, vts in enumerate(args.vts):
            vendor = vendor_raw_to_mcelsius(
                raw, vts, args.adc_ge, args.adc_oe, args.degc_cali, args.slope
            )
            mainline = mainline_v1_raw_to_mcelsius(
                raw, vts, args.adc_ge, args.degc_cali,
                args.mainline_cali_val, args.slope
            )
            delta = vendor - mainline
            maximum = max(maximum, abs(delta))
            print(f"{raw} {sensor} {vendor} {mainline} {delta}")
    print(f"max_abs_delta_mcelsius={maximum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
