import tokenize
from collections import defaultdict, OrderedDict
import six


STATE_LABEL = 256
ops = set(['&=', '<<', '<=', '==', '[', '//=', '%=', '^', ']',
    '~', '//', '|=', '-=', '}', '^=', '!=', '>=', '>>',
    '<', '**=', '>>=', '*=', '+=', ';', ':', '/=', '<<=',
    '>', '=', '|', '{', '**', '@', '&', '%', '+', '*',
    ')', '(', '.', '-', ',', '<>', '...', '->'])
normal_tks = set(['NAME', 'STRING', 'NUMBER', 'INDENT',
    'DEDENT', 'NEWLINE', 'ENDMARKER'])

class Label(object):
    __slots__ = 'type', 'val'

    def __init__(self, type, val=None):
        self.type = type
        self.val = val

    @classmethod
    def get_label(cls, label):
        if label[0] == "'":
            if label[-1] != "'" or len(label) < 3:
                raise Exception('invalid label: %r' % label)
            label = label[1:-1]
            if label in ops:
                return cls(tokenize.OP, label)
            return cls(tokenize.NAME, label)
        elif label in normal_tks:
            return cls(getattr(tokenize, label))


class State(object):
    __slots__ = 'is_final', 'name', 'symbol', 'arcs', 'bootstrap'

    def __init__(self, is_final, name=None, symbol=None):
        self.is_final = is_final
        self.name = name
        self.symbol = symbol
        self.arcs = {}

    def __repr__(self):
        if self.name is not None:
            return '<State %s>' % self.name
        return super(State, self).__repr__()

    def arc(self, label, state):
        if label in self.arcs:
            raise Exception('duplicated arc')
        self.arcs[label] = state

    def build_bootstrap(self):
        if not hasattr(self, 'bootstrap'):
            self.bootstrap = defaultdict(lambda: {})
            for label, state in self.arcs.items():
                if label.type == STATE_LABEL:
                    if label.val == self:
                        continue
                    for t, vals in label.val.build_bootstrap().items():
                        for val in vals.keys():
                            if val in self.bootstrap[t]:
                                raise Exception('duplicated bootstrap')
                            self.bootstrap[t][val] = (label.val, state)
                else:
                    self.bootstrap[label.type][label.val] = (None, state)
        return self.bootstrap

    def generate(self, name, ids):
        myid = ids[self]
        varname = '%s%d' % (name, myid)
        if myid == 0:
            yield '%s = %s\n' % (varname, self.name)
        else:
            yield '%s = State(%r)\n' % (varname, self.is_final)

        for label, state in self.arcs.items():
            if state not in ids:
                yield from state.generate(name, ids)
            if label.type == STATE_LABEL:
                yield '%s.arc(Label(%d, %s), %s%d)\n' % (varname,
                    label.type, label.val.name, name, ids[state])
            else:
                yield '%s.arc(Label(%d, %r), %s%d)\n' % (varname,
                    label.type, label.val, name, ids[state])
        yield '%s.bootstrap = {' % varname
        for t, vals in self.bootstrap.items():
            yield '\n    %d: {' % t
            for v, (st1, st2) in vals.items():
                yield '\n        %r: (' % v
                if st1 is None:
                    yield 'None'
                else:
                    yield '%s' % st1.name
                yield ', %s%d),' % (name, ids[st2])
            yield '},'
        yield '}\n'


class IDs(object):
    def __init__(self):
        self.inc = 0
        self.m = {}

    def __getitem__(self, k):
        i = self.m.get(k, None)
        if i is None:
            i = self.inc
            self.inc += 1
            self.m[k] = i
        return i

    def __contains__(self, k):
        return k in self.m


class States(object):
    def __init__(self, **states):
        self.all_states = []
        self.states = OrderedDict()
        self.symbols = {}  # name -> id
        self.inc = STATE_LABEL
        self.reverse_symbol = {}  # id -> name
        for name, state in states.items():
            self[name] = state

    def __setitem__(self, name, state):
        self.inc += 1
        self.symbols[name] = self.inc
        self.reverse_symbol[self.inc] = name
        self.states[name] = state
        stack = [state]
        states = set([state])
        while stack:
            st = stack[0]
            stack = stack[1:]
            for s in st.arcs.values():
                if s not in states:
                    self.all_states.append(s)
                    stack.append(s)
                    states.add(s)
        self.all_states.append(state)

    def __getitem__(self, k):
        if isinstance(k, int):
            k = self.reverse_symbol[k]
        return self.states[k]

    def __iter__(self):
        yield from self.states

    def keys(self):
        yield from self.states.keys()

    def items(self):
        yield from self.states.items()

    def from_dfas(self, dfas):
        states = {}
        def dfa2state(dfa):
            state = states.get(dfa, None)
            if state is not None:
                return state
            state = State(dfa.is_final)
            states[dfa] = state
            for name, d in dfa.arcs.items():
                label = Label.get_label(name)
                if label is None:
                    label = Label(STATE_LABEL,
                        dfa2state(dfas[name][0]))
                state.arc(label, dfa2state(d))
            return state
        for name, dfa in dfas.items():
            dfa2state(dfa[0])
        for name, dfa in dfas.items():
            state = states[dfa[0]]
            state.name = name
            self[name] = state

    def build_bootstrap(self):
        for state in self.all_states:
            state.build_bootstrap()

    def generate(self):
        buf = six.StringIO()
        buf.write('# generated by cpy.parser.state.States\n')
        buf.write('from .grammar.state import State, Label\n')
        buf.write('from .grammar.symbols import Symbols\n\n\n')

        buf.write('class _Symbols(Symbols):\n')
        for i, name in enumerate(self.states.keys()):
            buf.write('    %s = %d\n' % (name, i + STATE_LABEL + 1))
        buf.write('symbols = _Symbols()\n\n\n')

        for i, (name, state) in enumerate(self.states.items()):
            buf.write('%s = State(%r, %r, %d)\n' % (
                name, state.is_final, name, STATE_LABEL + i + 1))
        for name, state in self.states.items():
            buf.write('\n\n')
            buf.write(''.join(state.generate(name, IDs())))
        return buf.getvalue()
