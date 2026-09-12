#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate bound A53 RAM-session scripts offline; never invoke device access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts'
RELEASE = '7.1.3-gemini-a53-service-facilities'
SOURCE_PINS = {
    'collect-baseline.py': 'efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf',
    'session_steps.py': '762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc',
    'finish-baseline.py': 'f4fc22f6de7456e9c5e3336fd76114151492414d4c09356cda77b2a9d35a6708',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def boot_uuid(value):
    parsed = uuid.UUID(value)
    require(parsed.int != 0 and str(parsed) == value, 'canonical nonzero boot UUID required')
    return value


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(candidate_dir, previous):
    """Bind existing script generators and classifiers to verified new inputs."""
    boot_uuid(previous)
    for name, expected in SOURCE_PINS.items():
        require(digest((BASELINE / name).read_bytes()) == expected, 'session source changed: ' + name)
    collector = load_module('a53_service_collector', BASELINE / 'collect-baseline.py')
    collector.source_tools()  # Verify every transitive historical source pin first.
    legacy = load_module('a53_service_observation', collector.HISTORICAL / 'classify_observation.py')
    legacy.RELEASE = RELEASE
    # This instance alone changes the release expected by the existing classifier.
    collector.source_tools = lambda: vars(legacy)
    steps = load_module('a53_service_steps', BASELINE / 'session_steps.py')
    steps.RELEASE = RELEASE
    finish = load_module('a53_service_finish', BASELINE / 'finish-baseline.py')
    candidate_dir = Path(os.path.abspath(candidate_dir))
    collector.directory(candidate_dir)
    receipt = json.loads((HERE / 'results/a53-service-ram-candidate.json').read_text())
    require(receipt['kernel_release'] == RELEASE and receipt['physical_admission'] is False,
            'unexpected composition receipt')
    expected_files = receipt['files']
    require({p.name for p in candidate_dir.iterdir()} == set(expected_files) | {'candidate.json'},
            'candidate inventory mismatch')
    for name, expected in expected_files.items():
        data = collector.regular(candidate_dir / name, 16777216)
        require(len(data) == expected['bytes'] and digest(data) == expected['sha256'],
                'candidate file identity mismatch: ' + name)
    recipe = HERE / 'build-a53-ram-candidate.py'
    require(digest(recipe.read_bytes()) == receipt['recipe_sha256'], 'composition recipe changed')
    builder = load_module('a53_service_builder', recipe)
    for path, expected in builder.TOOLS.items():
        require(digest(path.read_bytes()) == expected, 'composition dependency changed')
    old_builder = load_module('a53_parent_builder', builder.BASELINE / 'scripts/build-candidate.py')
    parse, _ = old_builder.parser_tools()
    members = parse(collector.regular(candidate_dir / 'initramfs.img', 16777216))
    require(len(members) == 47 and digest(members['init'].data) == receipt['init_sha256'],
            'RAM environment differs')
    candidate = {'files': {name: value['sha256'] for name, value in expected_files.items()},
                 'members': {name: {'sha256': digest(member.data), 'size': len(member.data),
                                    'mode': oct(member.mode)} for name, member in members.items()}}
    context = {'candidate': candidate, 'recovery_id': previous,
               'admission': {'candidate_sha256': expected_files['boot.img']['sha256']}}
    return context, collector, steps, finish


def scripts(context, collector, steps, boot):
    boot_uuid(boot)
    require(boot != context['recovery_id'], 'mainline and preceding Gemian boot IDs must differ')
    return {'observe.sh': collector.remote_script(context),
            'probe.sh': steps.probe_script(context['candidate'], boot),
            'seal.sh': steps.seal_script(context['candidate'], boot),
            'recovery.sh': steps.recovery_script(context['candidate'], boot)}


def classify_observation(context, collector, stdout, stderr, process):
    result = collector.classify_capture(context, stdout, stderr, process)
    if result['classification'] == 'baseline-observation-only-pass':
        boot_uuid(result['boot_id'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--previous-gemian-boot', required=True)
    parser.add_argument('--mainline-boot', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    context, collector, steps, _ = prepare(args.candidate, args.previous_gemian_boot)
    generated = scripts(context, collector, steps, args.mainline_boot)
    output = Path(os.path.abspath(args.output))
    for path in (output, *output.parents):
        require(not path.is_symlink(), 'symlink output path')
    output.mkdir(mode=0o700)  # Never overwrite a prior bound script bundle.
    for name, data in generated.items():
        collector.write_new(output / name, data)
    receipt = {'status': 'offline-script-generation-only', 'kernel_release': RELEASE,
               'candidate_sha256': context['admission']['candidate_sha256'],
               'previous_gemian_boot': args.previous_gemian_boot,
               'mainline_boot': args.mainline_boot,
               'generator_sha256': digest(Path(__file__).read_bytes()),
               'source_sha256': SOURCE_PINS,
               'scripts_sha256': {name: digest(data) for name, data in generated.items()},
               'network_access': 'none', 'device_action': 'none', 'physical_admission': False,
               'identity_warning': 'Supplied UUIDs are bindings, not observations; live execution requires verified deployment, observed identity and the finite session protocol.'}
    collector.write_new(output / 'scripts.json', (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
