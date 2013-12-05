from . import ast
from .pystates import symbols as syms
import token
import six


class ASTError(Exception):
    pass


class ASTMeta(type):
    def __new__(cls, name, bases, attrs):
        handlers = {}
        attrs['handlers'] = handlers
        newcls = type.__new__(cls, name, bases, attrs)
        for k, v in attrs.items():
            if k.startswith('handle_'):
                sym = k[len('handle_'):]
                handlers[syms[sym]] = getattr(newcls, k)
        return newcls


operator_map = {
    '+': ast.Add,
    '-': ast.Sub,
    '*': ast.Mult,
    '/': ast.Div,
    '%': ast.Mod,
    '**': ast.Pow,
    '<<': ast.LShift,
    '>>': ast.RShift,
    '|': ast.BitOr,
    '^': ast.BitXor,
    '&': ast.BitAnd,
    '//': ast.FloorDiv,
    '==': ast.Eq,
    '!=': ast.NotEq,
    '<': ast.Lt,
    '<=': ast.LtE,
    '>': ast.Gt,
    '>=': ast.GtE,
}


@six.add_metaclass(ASTMeta)
class ASTBuilder(object):
    def __init__(self, root_node):
        self.root = root_node
        self.ast = self.build()

    def build(self):
        n = self.root
        if n == syms.single_input:
            # single_input: NEWLINE | simple_stmt | compound_stmt NEWLINE
            if n[0] == token.NEWLINE:
                return ast.Interactive([])
            return ast.Interactive(self.handle(n[0]))
        elif n == syms.file_input:
            # file_input: (NEWLINE | stmt)* ENDMARKER
            stmts = []
            for stmt in n.filter(syms.stmt):
                stmts.extend(self.handle(stmt[0]))
            return ast.Module(stmts)
        elif n == syms.eval_input:
            # eval_input: testlist NEWLINE* ENDMARKER
            return ast.Expression(self.handle_testlist(n[0]))
        raise ASTError('invalid root node')

    def handle(self, node):
        handler = self.handlers.get(node.type, None)
        if handler is None:
            raise ASTError('invalid node: %r', node)
        return handler(self, node)

    def handle_stmt(self, stmt):
        # stmt: simple_stmt | compound_stmt
        if stmt[0] == syms.simple_stmt:
            return self.handle_simple_stmt(stmt[0])
        return [self.handle(stmt[0][0])]

    def handle_simple_stmt(self, simple_stmt):
        # simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
        # small_stmt: (expr_stmt | del_stmt | pass_stmt | flow_stmt |
        #     import_stmt | global_stmt | nonlocal_stmt | assert_stmt)
        stmts = []
        for small_stmt in simple_stmt.filter(syms.small_stmt):
            stmts.append(self.handle(small_stmt[0]))
        return stmts

    def handle_compound_stmt(self, compound_stmt):
        # compound_stmt: (if_stmt | while_stmt | for_stmt |
        #     try_stmt | with_stmt | funcdef)
        return [self.handle(compound_stmt[0])]

    def handle_testlist(self, testlist):
        # testlist: test (',' test)* [',']
        if len(testlist) == 1:
            return self.handle_test(testlist[0])
        exprs = []
        for test in testlist.filter(syms.test):
            exprs.append(self.handle_test(test))
        return ast.Tuple(exprs, ast.Load, *testlist.start)

    def handle_test(self, test):
        # test: or_test ['if' or_test 'else' test] | lambdef
        if len(test) == 1:
            if test[0] == syms.lambdef:
                return self.handle_lambdef(test[0])
            return self.handle_or_test(test[0])
        body = self.handle_or_test(test[0])
        te = self.handle_or_test(test[2])
        orelse = self.handle_test(test[4])
        return ast.IfExp(te, body, orelse, *test.start)

    def handle_or_test(self, or_test):
        # or_test: and_test ('or' and_test)*
        if len(or_test) == 1:
            return self.handle_and_test(or_test[0])
        return ast.BoolOp(ast.Or,
            [self.handle_and_test(x) for x in or_test.filter(syms.and_test)],
            *or_test.start)

    def handle_and_test(self, and_test):
        #and_test: not_test ('and' not_test)*
        if len(and_test) == 1:
            return self.handle_not_test(and_test[0])
        return ast.BoolOp(ast.And,
            [self.handle_not_test(x) for x in and_test.filter(syms.not_test)],
            *and_test.start)

    def handle_not_test(self, node):
        # not_test: 'not' not_test | comparison
        if len(node) == 2:
            return self.handle_not_test(node[1])
        # comparison: expr (comp_op expr)*
        expr = self.handle_expr(node[0])
        if len(node) == 1:
            return expr
        operators = []
        operands = []
        for i in range(1, len(expr), 2):
            operators.append(node[i][0])
            operands.append(self.handle_expr(node[i + 1]))
        return ast.Compare(expr, operators, operands, *node.start)

    def handle_lambdef(self, node):
        # lambdef: 'lambda' [varargslist] ':' test
        if len(node) == 3:
            args = ast.arguments(
                None, None, None, None, None, None, None, None)
        else:
            args = self.handle_varargslist(node[1])
        return ast.Lambda(args, self.handle_test(node[-1]), *node.start)

    def handle_varargslist(self, node):
        pass

    def handle_expr(self, node):
        # expr: xor_expr ('|' xor_expr)*
        if node == syms.factor:
            return self.handle_factor(node)
        if len(node) == 1:
            return self.handle_expr(node[0])
        binop = ast.BinOp(
            self.handle_expr(node[0]),
            operator_map[node[1].val],
            self.handle_expr(node[2]),
            *node.start)
        for i in range(3, len(node), 2):
            binop = ast.BinOp(binop, operator_map[node[i].val],
                self.handle_expr(node[i + 1]), *node.start)
        return binop

    def handle_factor(self, node):
        # factor: ('+'|'-'|'~') factor | power
        if len(node) == 1:
            return self.handle_power(node[0])
        uop = node[0].val
        if uop == '+':
            uop = ast.UAdd
        elif uop == '-':
            uop = ast.USub
        else:
            uop = ast.Invert
        return ast.UnaryOp(uop, self.handle_power(node[1]), *node.start)

    def handle_power(self, node):
        # power: atom trailer* ['**' factor]
        atom = self.handle_atom(node[0])
        if len(node) == 1:
            return atom
        for n in node.subs[1:]:
            if n != syms.trailer:
                break
            atom = self.get_trailer(n, atom)
        if node[-1] == syms.factor:
            return ast.BinOp(
                atom, ast.Pow, self.handle_factor(node[-1]), *node.start)
        return atom

    def handle_atom(self, node):
        # atom: ('(' [yield_expr|testlist_comp] ')' |
        #     '[' [testlist_comp] ']' |
        #     '{' [dictorsetmaker] '}' |
        #     NAME | NUMBER | STRING+ | '...' | 'None' | 'True' | 'False')
        n = node[0]
        if n == token.Name:
            return ast.Name(n.val, ast.Load, *node.start)

    def get_trailer(self, node, atom):
        # trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
        v = node[0].val
        if v == '.':
            return ast.Attribute(atom, node[1].val, ast.Load, *node.start)
        elif v == '(':
            if len(node) == 2:
                return ast.Call(atom, None, None, None, None, *node.start)
            return self.get_call(atom, node[1])
        return self.get_subscriptlist(atom, node[1])

    def get_call(self, left, arglist):
        pass

    def get_subscriptlist(self, left, node):
        pass

    def handle_expr_stmt(self, expr_stmt):
        pass

    def handle_del_stmt(self, del_stmt):
        pass

    def handle_pass_stmt(self, pass_stmt):
        pass

    def handle_flow_stmt(self, flow_stmt):
        pass

    def handle_import_stmt(self, node):
        if node[0] == syms.import_name:
            return self.handle_import_name(node[0])
        return self.handle_import_from(node[0])

    def handle_import_name(self, node):
        # import_name: 'import' dotted_as_names
        # dotted_as_names: dotted_as_name (',' dotted_as_name)*
        # dotted_as_name: dotted_name ['as' NAME]
        alias = []
        for n in node[1].filter(syms.dotted_as_name):
            name = self.handle_dotted_name(n[0])
            if len(n) == 1:
                alias.append(ast.alias(name, None))
            else:
                alias.append(ast.alias(name, n[2].val))
        return ast.Import(alias, *node.start)

    def handle_import_from(self, node):
        # import_from: ('from' (('.' | '...')* dotted_name | ('.' | '...')+)
        #      'import' ('*' | '(' import_as_names ')' | import_as_names))
        level = 0
        for i in range(1, len(node)):
            if node[i] != token.OP:
                break
            level += len(node[i].val)
        if node[i] == syms.dotted_name:
            module = self.handle_dotted_name(node[i])
            i += 1
        else:
            module = None
        v = node[i + 1].val
        if v == '*':
            names = [ast.alias('*', None)]
        elif v == '(':
            names = self.handle_import_as_names(node[i + 2])
        else:
            names = self.handle_import_as_names(node[i + 1])
        return ast.ImportFrom(module, names, level, *node.start)

    def handle_dotted_name(self, node):
        # dotted_name: NAME ('.' NAME)*
        return '.'.join([n.val for n in node.filter(token.NAME)])

    def handle_import_as_names(self, node):
        # import_as_name: NAME ['as' NAME]
        # import_as_names: import_as_name (',' import_as_name)* [',']
        names = []
        for n in node.filter(syms.import_as_name):
            if len(n) == 1:
                names.append(ast.alias(n[0].val, None))
            else:
                names.append(ast.alias(n[0].val, n[2].val))
        return names

    def handle_global_stmt(self, global_stmt):
        pass

    def handle_nonlocal_stmt(self, nonlocal_stmt):
        pass

    def handle_assert_stmt(self, assert_stmt):
        pass

    def handle_if_stmt(self, if_stmt):
        pass

    def handle_while_stmt(self, while_stmt):
        pass

    def handle_for_stmt(self, for_stmt):
        pass

    def handle_try_stmt(self, try_stmt):
        pass

    def handle_with_stmt(self, with_stmt):
        pass

    def handle_funcdef(self, funcdef):
        pass
