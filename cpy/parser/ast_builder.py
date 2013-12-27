from . import ast
from .pystates import symbols as syms
from .grammar.sourcefile import SourceFile
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
    '+=': ast.Add,
    '-': ast.Sub,
    '-=': ast.Sub,
    '*': ast.Mult,
    '*=': ast.Mult,
    '/': ast.Div,
    '/=': ast.Div,
    '%': ast.Mod,
    '%=': ast.Mod,
    '**': ast.Pow,
    '**=': ast.Pow,
    '<<': ast.LShift,
    '<<=': ast.LShift,
    '>>': ast.RShift,
    '>>=': ast.RShift,
    '|': ast.BitOr,
    '|=': ast.BitOr,
    '^': ast.BitXor,
    '^=': ast.BitXor,
    '&': ast.BitAnd,
    '&=': ast.BitAnd,
    '//': ast.FloorDiv,
    '//=': ast.FloorDiv,
}

compare_map = {
    '==': ast.Eq,
    '!=': ast.NotEq,
    '<': ast.Lt,
    '<=': ast.LtE,
    '>': ast.Gt,
    '>=': ast.GtE,
    'is': ast.Is,
    'is not': ast.IsNot,
    'in': ast.In,
    'not in': ast.NotIn,
}


@six.add_metaclass(ASTMeta)
class ASTBuilder(object):
    def __init__(self, src):
        if not isinstance(src, SourceFile):
            raise Exception('invalid sourcefile')
        self.src = src
        self.root = src.parse_tree.root
        self.ast = self.build()

    def syntax_error(self, msg, node):
        return SyntaxError(msg, (self.src.name, node.start[0], node.start[1],
                self.src.get_line(node.start[0])))

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
            return ast.UnaryOp(
                ast.Not, self.handle_not_test(node[1]), *node.start)
        # comparison: expr (comp_op expr)*
        # comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'
        node = node[0]
        expr = self.handle_expr(node[0])
        if len(node) == 1:
            return expr
        operators = []
        operands = []
        for i in range(1, len(node), 2):
            if len(node[i]) == 1:
                op = node[i][0].val
            else:
                op = '%s %s' % (node[i][0].val, node[i][1].val)
            operators.append(compare_map[op])
            operands.append(self.handle_expr(node[i + 1]))
        return ast.Compare(expr, operators, operands, *node.start)

    def handle_lambdef(self, node):
        # lambdef: 'lambda' [varargslist] ':' test
        if len(node) == 3:
            args = ast.arguments(args=[], vararg=None, varargannotation=None,
                kwonlyargs=[], kwarg=None, kwargannotation=None,
                defaults=[], kw_defaults=[])
        else:
            args = self.handle_varargslist(node[1])
        return ast.Lambda(args, self.handle_test(node[-1]), *node.start)

    def handle_varargslist(self, node):
        # typedargslist: (tfpdef ['=' test] (',' tfpdef ['=' test])* [','
        #        ['*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef] | '**' tfpdef]]
        #      |  '*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef] | '**' tfpdef)
        # tfpdef: NAME [':' test]
        # varargslist: (vfpdef ['=' test] (',' vfpdef ['=' test])* [','
        #        ['*' [vfpdef] (',' vfpdef ['=' test])* [',' '**' vfpdef] | '**' vfpdef]]
        #      |  '*' [vfpdef] (',' vfpdef ['=' test])* [',' '**' vfpdef] | '**' vfpdef)
        # vfpdef: NAME
        if node[0].val == '**':
            kwarg = node[1][0].val
            kwargannotation = node[1][2].val if len(node[1]) == 3 else None
            return ast.arguments(args=[], vararg=None, varargannotation=None,
                kwonlyargs=[], kwarg=kwarg, kwargannotation=kwargannotation,
                defaults=[], kw_defaults=[])
        elif node[0].val == '*':
            vararg, i = node[1][0].val, 3
            varargannotation = node[1][2].val if len(node[1]) == 3 else None
            kwonlyargs = []
            kw_defaults = []
            while i < len(node) and node[i].val != '**':
                arg = ast.arg(node[i][0].val, None)
                if len(node[i]) == 3:
                    arg.annotation = node[i][2].val
                kwonlyargs.append(arg)
                if node[i + 1].val == '=':
                    kw_defaults.append(self.handle_test(node[i + 2]))
                    i += 4
                else:
                    i += 2
            if i < len(node) and node[i].val == '**':
                kwarg = node[i + 1][0].val
                kwargannotation = node[i + 1][2] if len(node[i + 1]) == 3 else None
            else:
                kwarg, kwargannotation = None, None
            return ast.arguments(args=[], vararg=vararg,
                varargannotation=varargannotation, kwonlyargs=kwonlyargs,
                kwarg=kwarg, kwargannotation=kwargannotation,
                defaults=[], kw_defaults=kw_defaults)
        i = 0
        args = []
        defaults = []
        while i < len(node) and node[i] != token.OP:
            arg = ast.arg(node[i][0].val, None)
            if len(node[i]) == 3:
                arg.annotation = node[i][2].val
            args.append(arg)
            if i + 1 < len(node) and node[i + 1].val == '=':
                defaults.append(self.handle_test(node[i + 2]))
                i += 4
            elif len(defaults) > 0:
                # TODO: get line
                raise self.syntax_error(
                    'non-default argument follows default argument', node)
            else:
                i += 2
        if i < len(node):
            argument = self.handle_varargslist(node.subs[i:])
            argument.args = args
            argument.defaults = defaults
            return argument
        return ast.arguments(args=args, vararg=None, varargannotation=None,
            kwonlyargs=[], kwarg=None, kwargannotation=None, defaults=defaults,
            kw_defaults=[])
    handle_typedargslist = handle_varargslist

    def handle_expr(self, node):
        # expr: xor_expr ('|' xor_expr)*
        # xor_expr: and_expr ('^' and_expr)*
        # and_expr: shift_expr ('&' shift_expr)*
        # shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        # arith_expr: term (('+'|'-') term)*
        # term: factor (('*'|'/'|'%'|'//') factor)*
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
        return ast.UnaryOp(uop, self.handle_factor(node[1]), *node.start)

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

    def get_trailer(self, node, atom):
        # trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
        v = node[0].val
        if v == '.':
            return ast.Attribute(atom, node[1].val, ast.Load, *node.start)
        elif v == '(':
            if len(node) == 2:
                return ast.Call(atom, [], [], None, None, *node.start)
            args, keywords, starargs, kwargs = self.get_arglist(node[1])
            return ast.Call(atom, args, keywords, starargs, kwargs, *node.start)
        return self.get_subscriptlist(atom, node[1])

    def get_subscriptlist(self, left, node):
        # subscriptlist: subscript (',' subscript)* [',']
        # subscript: test | [test] ':' [test] [sliceop]
        # sliceop: ':' [test]
        if len(node) == 1:
            sl = self.get_slice(node[0])
            return ast.Subscript(left, sl, ast.Load, *node.start)
        slices = []
        for n in node.filter(syms.subscript):
            slices.append(self.get_slice(n))
        extsl = ast.ExtSlice(slices)
        return ast.Subscript(left, extsl, ast.Load, *node.start)

    def get_slice(self, node):
        # subscript: test | [test] ':' [test] [sliceop]
        # sliceop: ':' [test]
        if len(node) == 1:
            if node[0] == syms.test:
                return ast.Index(self.handle_test(node[0]))
            return ast.Slice(None, None, None)
        if node[0] == syms.test:
            lower = self.handle_test(node[0])
            next = 2
        else:
            lower, next = None, 1
        if len(node) > 2:
            upper, next = self.handle_test(node[next]), next + 1
            step = None
            if next < len(node):
                sliceop = node[next]
                if len(sliceop) == 2:
                    step = self.handle_test(sliceop[1])
            return ast.Slice(lower, upper, step)
        return ast.Slice(lower, None, None)

    def get_arglist(self, node):
        # arglist: (argument ',')* (argument [',']
        #                 |'*' test (',' argument)* [',' '**' test] 
        #                 |'**' test)
        # return args, keywords, starargs, kwargs
        args, keywords, starargs, kwargs = [], [], None, None
        i = 0
        while i < len(node) and node[i] == syms.argument:
            arg = self.handle_argument(node[i])
            if isinstance(arg, ast.keyword):
                keywords.append(arg)
            elif len(keywords) == 0:
                args.append(arg)
            else:
                raise self.syntax_error('non-keyword arg after keyword arg', node)
            i += 2
        if i >= len(node):
            pass
        elif node[i].val == '*':
            starargs = self.handle_test(node[i + 1])
            i += 3
            while i < len(node) and node[i] == syms.argument:
                kw = self.handle_argument(node[i])
                if not isinstance(kw, ast.keyword):
                    raise self.syntax_error(
                        'only named arguments may follow *expression', node)
                keywords.append(kw)
                i += 2
            if i < len(node):
                kwargs = self.handle_test(node[i + 1])
        else:
            kwargs = self.handle_test(node[i + 1])
        return args, keywords, starargs, kwargs

    def handle_argument(self, node):
        # argument: test [comp_for] | test '=' test
        if len(node) == 1:
            return self.handle_test(node[0])
        elif len(node) == 3:
            k = self.handle_test(node[0])
            v = self.handle_test(node[2])
            return ast.keyword(k, v)
        return ast.GeneratorExp(self.handle_test(node[0]),
            self.get_comp_for(node[1]), *node.start)

    def get_comp_for(self, node):
        # comp_for: 'for' exprlist 'in' or_test [comp_iter]
        # comp_iter: comp_for | comp_if
        target = self.handle_exprlist(node[1])
        if not isinstance(target, ast.AssignTypes):
            raise self.syntax_error(
                'invalid assign to %s' % type(target).__name__, node[1])
        self.loop_mark_ctx(target, ast.Store)
        compfor = ast.comprehension(target, self.handle_or_test(node[3]), [])
        if len(node) == 4:
            return [compfor]
        if node[-1][0] == syms.comp_if:
            tails = self.get_comp_if(node[-1][0])
        else:
            tails = self.get_comp_for(node[-1][0])
        ifs, i = [], 0
        while i < len(tails) and isinstance(tails[i], ast.Compare):
            ifs.append(tails[i])
            i += 1
        compfor.ifs = ifs
        return [compfor] + tails[i:]

    def get_comp_if(self, node):
        # comp_if: 'if' test_nocond [comp_iter]
        # comp_iter: comp_for | comp_if
        comp = self.test_nocond(node[1])
        if len(node) == 3:
            if node[2][0] == syms.comp_if:
                subs = self.get_comp_if(node[2][0])
            else:
                subs = self.get_comp_for(node[2][0])
            return [comp] + subs
        return [comp]

    def handle_exprlist(self, node):
        # exprlist: (expr|star_expr) (',' (expr|star_expr))* [',']
        exprs = []
        for n in node.subs:
            if n == syms.expr:
                exprs.append(self.handle_expr(n))
            elif n == syms.star_expr:
                exprs.append(self.handle_star_expr(n))
        if len(exprs) == 1 and node[-1] != token.OP:
            return exprs[0]
        return ast.Tuple(exprs, ast.Store, *node.start)

    def handle_test_nocond(self, node):
        # test_nocond: or_test | lambdef_nocond
        # lambdef_nocond: 'lambda' [varargslist] ':' test_nocond
        if node[0] == syms.or_test:
            return self.handle_or_test(node[0])
        node = node[0]
        if len(node) == 3:
            args = ast.arguments(args=[], vararg=None, varargannotation=None,
                kwonlyargs=[], kwarg=None, kwargannotation=None,
                defaults=[], kw_defaults=[])
        else:
            args = self.handle_varargslist(node[1])
        return ast.Lambda(args, self.handle_test_nocond(node[-1]), *node.start)

    def handle_atom(self, node):
        # atom: ('(' [yield_expr|testlist_comp] ')' |
        #     '[' [testlist_comp] ']' |
        #     '{' [dictorsetmaker] '}' |
        #     NAME | NUMBER | STRING+ | '...' | 'None' | 'True' | 'False')
        n = node[0]
        if n == token.NAME:
            return ast.Name(n.val, ast.Load, *node.start)
        elif n == token.NUMBER:
            return ast.Num(eval(n.val), *node.start)
        elif n.val == '...':
            return ast.Ellipsis(*node.start)
        elif n == token.STRING:
            return ast.Str(self.get_string(node.subs), *node.start)
        elif n.val == '(':
            if len(node) == 2:
                return ast.Tuple(None, ast.Load, *node.start)
            if node[1] == syms.yield_expr:
                return self.handle_yield_expr(node[1])
            return self.get_testlist_comp('(', node[1])
        elif n.val == '[':
            if len(node) == 2:
                return ast.List(None, ast.Load, *node.start)
            return self.get_testlist_comp('[', node[1])
        else:
            return self.handle_dictorsetmaker(node[1])

    def get_string(self, nodes):
        strs = []
        for n in nodes:
            strs.append(n.val.strip(n.val[0]))
        return ''.join(strs)

    def handle_yield_expr(self, node):
        # yield_expr: 'yield' [yield_arg]
        # yield_arg: 'from' test | testlist
        if len(node) == 1:
            return ast.Yield(None, *node.start)
        if len(node[1]) == 1:
            testlist = self.handle_testlist(node[1][0])
            return ast.Yield(testlist, *node.start)
        test = self.handle_test(node[1][1])
        return ast.YieldFrom(test, *node.start)

    def get_testlist_comp(self, outter, node):
        # testlist_comp: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        if node[0] == syms.test:
            expr = self.handle_test(node[0])
        else:
            expr = self.handle_star_expr(node[0])
        if len(node) == 1:
            # (test|star_expr)
            if outter == '(':
                return expr
            return ast.List([expr], ast.Load, *node.start)
        if node[1] == syms.comp_for:
            # (test|star_expr) comp_for
            generators = self.get_comp_for(node[1])
            return ast.GeneratorExp(expr, generators, *node.start)
        # (test|star_expr) (',' (test|star_expr))* [',']
        i = 2
        elts = [expr]
        while i < len(node):
            if node[i] == syms.test:
                elts.append(self.handle_test(node[i]))
            else:
                elts.append(self.handle_star_expr(node[i]))
            i += 2
        if outter == '(':
            return ast.Tuple(elts, ast.Load, *node.start)
        return ast.List(elts, ast.Load, *node.start)

    def handle_dictorsetmaker(self, node):
        # dictorsetmaker: ( (test ':' test (comp_for | (',' test ':' test)* [','])) |
        #                   (test (comp_for | (',' test)* [','])) )
        if len(node) > 1 and node[1] == token.OP:
            if node[3] == syms.comp_for:
                # test ':' test comp_for
                k = self.handle_test(node[0])
                v = self.handle_test(node[2])
                generators = self.get_comp_for(node[3])
                return ast.DictComp(k, v, generators, *node.start)
            # test ':' test (',' test ':' test)* [',']
            i = 0
            keys, values = [], []
            while i < len(node):
                keys.append(self.handle_test(node[i]))
                values.append(self.handle_test(node[i + 2]))
                i += 4
            return ast.Dict(keys, values, *node.start)
        # (test (comp_for | (',' test)* [',']))
        if len(node) > 1 and node[1] == syms.comp_for:
            # test comp_for
            elt = self.handle_test(node[0])
            generators = self.get_comp_for(node[1])
            return ast.SetComp(elt, generators, *node.start)
        # test (',' test)* [',']
        elts = []
        i = 0
        while i < len(node):
            elts.append(self.handle_test(node[i]))
            i += 2
        return ast.Set(elts, *node.start)

    def handle_expr_stmt(self, node):
        # expr_stmt: testlist_star_expr (augassign (yield_expr|testlist) |
        #                      ('=' (yield_expr|testlist_star_expr))*)
        # augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' |
        #             '<<=' | '>>=' | '**=' | '//=')
        expr = self.handle_testlist_star_expr(node[0])
        if len(node) == 1:
            return  ast.Expr(expr, *node.start)
        if not isinstance(expr, ast.AssignTypes):
            raise self.syntax_error(
                'invalid assign to %s' % type(expr).__name__, node)
        self.loop_mark_ctx(expr, ast.Store)
        if node[1] == syms.augassign:
            op = operator_map[node[1][0].val]
            if node[2] == syms.yield_expr:
                return ast.AugAssign(
                    expr, op, self.handle_yield_expr(node[2]), *node.start)
            return ast.AugAssign(
                expr, op, self.handle_testlist(node[2]), *node.start)

        targets, i = [expr], 2
        for i in range(2, len(node) - 1, 2):
            if node[i] == syms.yield_expr:
                t = self.handle_yield_expr(node[i])
            else:
                t = self.handle_testlist_star_expr(node[i])
            if not isinstance(t, ast.AssignTypes):
                raise self.syntax_error(
                    'invalid assign to %s' % type(t).__name__, node[i])
            self.loop_mark_ctx(t, ast.Store)
            targets.append(t)
            i += 2
        if node[-1] == syms.yield_expr:
            value = self.handle_yield_expr(node[-1])
        else:
            value = self.handle_testlist_star_expr(node[-1])
        self.loop_mark_ctx(value, ast.Load)
        return ast.Assign(targets, value, *node.start)

    @classmethod
    def loop_mark_ctx(cls, obj, ctx):
        obj.ctx = ctx
        if isinstance(obj, (ast.List, ast.Tuple)):
            for elt in obj.elts:
                cls.loop_mark_ctx(elt, ctx)

    def handle_testlist_star_expr(self, node):
        # testlist_star_expr: (test|star_expr) (',' (test|star_expr))* [',']
        exprs = []
        for n in node.subs:
            if n == syms.test:
                exprs.append(self.handle_test(n))
            elif n == syms.star_expr:
                exprs.append(self.handle_star_expr(n))
        if len(exprs) == 1 and  node[-1] != token.OP:
            return exprs[0]
        return ast.Tuple(exprs, ast.Store, *node.start)

    def handle_star_expr(self, node):
        # star_expr: '*' expr
        return ast.Starred(self.handle_expr(node[1]), ast.Store, *node.start)

    def handle_del_stmt(self, node):
        # del_stmt: 'del' exprlist
        expr = self.handle_exprlist(node[1])
        if isinstance(expr, ast.Tuple):
            return ast.Delete(expr.elts, *node.start)
        return ast.Delete([expr], *node.start)

    def handle_pass_stmt(self, node):
        # pass_stmt: 'pass'
        return ast.Pass(*node.start)

    def handle_flow_stmt(self, node):
        # flow_stmt: break_stmt | continue_stmt | return_stmt
        #          | raise_stmt | yield_stmt
        # return_stmt: 'return' [testlist]
        # break_stmt: 'break'
        # continue_stmt: 'continue'
        # yield_stmt: yield_expr
        # raise_stmt: 'raise' [test ['from' test]]
        node = node[0]
        if node == syms.return_stmt:
            if len(node) == 2:
                return ast.Return(self.handle_testlist(node[1]), *node.start)
            return ast.Return(None, *node.start)
        elif node == syms.break_stmt:
            return ast.Break(*node.start)
        elif node == syms.continue_stmt:
            return ast.Continue(*node.start)
        elif node == syms.yield_stmt:
            return self.handle_yield_expr(node[0])
        exc = len(node) > 1 and self.handle_test(node[1]) or None
        cause = len(node) == 4 and self.handle_test(node[3]) or None
        return ast.Raise(exc, cause, *node.start)

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

    def handle_global_stmt(self, node):
        # global_stmt: 'global' NAME (',' NAME)*
        return ast.Global(list(node.filter(token.NAME)), *node.start)

    def handle_nonlocal_stmt(self, node):
        # nonlocal_stmt: 'nonlocal' NAME (',' NAME)*
        return ast.Nonlocal(list(node.filter(token.NAME)), *node.start)

    def handle_assert_stmt(self, node):
        # assert_stmt: 'assert' test [',' test]
        test = self.handle_test(node[1])
        if len(node) == 2:
            msg = None
        else:
            msg = self.handle_test(node[3])
        return ast.Assert(test, msg, *node.start)

    def handle_suite(self, node, get_stmts=False):
        # suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT
        if len(node) == 1:
            stmts = self.handle_simple_stmt(node[0])
            if get_stmts:
                return stmts
            return ast.Suite(stmts)
        stmts = []
        for i in range(2, len(node) - 1):
            stmts.extend(self.handle_stmt(node[i]))
        if get_stmts:
            return stmts
        return ast.Suite(stmts)

    def handle_if_stmt(self, node):
        # if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        test = self.handle_test(node[1])
        body = self.handle_suite(node[3], get_stmts=True)
        ifexpr = ast.If(test, body, [], *node.start)
        cur, i = ifexpr, 4
        while i < len(node) and node[i].val == 'elif':
            test = self.handle_test(node[i + 1])
            body = self.handle_suite(node[i + 3], get_stmts=True)
            expr = ast.If(test, body, [], *node[i].start)
            cur.orelse.append(expr)
            cur = expr
            i += 4
        if i < len(node):
            cur.orelse = self.handle_suite(node[-1], get_stmts=True)
        return ifexpr

    def handle_while_stmt(self, node):
        # while_stmt: 'while' test ':' suite ['else' ':' suite]
        test = self.handle_test(node[1])
        body = self.handle_suite(node[3], get_stmts=True)
        if len(node) == 4:
            orelse = []
        else:
            orelse = self.handle_suite(node[6], get_stmts=True)
        return ast.While(test, body, orelse, *node.start)

    def handle_for_stmt(self, node):
        # for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]
        target = self.handle_exprlist(node[1])
        if not isinstance(target, ast.AssignTypes):
            raise self.syntax_error(
                'invalid assign to %s' % type(target).__name__, node[1])
        self.loop_mark_ctx(target, ast.Store)
        iterator = self.handle_testlist(node[3])
        body = self.handle_suite(node[5], get_stmts=True)
        if len(node) == 6:
            orelse = []
        else:
            orelse = self.handle_suite(node[8], get_stmts=True)
        return ast.For(target, iterator, body, orelse, *node.start)

    def handle_try_stmt(self, node):
        # try_stmt: ('try' ':' suite
        #            ((except_clause ':' suite)+
        #             ['else' ':' suite]
        #             ['finally' ':' suite] |
        #            'finally' ':' suite))
        # except_clause: 'except' [test ['as' NAME]]
        body = self.handle_suite(node[2], get_stmts=True)
        handlers, i = [], 3
        while i < len(node) and node[i] == syms.except_clause:
            expnode = node[i]
            exptype = len(expnode) > 1 and self.handle_test(expnode[1]) or None
            expname = len(expnode) > 2 and expnode[3].val or None
            expbody = self.handle_suite(node[i + 2], get_stmts=True)
            handlers.append(
                ast.ExceptHandler(exptype, expname, expbody, *expnode.start))
            i += 3
        orelse = []
        if i < len(node) and node[i].val == 'else':
            orelse = self.handle_suite(node[i + 2], get_stmts=True)
            i += 3
        finalbody = []
        if i < len(node) and node[i].val == 'finally':
            finalbody = self.handle_suite(node[i + 2], get_stmts=True)
        return ast.Try(body, handlers, orelse, finalbody, *node.start)

    def handle_with_stmt(self, node):
        # with_stmt: 'with' with_item (',' with_item)*  ':' suite
        # with_item: test ['as' expr]
        items, i = [], 1
        while i < len(node) and node[i] == syms.with_item:
            wnode = node[i]
            item = ast.withitem(self.handle_test(wnode[0]), None)
            if len(wnode) == 3:
                item.optional_vars = self.handle_test(wnode[2])
            items.append(item)
            i += 2
        body = self.handle_suite(node[-1], get_stmts=True)
        return ast.With(items, body, *node.start)

    def handle_funcdef(self, node):
        # funcdef: 'def' NAME parameters ['->' test] ':' suite
        # parameters: '(' [typedargslist] ')'
        name = node[1].val
        if len(node[2]) == 2:
            params = ast.arguments(args=[], vararg=None, varargannotation=None,
                kwonlyargs=[], kwarg=None, kwargannotation=None,
                defaults=[], kw_defaults=[])
        else:
            params = self.handle_typedargslist(node[2][1])
        if node[3].val == ':':
            returns = None
        else:
            returns = self.handle_test(node[4])
        body = self.handle_suite(node[-1], get_stmts=True)
        return ast.FunctionDef(name, params, body, [], returns, *node.start)

    def handle_classdef(self, node):
        # classdef: 'class' NAME ['(' [arglist] ')'] ':' suite
        name = node[1].val
        if len(node) == 7:
            bases, keywords, starargs, kwargs = self.get_arglist(node[3])
        else:
            bases, keywords, starargs, kwargs = [], [], None, None
        body = self.handle_suite(node[-1], get_stmts=True)
        return ast.ClassDef(
            name, bases, keywords, starargs, kwargs, body, [], *node.start)

    def handle_decorated(self, node):
        # decorated: decorators (classdef | funcdef)
        # decorators: decorator+
        # decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
        # dotted_name: NAME ('.' NAME)*
        if node[1] == syms.funcdef:
            funccls = self.handle_funcdef(node[1])
        else:
            funccls = self.handle_classdef(node[1])
        decs, i = [], 0
        for n in node[0]:
            name = self.get_attribute(node[1])
            if n[2].val == '(':
                if len(n) == 6:
                    args, keywords, starargs, kwargs = self.get_arglist(n[3])
                else:
                    args, keywords, starargs, kwargs = [], [], None, None
                decs.append(ast.Call(
                    name, args, keywords, starargs, kwargs, *n[1].start))
            else:
                decs.append(name)
        funccls.decorator_list = decs
        return funccls

    def get_attribute(self, node):
        # dotted_name: NAME ('.' NAME)*
        if len(node) == 1:
            return ast.Name(node[0].val, ast.Load, *node.start)
        attr = ast.Attribute(node[0].val, node[2].val, ast.Load, *node.start)
        i = 3
        while i < len(node):
            attr = ast.Attribute(attr, node[i].val, ast.Load, *node.start)
            i += 2
        return attr
