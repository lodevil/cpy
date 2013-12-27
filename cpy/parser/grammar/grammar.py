from .parse_tree import Node, ParseTree
from .sourcefile import SourceFile


class Grammar(object):
    def __init__(self, symbols, states, default_state='file_input'):
        self.symbols = symbols
        self.states = states
        self.default_state = default_state

    def parse(self, src=None, path=None, init=None):
        src = SourceFile(path=path, src=src)
        tokens = src.tokens()
        if init is None:
            init = self.default_state
        tree = ParseTree(self.symbols, init)
        stack = [self.states[init]]

        tk = next(tokens)
        while stack:
            state = stack[-1]
            #get arc
            val_arcs = state.bootstrap.get(tk.type, None)
            if val_arcs is None:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar0',
                    (src.name, tk.start[0], tk.start[1], tk.line))
            arc = val_arcs.get(tk.string, None) or val_arcs.get(None, None)
            if arc is None:
                if state.is_final:
                    stack = stack[:-1]
                    if stack:
                        tree.up()
                    continue
                raise SyntaxError('invalid grammar1',
                    (src.name, tk.start[0], tk.start[1], tk.line))
            #process arc
            stack[-1] = arc[1]
            if arc[0] is not None:
                stack.append(arc[0])
                tree.add_down(Node(arc[0].symbol, None, tk.start))
            else:
                tree.add(Node(tk.type, tk.string, tk.start, tk.end))
                try:
                    tk = next(tokens)
                except StopIteration:
                    if arc[1].is_final:
                        stack = stack[:-1]
                        if stack:
                            tree.up()
                        break
                    raise SyntaxError('unexpected end',
                        (src.name, tk.start[0], tk.start[1], tk.line))

        #check no more tokens
        try:
            tk = next(tokens)
            raise SyntaxError('too more tokens: %r',
                (src.name, tk.start[0], tk.start[1], tk.line))
        except StopIteration:
            pass

        src.parse_tree = tree
        return src
