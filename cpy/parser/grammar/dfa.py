

class DFA(object):
    def __init__(self, nfas, end):
        self.nfas = nfas
        self.is_final = end in nfas
        self.arcs = {}

    def arc(self, state, label):
        self.arcs[label] = state

    def unify_state(self, old, new):
        for label, state in self.arcs.items():
            if state is old:
                self.arcs[label] = new

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if not isinstance(other, DFA):
            # This shouldn't really happen.
            return NotImplemented
        if other.is_final != self.is_final:
            return False
        if len(self.arcs) != len(other.arcs):
            return False
        for label, state in self.arcs.items():
            try:
                other_state = other.arcs[label]
            except KeyError:
                return False
            else:
                if other_state is not state:
                    return False
        return True
