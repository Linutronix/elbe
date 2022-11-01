# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from urwid import (
    Edit,
    Filler,
    IntEdit,
    WidgetDecoration,
    emit_signal
)

from elbepack.debianize.base.tui import TUISignal
from elbepack.debianize.base.tui import TUI
from elbepack.debianize.widgets.button import Button
from elbepack.debianize.widgets.grid import Grid


WidgetDecoration.get_data = lambda wrapped_widget: wrapped_widget.base_widget.get_data()
Edit.get_data = Edit.get_edit_text
IntEdit.get_data = IntEdit.value


class Form(Grid):

    signals = [TUISignal.QUIT]

    def __init__(self, named_grid_elements):
        self.named_widgets = {}
        unnamed_grid_elements = []
        for row in named_grid_elements:
            self.named_widgets.update(row)
            unnamed_grid_elements.append(list(row.values()))

        confirm = Button("Confirm", "confirm_button", self.confirm)
        abort = Button("Abort", "abort_button", self.abort)
        unnamed_grid_elements.append([confirm, abort])

        super(Form, self).__init__(unnamed_grid_elements)
        self.root = Filler(self, valign="top")

        self.keybind["f5"] = self.confirm
        self.keybind["f10"] = self.abort

    def confirm(self):
        data = self.get_form_data()
        sanitize = self.sanitize_inputs(data)
        if sanitize:
            # TODO - Better sanitization handling
            buf = []
            for key, value in sanitize.items():
                buf.append(f"{key}: {value}")
            TUI.printf('\n'.join(buf))
        else:
            self.on_submit(data)

    def abort(self):
        emit_signal(self, TUISignal.QUIT)
        TUI.quit()

    def get_form_data(self):
        return {name: widget.get_data() for name, widget in self.named_widgets.items()}

    def on_submit(self, data):
        raise Exception("Form can not submit")

    def sanitize_inputs(self, data):
        return False
