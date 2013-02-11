"""Change-requests handling"""

import re


class ChangeRequest(object):
    """
    Class to represent and handle change requests.

    Attributes of a ChangeRequest:
        cr_n - (logic clock) number of this change-request
        pos - position of the edit
        op - edit operation (+ / -)
        delta - number of modified characters
        value - actual edit data (empty for deletions)
    """

    def __init__(self, author='', cr_n=0, pos=0, delta=0, op=0, value=''):
        super(ChangeRequest, self).__init__()

        self.author, self.cr_n, self.pos, self.delta, self.op, self.value =\
            author, cr_n, pos, delta, op, value

    # Edit types
    ADD_EDIT = 0
    DEL_EDIT = 1

    def serialize(self):
        """Produces a string that encodes the CR"""
        parts = {}
        parts['op'] = '-'
        if self.op == ChangeRequest.ADD_EDIT:
            parts['op'] = '+'
        # TODO: Encode numbers in a higher base (36)
        parts['auth'] = self.author
        parts['cr_n'] = str(self.cr_n)
        parts['pos'] = str(self.pos)
        parts['delta'] = str(self.delta)
        parts['content'] = self.value

        return "%(auth)s:%(cr_n)s:%(pos)s%(op)s%(delta)s:%(content)s:" % parts

    def deserialize(self, edit):
        pattern = re.compile(
            r'(?P<auth>.+?):(?P<cr>-?[0-9]+?):(?P<pos>[0-9]+?)(?P<op>[+-]?)(?P<delta>[0-9]+?):(?P<data>.*?):'
        )
        sections = re.search(pattern, edit).groups()

        op = ChangeRequest.DEL_EDIT
        if sections[3] == '+':
            op = ChangeRequest.ADD_EDIT

        self.author = sections[0]
        self.cr_n = int(sections[1])
        self.pos = int(sections[2])
        self.delta = int(sections[4])
        self.op = op
        self.value = sections[5]

    def apply_over(self, instr):
        if self.op == ChangeRequest.ADD_EDIT:
            head = instr[:self.pos]
            tail = instr[self.pos:]
            return head + self.value + tail
        elif self.op == ChangeRequest.DEL_EDIT:
            head = instr[:self.pos]
            tail = instr[self.pos+self.delta:]
            return head + tail
        else:
            print 'UNKNOWN OPERATION'

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        oper = 'n/a'
        if self.op == ChangeRequest.ADD_EDIT:
            oper = 'ins'
        elif self.op == ChangeRequest.DEL_EDIT:
            oper = 'del'

        if self.delta > 0:
            delta = '+' + str(self.delta)
        else:
            delta = str(self.delta)

        return '<' + self.author + '  CR:' + str(self.cr_n) +\
                '  (' + str(self.pos) + ':' + delta + ')  ' +\
                oper + ':' + str(self.value) + '>'
