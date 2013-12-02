from .parse_tree import Node, ParseTree
from .tokens import Tokens


class Grammar(object):
    def __init__(self, symbols, states, default_state='file_input'):
        self.symbols = symbols
        self.states = states
        self.default_state = default_state

    def parse(self, src, init=None):
        tokens = Tokens(src)
        if init is None:
            init = self.default_state
        tree = ParseTree(self.symbols, init)
        stack = [self.states[init]]

        while stack:
            state = stack[-1]
            tk = tokens.cur
            #get arc
            if tk.type not in state.bootstrap:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar0',
                    ('<src>', tk.start[0], tk.start[1], tk.line))
            arc = state.bootstrap[tk.type].get(tk.string, None) or \
                    state.bootstrap[tk.type].get(None, None)
            if arc is None:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar1',
                    ('<src>', tk.start[0], tk.start[1], tk.line))
            #process arc
            stack[-1] = arc[1]
            if arc[0] is not None:
                stack.append(arc[0])
                tree.add_down(Node(arc[0].symbol, None, tk.start))
            else:
                tree.add(Node(tk.type, tk.string, tk.start, tk.end))
                try:
                    tokens.next()
                except StopIteration:
                    if arc[1].is_final:
                        stack = stack[:-1]
                        if stack:
                            tree.up()
                        break
                    raise SyntaxError('unexpected end',
                        ('<src>', tk.start[0], tk.start[1], tk.line))

        #check no more tokens
        try:
            tokens.next()
            raise SyntaxError('too more tokens: %r', tokens.cur)
        except StopIteration:
            pass

        return tree
