#!/usr/bin/env python3

# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import dataclasses
import enum
import fnmatch
import json
import os
import pathlib
import typing


@dataclasses.dataclass
class FirmwareTarget:
    architecture: str
    machines: list[str]

    @classmethod
    def from_json(cls, json):
        return cls(
            architecture=json['architecture'],
            machines=json['machines'],
        )


class FirmwareFlashMode(enum.Enum):
    SPLIT = 'split'
    COMBINED = 'combined'
    STATELESS = 'stateless'


@dataclasses.dataclass
class FirmwareFlashFile:
    filename: str
    format: str

    @classmethod
    def from_json(cls, json):
        return cls(
            filename=json['filename'],
            format=json['format'],
        )


@dataclasses.dataclass
class FirmwareMappingFlash:
    mode: FirmwareFlashMode
    executable: FirmwareFlashFile
    nvram_template: typing.Optional[FirmwareFlashFile]

    @classmethod
    def from_json(cls, json):
        return cls(
            mode=FirmwareFlashMode(json.get('mode', FirmwareFlashMode.COMBINED)),
            executable=FirmwareFlashFile.from_json(json['executable']),
            nvram_template=FirmwareFlashFile.from_json(json['nvram-template'])
            if 'nvram-template' in json
            else None,
        )


@dataclasses.dataclass
class FirmwareMappingMemory:
    filename: str

    @classmethod
    def from_json(cls, json):
        return cls(filename=json['filename'])


@dataclasses.dataclass
class FirmwareMapping:
    device: str

    @classmethod
    def from_json(cls, json):
        if json['device'] == 'flash':
            return FirmwareMappingFlash.from_json(json)
        if json['device'] == 'memory':
            return FirmwareMappingMemory.from_json(json)
        raise ValueError(json)


@dataclasses.dataclass
class Firmware:
    description: str
    interface_types: list[str]
    features: list[str]
    tags: list[str]
    targets: list[FirmwareTarget]
    mapping: FirmwareMapping
    json_path: typing.Optional[pathlib.Path] = None

    @classmethod
    def from_json(cls, json):
        return cls(
            description=json['description'],
            interface_types=json['interface-types'],
            features=json['features'],
            tags=json['tags'],
            targets=[FirmwareTarget.from_json(j) for j in json['targets']],
            mapping=FirmwareMapping.from_json(json['mapping']),
        )


@dataclasses.dataclass
class FeatureMatcher:
    required_values: set[str]
    forbidden_values: set[str]

    @classmethod
    def from_string(cls, s):
        required_values = []
        forbidden_values = []

        for value in s.split(' '):
            value = value.strip()
            if value.startswith('!'):
                forbidden_values.append(value[1:])
            else:
                required_values.append(value)

        return cls(required_values=set(required_values),
                   forbidden_values=set(forbidden_values))

    def is_satisfied_by(self, available_values):
        if not set(self.required_values).issubset(available_values):
            return False

        if not set(self.forbidden_values).isdisjoint(available_values):
            return False

        return True


@dataclasses.dataclass
class SearchRequest:
    architecture: str
    machine: str
    interface_types: FeatureMatcher
    features: FeatureMatcher

    def _matches_target(self, target):
        if self.architecture != target.architecture:
            return False

        for machine in target.machines:
            if fnmatch.fnmatch(self.machine, machine):
                return True

        return False

    def matches(self, firmware):
        if not self.interface_types.is_satisfied_by(firmware.interface_types):
            return False

        if not self.features.is_satisfied_by(firmware.features):
            return False

        if not any([self._matches_target(target) for target in firmware.targets]):
            return False

        return True


class FirmwareSearcher:
    def __init__(self):
        self.search_dirs = self._get_search_dirs()
        self.filenames = self._get_filenames(self.search_dirs)

    @staticmethod
    def _get_search_dirs() -> list[pathlib.Path]:
        search_dirs = []

        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config_home is not None:
            search_dirs.append(
                pathlib.Path(xdg_config_home).joinpath('qemu', 'firmware')
            )
        else:
            search_dirs.append(
                pathlib.Path.home().joinpath('.config', 'qemu', 'firmware')
            )

        search_dirs.append(pathlib.Path('/etc/qemu/firmware'))

        for d in os.environ.get('XDG_DATA_DIRS', '/usr/local/share/:/usr/share/').split(
            ':'
        ):
            search_dirs.append(pathlib.Path(d).joinpath('qemu', 'firmware'))

        return search_dirs

    @staticmethod
    def _get_filenames(search_dirs: list[pathlib.Path]) -> list[str]:
        filenames = set()

        for search_dir in search_dirs:
            if not search_dir.exists() or not search_dir.is_dir():
                continue

            for entry in search_dir.iterdir():
                filenames.add(entry.name)

        return sorted(filenames)

    def _search_for_filename(self, filename, request):
        for search_dir in self.search_dirs:
            path = search_dir.joinpath(filename)

            if not path.exists():
                continue

            if path.stat().st_size == 0:
                return

            with path.open('r') as f:
                j = json.load(f)

            fw = Firmware.from_json(j)
            if request.matches(fw):
                fw.json_path = path
                return fw

    def search(self, request):
        for filename in self.filenames:
            fw = self._search_for_filename(filename, request)
            if fw is not None:
                return fw


if __name__ == '__main__':
    searcher = FirmwareSearcher()
    request = SearchRequest(
        architecture='x86_64',
        machine='pc-q35-foo',
        interface_types=FeatureMatcher.from_string('uefi !bios'),
        features=FeatureMatcher.from_string('!requires-smm'),
    )
    print(searcher.search(request))
