# -*- coding: utf-8 -*-
# AUTHOR: RaNaN


class Handler:
    def __init__(self, cli):
        self.cli = cli
        self.init()

    client = property(lambda self: self.cli.client)
    input = property(lambda self: self.cli.input)

    def init(self):
        pass

    def on_char(self, char):
        pass

    def on_back_space(self):
        pass

    def on_enter(self, inp):
        pass

    def set_input(self, inp=""):
        self.cli.set_input(inp)

    def backspace(self):
        self.cli.set_input(self.input[:-1])

    def render_body(self, line):
        """
        gets the line where to render output and should return the line number below its
        content.
        """
        return line + 1
