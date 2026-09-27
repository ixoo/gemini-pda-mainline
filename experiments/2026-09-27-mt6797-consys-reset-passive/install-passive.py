#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the passive CONMCU reset image."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_installer', SOURCE)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-consys-reset-passive'
INSTALLER.RECEIPT_NAME = 'mt6797-consys-reset-passive-deployment-1'
INSTALLER.MANIFEST_SHA = 'f75ef78fd3f5adaec6dd2b2c74b5216e59800b43cdd3ed319453cd79d699c10e'
PREDECESSOR_SHA = '34b56a58abe0932d1e7374ed7e668487518fa9d6067a9bf6d60c19d313780020'
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
