# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from urwid import (
    LineBox,
    RadioButton,
    Text
)

from elbepack.debianize.widgets.grid import Grid


class RadioPolicy(object):
    HORIZONTAL = 0
    VERTICAL   = 1


class RadioGroup(Grid):
    def __init__(self, title, enum_type, starting_value, policy=RadioPolicy.VERTICAL):
        self.selected_value = starting_value
        self.enum_type = enum_type

        self.radio_group = []
        for choice in enum_type.__dict__.keys():
            if choice.startswith('_'):
                continue
            RadioButton(self.radio_group,
                        label=choice.capitalize(),
                        state=choice == starting_value)

        rows = [
            [Text(("header", title))]
        ]

        if policy is RadioPolicy.VERTICAL:
            for radio in self.radio_group:
                rows.append([radio])
        else:
            col = []
            for radio in self.radio_group:
                col.append(radio)
            rows.append(col)

        super(RadioGroup, self).__init__(rows)
        self._w = LineBox(self._w)

    def get_data(self):
        for radio in self.radio_group:
            if radio.state:
                return self.enum_type.__dict__[radio.label.upper()]
