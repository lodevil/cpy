
class NFA(object):
    '''NFA state'''
    def __init__(self, is_end=False):
        self.arcs = []
        self.is_end = is_end

    def arc(self, state, val=None):
        self.arcs.append((val, state))

    def DFA(self):
        pass
