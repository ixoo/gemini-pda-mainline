#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the passive CONN-provider image."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_installer', SOURCE)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-conn-provider-passive'
INSTALLER.RECEIPT_NAME = 'mt6797-conn-provider-passive-deployment-1'
INSTALLER.MANIFEST_SHA = '8ef25dba9d8e36ef11be597588adf1456d731a78f73fc97b368d312261bb40a4'
PREDECESSOR_SHA = '9483e4bc1bb1882052a0158a024ddf20bff9018440aaa03b4a9bd3ad3abfc2de'
ORIGINAL_ADAPT = INSTALLER.adapt


def adapt(source, candidate, previous):
    source = ORIGINAL_ADAPT(source, candidate, previous)
    anchor = 'already_current="$(single_value already_current "$probe_output")" || die '\
             "'invalid current-state evidence'\n"
    if source.count(anchor) != 1:
        raise ValueError('predecessor-check anchor changed')
    return source.replace(anchor, '[[ "$predecessor_sha256" == ' + PREDECESSOR_SHA +
                          " ]] || die 'unexpected boot2 predecessor'\n" + anchor)


INSTALLER.adapt = adapt
MANIFEST_SHA = INSTALLER.MANIFEST_SHA
validate = INSTALLER.validate
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
