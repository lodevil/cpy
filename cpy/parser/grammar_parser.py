import tokenize
from .nfa import NFA
import six
from .state import STATE_LABEL, Label, State

'''inspired by pypy'''


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
        self.states = {}
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
            dfa = start_state.DFA(end_state)
            self.dfas[name] = dfa
        for name, dfa in self.dfas.items():
            self.dfa2state(dfa)
        for state in self.states.values():
            state.build_bootstrap()
        states = {}
        for name, dfa in self.dfas.items():
            state = self.states[dfa[0]]
            state.name = name
            states[name] = state
        self.states = states

    def dfa2state(self, dfa):
        if isinstance(dfa, list):
            dfa = dfa[0]
        state = self.states.get(dfa, None)
        if state is not None:
            return state
        state = State(dfa.is_final)
        self.states[dfa] = state
        for name, d in dfa.arcs.items():
            label = Label.get_label(name)
            if label is None:
                label = Label(STATE_LABEL,
                    self.dfa2state(self.dfas[name]))
            state.arc(label, self.dfa2state(d))
        return state

    def get_first(self, name):
        pass

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
            start_state.arc(end_state)
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
