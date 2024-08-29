# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import json
import pathlib
import tempfile
import uuid
import warnings

import jsonschema

try:
    import jsonschema._validators

    def _extras_msg(extras):
        verb = 'was' if len(extras) == 1 else 'were'
        return ', '.join(repr(extra) for extra in extras), verb

    # jsonschema before commit 8cff13d0e8b
    # ("Fix items/prefixItems' message when used with heterogeneous arrays.")
    # Tries to sort arrays, which does not work with our arrays of dicts.
    # Override it with a non-sorting variant.
    jsonschema._validators.extras_msg = _extras_msg
except ImportError:
    pass

# RefResolver is deprecated in newer versions of 'jsonschema',
# But we need it for comaptibility with the versions in Debian.
# Also, as long as it works...
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', 'jsonschema.RefResolver', DeprecationWarning)
    from jsonschema.validators import RefResolver


from elbepack.main import run_elbe_subcommand

here = pathlib.Path(__file__).parent


def generate_test_bom():
    source_dir = here.joinpath('build-simple-example')
    mapping_file = here.joinpath('example-mapping.xml')
    with tempfile.NamedTemporaryFile() as output, \
         tempfile.NamedTemporaryFile('r') as errors:
        run_elbe_subcommand([
            'cyclonedx-sbom', '--output', output.name,
            '--errors', errors.name,
            '-m', mapping_file, '-d', source_dir,
        ])
        output.seek(0)
        return json.load(output), errors.read()


def test_schema():
    test_bom, _ = generate_test_bom()
    with here.joinpath('bom-1.6.schema.json').open() as f:
        bom_schema = json.load(f)
    with here.joinpath('spdx.schema.json').open() as f:
        spdx_schema = json.load(f)
    resolver = RefResolver.from_schema(bom_schema, store={
        'http://cyclonedx.org/schema/spdx.schema.json': spdx_schema,
    })
    jsonschema.validate(test_bom, bom_schema, resolver=resolver)


def test_reference_data():
    test_bom, error_report = generate_test_bom()
    test_bom['metadata']['timestamp'] = '0001-01-01T00:00:00+00:00'
    test_bom['serialNumber'] = uuid.UUID(int=0).urn
    test_bom['metadata']['tools'][0]['version'] = 'INVALID'
    with here.joinpath('cyclonedx_reference.json').open() as f:
        reference_data = json.load(f)

    assert test_bom == reference_data

    reference_errors = here.joinpath('cyclonedx_reference.json.errors').read_text()
    assert error_report == reference_errors
