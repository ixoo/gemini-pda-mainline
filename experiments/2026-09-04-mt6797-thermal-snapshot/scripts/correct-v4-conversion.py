#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate a narrowly scoped V4 correction from one pinned production file."""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA = 'e2ce72fa105be597a5c7a3cea37499512093c86ba4cc4ac85b92c10b0254c481'


def function(source, name):
    start = source.index('static int ' + name + '(')
    end = source.index('\n}', start) + 2
    return source[start:end]


def corrected(source):
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA:
        raise ValueError('production source identity mismatch')
    old = function(source, 'raw_to_mcelsius_v4')
    new = old.replace('s64 gain, x_roomt, measured, delta, slope_denominator;',
                      's64 gain, x_roomt, measured, delta, slope_denominator;\n\ts64 offset = mt->adc_oe - 512;\n\tint vts_index;\n\n\tif (sensno < 0 || sensno >= mt->conf->num_sensors)\n\t\treturn THERMAL_TEMP_INVALID;\n\tvts_index = mt->conf->vts_index[sensno];')
    new = new.replace('mt->vts[sensno]', 'mt->vts[vts_index]')
    # Keep raw register masking and signed-shift rounding unchanged.
    new = new.replace('3350 - mt->adc_oe', '3350 - offset')
    new = new.replace('(s64)raw - mt->adc_oe', '(s64)raw - offset')
    if new == old or source.count(old) != 1:
        raise ValueError('conversion edit mismatch')
    return source.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.is_symlink():
        raise ValueError('symlinked source')
    result = corrected(args.source.read_text())
    with args.output.open('x') as stream:
        stream.write(result)


if __name__ == '__main__':
    main()
