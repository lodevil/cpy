import tokenize
from .nfa import NFA
import six


class GrammarSyntaxError(Exception):
    pass


class GrammarParser(object):
    '''Python Grammar Parser'''
    def __init__(self, gramsrc):
        self.type = tokenize.ENDMARKER
        self.val = ''
        self.range = ((0, 0), (0, 0))
        self.line = ''
        self.dfas = {}
        stream = six.StringIO(gramsrc)
        self.tokens = tokenize.generate_tokens(stream.readline)
        self.parse(gramsrc)

    def next(self):
        #extract next token
        tk = next(self.tokens)
        while tk[0] in (tokenize.NL, tokenize.COMMENT):
            tk = next(self.tokens)
        self.type, self.val = tk[:2]
        self.range = tk[2:4]
        self.line = tk[4]

    def expect(self, type, val=None):
        #check current token's type and value
        if self.type != type:
            msg = 'expect token %s, but got %s(%r) at line %d,%d' % (
                tokenize.tok_name[type], tokenize.tok_name[self.type],
                self.val, self.range[0][0], self.range[0][1])
            raise GrammarSyntaxError(msg)

        if val is not None and self.val != val:
            msg = 'expect %r, but got %r at line %d,%d' % (
                val, self.val, self.range[0][0], self.range[0][1])
            raise GrammarSyntaxError(msg)
        val = self.val
        self.next()
        return val

    def test(self, type, val):
        return self.type == type and self.val == val

    def parse(self, gramsrc):
        self.next()
        while self.type != tokenize.ENDMARKER:
            while self.type == tokenize.NEWLINE:
                self.next()
            name, start_state, end_state = self.parse_rule()
            print('got', name)
            self.dfas[name] = start_state.DFA()

    def parse_rule(self):
        name = self.expect(tokenize.NAME)
        self.expect(tokenize.OP, ':')
        start_state, end_state = self.parse_alternatives()
        self.expect(tokenize.NEWLINE)
        return name, start_state, end_state

    def parse_alternatives(self):
        start_state, end_state = self.parse_items()
        if self.test(tokenize.OP, '|'):
            s = NFA(); s.arc(start_state); start_state = s
            s = NFA(); end_state.arc(s); end_state = s
            while self.test(tokenize.OP, '|'):
                self.next()
                start, end = self.parse_items()
                start_state.arc(start)
                end.arc(end_state)
        return start_state, end_state

    def parse_items(self):
        start_state, end_state = self.parse_item()
        while self.type in (tokenize.NAME, tokenize.STRING) or \
                self.test(tokenize.OP, '(') or \
                self.test(tokenize.OP, '['):
            start, end = self.parse_item()
            end_state.arc(start)
            end_state = end
        return start_state, end_state

    def parse_item(self):
        if self.test(tokenize.OP, '['):
            self.next()
            start_state, end_state = self.parse_alternatives()
            self.expect(tokenize.OP, ']')
        else:
            start_state, end_state = self.parse_atom()
            if self.type == tokenize.OP and self.val in ('*', '+'):
                end_state.arc(start_state)
                if self.val == '*':
                    end_state = start_state
                self.next()
        return start_state, end_state

    def parse_atom(self):
        if self.test(tokenize.OP, '('):
            self.next()
            start_state, end_state = self.parse_alternatives()
            self.expect(tokenize.OP, ')')
        elif self.type in (tokenize.NAME, tokenize.STRING):
            start_state, end_state = NFA(), NFA()
            start_state.arc(end_state, self.val)
            self.next()
        else:
            msg = 'invalid token %r at line %d, %d' % (self.val,
                self.range[0][0], self.range[0][1])
            raise GrammarSyntaxError(msg)

        return start_state, end_state
