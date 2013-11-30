import tokenize
from collections import defaultdict


STATE_LABEL = 256
ops = set(['&=', '<<', '<=', '==', '[', '//=', '%=', '^', ']',
    '~', '//', '|=', '-=', '}', '^=', '!=', '>=', '>>',
    '<', '**=', '>>=', '*=', '+=', ';', ':', '/=', '<<=',
    '>', '=', '|', '{', '**', '@', '&', '%', '+', '*',
    ')', '(', '.', '-', ',', '<>'])
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
    __slots__ = 'is_final', 'name', 'arcs', 'bootstrap'

    def __init__(self, is_final, name=None):
        self.is_final = is_final
        self.name = name
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
                state.build_bootstrap()
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

    def check(self, tks):
        tk = tks.cur
        if tk[0] not in self.bootstrap:
            if self.is_final:
                return True
            raise Exception('fail0')
        arc = self.bootstrap[tk[0]].get(tk[1], None) or \
            self.bootstrap[tk[0]].get(None, None)
        if arc is None:
            if self.is_final:
                return True
            raise Exception('fail1')
        if arc[0] is not None:
            if not arc[0].check(tks):
                if self.is_final:
                    return True
                raise Exception('fail2')
        else:
            try:
                tks.next()
            except StopIteration:
                if arc[1].is_final:
                    return True
                raise
        return arc[1].check(tks)
