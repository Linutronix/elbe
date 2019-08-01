# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import os
import signal

from urwid import (
    ExitMainLoop,
    Frame,
    MainLoop,
    Text
)


# +=====================================================+
# |+-: root (box) -------------------------------------+|
# ||+-: header (flow) --------------------------------+||
# |||                                                 |||
# ||+-------------------------------------------------+||
# ||+-: body (box) -----------------------------------+||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# |||                                                 |||
# ||+-------------------------------------------------+||
# ||+-: helper (flow) --------------------------------+||
# |||                                                 | |
# ||+-------------------------------------------------+||
# |+---------------------------------------------------+|
# +=====================================================+


def generate_helper_text(hints):
    markup = []
    for key, text, text_palette in hints:
        markup.extend((("helper_key", key), " ", (text_palette, text), " "))
    return markup


class TUISignal(object):
    QUIT = "on_quit"
    CLICK = "on_click"
    FLUSH = "on_flush"

class TUIException(Exception):
    pass


class TUI(object):

    palette = [
        ("blue_head", "dark blue", ""),
        ("red_head", "dark red", ""),
        ("header", "bold, underline, default", ""),
        ("error", "bold, light red", ""),
        ("normal_box", "default", "default"),
        ("selected_box", "black", "light gray"),
        ("confirm_button", "default", "dark green"),
        ("abort_button", "light red", "dark red"),
        ("progress_low", "default", "yellow"),
        ("progress_hight", "default", "dark green"),
        ("helper_key", "bold", "default"),
        ("helper_text_brown", "black", "brown"),
        ("helper_text_red", "black", "dark red"),
        ("helper_text_green", "black", "dark green"),
        ("helper_text_light", "white", "dark blue"),
    ]

    main_helper_text = generate_helper_text([
        ("C-f", "Forward", "helper_text_brown"),
        ("C-b", "Backward", "helper_text_brown"),
        ("C-p", "Previous", "helper_text_brown"),
        ("C-n", "Next", "helper_text_brown"),
        ("TAB", "Next", "helper_text_brown"),
        ("backtab", "Previous", "helper_text_brown"),
        ("C-\\", "Quit", "helper_text_red"),
    ])

    keybind = {}

    def __init__(self, body):

        TUI.root = Frame(body.root,
                         Text(("header", ""), "center"),
                         Text(TUI.main_helper_text, "center"))

        TUI.loop = MainLoop(TUI.root, TUI.palette,
                            unhandled_input=TUI.unhandled_input)

        TUI.install_signals_handler()

    def __call__(self):
        TUI.loop.run()

    @classmethod
    def focus_header(cls):
        cls.root.focus_position = "header"

    @classmethod
    def focus_body(cls):
        cls.root.focus_position = "body"

    @classmethod
    def focus_footer(cls):
        cls.root.focus_position = "footer"

    @classmethod
    def header(cls, flow_widget=None):
        if flow_widget is not None:
            if "flow" not in flow_widget.sizing():
                raise TUIException("Header must be of sizing flow")
            cls.root.contents["header"] = flow_widget
        return cls.root.contents["header"]

    @classmethod
    def body(cls, box_widget=None):
        if box_widget is not None:
            if "box" not in box_widget.sizing():
                raise TUIException("Body must be of sizing box")
            cls.root.contents["body"] = (box_widget, TUI.root.options())
        return cls.root.contents["body"]

    @classmethod
    def footer(cls, flow_widget=None):
        if flow_widget is not None:
            if "flow" not in flow_widget.sizing():
                raise TUIException("Header must be of sizing flow")
            cls.root.contents["footer"] = flow_widget
        return cls.root.contents["footer"]

    @classmethod
    def unhandled_input(cls, key):
        if key in cls.keybind:
            cls.keybind[key]()
            return None

    @classmethod
    def bind_global(cls, key, callback):
        cls.keybind[key] = callback

    @classmethod
    def printf(cls, fmt, *args):
        cls.header()[0].set_text(("header", fmt.format(*args)))

    @classmethod
    def clear(cls):
        cls.printf("")

    @staticmethod
    def quit(*args):
        raise ExitMainLoop()

    @staticmethod
    def pause(*args):
        TUI.loop.stop()
        os.kill(os.getpid(), signal.SIGSTOP)
        TUI.loop.start()
        TUI.loop.draw_screen()

    @staticmethod
    def interrupt(*kargs):
        pass

    @staticmethod
    def install_signals_handler():

        if os.sys.platform != "win32":
            signal.signal(signal.SIGQUIT, TUI.quit)
            signal.signal(signal.SIGTSTP, TUI.pause)

        signal.signal(signal.SIGINT, TUI.interrupt)
