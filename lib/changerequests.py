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

        if self.value == ':':
            self.value = '\\:'
        elif self.value == '\n':
            self.value = '\\n'
        elif self.value == '\r':
            self.value = '\\r'
        elif self.value == '\t':
            self.value = '\\t'

    # Edit types
    ADD_EDIT = 0
    DEL_EDIT = 1

    def serialize(self):
        """Produces a string that encodes the CR"""

        def baseN(x, b=36, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
            if x < 0:
                return x
            return (x == 0) and numerals[0] or \
                   (baseN(x // b, b, numerals).lstrip(numerals[0]) +
                    numerals[x % b])

        parts = {}
        parts['op'] = '-'
        if self.op == ChangeRequest.ADD_EDIT:
            parts['op'] = '+'
        parts['auth'] = self.author
        # Encode numbers in a higher base (36)
        parts['cr_n'] = baseN(self.cr_n)
        parts['pos'] = baseN(self.pos)
        parts['delta'] = baseN(self.delta)
        parts['content'] = self.value

        return "%(auth)s:%(cr_n)s:%(pos)s%(op)s%(delta)s:%(content)s:" % parts

    def deserialize(self, edit):
        pattern = re.compile(
            r'(?P<auth>.+?):(?P<cr>-?[0-9a-z]+?):(?P<pos>[0-9a-z]+?)(?P<op>[+-]?)(?P<delta>[0-9a-z]+?):(?P<data>(\\:|[^:])*?):'
        )
        try:
            sections = re.search(pattern, edit).groups()
        except AttributeError:
            print('Unable to parse change request. Bad format!')
            return

        op = ChangeRequest.DEL_EDIT
        if sections[3] == '+':
            op = ChangeRequest.ADD_EDIT

        self.author = sections[0]
        # Decode numbers from base 36
        self.cr_n = int(sections[1], 36)
        self.pos = int(sections[2], 36)
        self.delta = int(sections[4], 36)
        self.op = op
        self.value = sections[5]

    def apply_over(self, instr):
        val = self.value.replace('\\n', '\n')
        val = val.replace('\\r', '\r')
        val = val.replace('\\t', '\t')
        val = val.replace('\\:', ':')
        if self.op == ChangeRequest.ADD_EDIT:
            head = instr[:self.pos]
            tail = instr[self.pos:]
            return head + val + tail
        elif self.op == ChangeRequest.DEL_EDIT:
            head = instr[:self.pos]
            tail = instr[self.pos+self.delta:]
            return head + tail
        else:
            print('UNKNOWN OPERATION')

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

        return '<' + self.author + '  CR:' + str(self.cr_n) + \
               '  (' + str(self.pos) + ':' + delta + ')  ' + \
               oper + ':' + str(self.value) + '>'


class EncodingHandler:

    # Response Type-to-Code
    resp_ttoc = {
        'ok':               200,  # Generic success message
        'generic_error':    500,  # Generic fail message

        # PadsManager
            # GET
            'yes':                  202,  # Positive answer
            'no':                   203,  # Negative answer (not error)

            # POST

            # PUT
            'pad_already_exists':   409,  # Error message

        # Pad
            # GET
            "nan":                  501,  # Not a number

            # POST

            # PUT
            'update_needed':        206,  # Additional updates are in msg-body
    }
    # For reverse look-up
    # resp_ctot = {key: value for (value, key) in resp_ttoc.items()}
    resp_ctot = {}
    for tp in resp_ttoc:
        resp_ctot[resp_ttoc[tp]] = tp

    @staticmethod
    def serialize_list(l):
        '''Serializes a list into a string'''
        return '>'.join(l)

    @staticmethod
    def deserialize_list(sl):
        '''Deserializes a serialized list'''
        # FIXME: this will not handle '>' inserts right
        return sl.split('>')
