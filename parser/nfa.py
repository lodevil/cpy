from .dfa import DFA

'''inspired by pypy'''


def simplify_dfa(dfa):
    changed = True
    while changed:
        changed = False
        for i, state in enumerate(dfa):
            for j in range(i + 1, len(dfa)):
                other_state = dfa[j]
                if state == other_state:
                    del dfa[j]
                    for sub_state in dfa:
                        sub_state.unify_state(other_state, state)
                    changed = True
                    break

class NFA(object):
    '''NFA state'''
    def __init__(self, is_end=False):
        self.arcs = []
        self.is_end = is_end

    def arc(self, state, label=None):
        self.arcs.append((label, state))

    def epsilon_closure(self, into):
        if self in into:
            return
        into.add(self)
        for label, state in self.arcs:
            if label is None:
                state.epsilon_closure(into)

    def DFA(self, end):
        base_nfas = set()
        self.epsilon_closure(base_nfas)
        state_stack = [DFA(base_nfas, end)]
        for state in state_stack:
            arcs = {}
            for nfa in state.nfas:
                for label, sub_nfa in nfa.arcs:
                    if label is not None:
                        sub_nfa.epsilon_closure(
                            arcs.setdefault(label, set()))
            for label, nfa_set in arcs.items():
                for st in state_stack:
                    if st.nfas == nfa_set:
                        break
                else:
                    st = DFA(nfa_set, end)
                    state_stack.append(st)
                state.arc(st, label)
        simplify_dfa(state_stack)
        return state_stack
