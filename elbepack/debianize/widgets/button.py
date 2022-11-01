# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from urwid import (
    AttrMap,
    LineBox,
    Text,
    WidgetWrap,
    connect_signal,
    emit_signal
)

from elbepack.debianize.base.tui import TUISignal


class Button(WidgetWrap):
    """
    A simple and clean button widget
    """

    signals = [TUISignal.CLICK]

    def __init__(self, text, palette, callback):
        """
        @text:  The text of show in the button.
        @palette:  A valid palette name to apply on the button.  See @TUI::palette
        @callback:  The callback to call when the button is clicked.
        """

        widget = LineBox(AttrMap(Text(f"[{text}]", align="center"),
                                 "default", palette))
        super(Button, self).__init__(widget)
        connect_signal(self, TUISignal.CLICK, callback)

        # Very important!  This is not documented in urwid's
        # documentation!  Without this, the button would only text.
        self._w.base_widget._selectable = True

    def keypress(self, size, key):
        if key == "enter":
            emit_signal(self, TUISignal.CLICK)
            return None
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if focus and event == "mouse release":
            emit_signal(self, TUISignal.CLICK)
            return True
        return False
