from ..grammar.state import Label, State, STATE_LABEL, States
from tokenize import NAME, OP, NEWLINE, ENDMARKER, ERRORTOKEN


class _Symbols(object):
    attr = 257
    attrs = 258
    item = 259
    stmt = 260
    module = 261
    asdl = 262
symbols = _Symbols()


attr = State(False, 'attr', 257)
attrs = State(False, 'attrs', 258)
item = State(False, 'item', 259)
stmt = State(False, 'stmt', 260)
module = State(False, 'module', 261)
asdl = State(False, 'asdl', 262)


attr0 = attr
attr1 = State(False)
attr2 = State(False)
attr3 = State(True)
attr0.arc(Label(NAME), attr1)
attr1.arc(Label(OP, '*'), attr2)
attr1.arc(Label(ERRORTOKEN, '?'), attr2)
attr1.arc(Label(NAME), attr3)
attr2.arc(Label(NAME), attr3)


attrs0 = attrs
attrs1 = State(False)
attrs2 = State(False)
attrs3 = State(False)
attrs4 = State(True)
attrs0.arc(Label(OP, '('), attrs1)
attrs1.arc(Label(STATE_LABEL, attr), attrs2)
attrs2.arc(Label(OP, ','), attrs3)
attrs2.arc(Label(OP, ')'), attrs4)
attrs3.arc(Label(STATE_LABEL, attr), attrs2)
attrs3.arc(Label(NEWLINE), attrs3)


item0 = item
item1 = State(True)
item2 = State(True)
item0.arc(Label(NAME), item1)
item0.arc(Label(STATE_LABEL, attrs), item2)
item1.arc(Label(STATE_LABEL, attrs), item2)


stmt0 = stmt
stmt1 = State(False)
stmt2 = State(False)
stmt3 = State(True)
stmt4 = State(False)
stmt5 = State(True)
stmt0.arc(Label(NAME), stmt1)
stmt1.arc(Label(OP, '='), stmt2)
stmt2.arc(Label(STATE_LABEL, item), stmt3)
stmt3.arc(Label(NEWLINE), stmt3)
stmt3.arc(Label(OP, '|'), stmt2)
stmt3.arc(Label(NAME, 'attributes'), stmt4)
stmt4.arc(Label(STATE_LABEL, attrs), stmt5)


module0 = module
module1 = State(False)
module2 = State(False)
module3 = State(False)
module4 = State(True)
module0.arc(Label(NAME, 'module'), module1)
module1.arc(Label(NAME), module2)
module2.arc(Label(NEWLINE), module2)
module2.arc(Label(OP, '{'), module3)
module3.arc(Label(NEWLINE), module3)
module3.arc(Label(STATE_LABEL, stmt), module3)
module3.arc(Label(OP, '}'), module4)


asdl0 = asdl
asdl1 = State(False)
asdl2 = State(True)
asdl0.arc(Label(NEWLINE), asdl)
asdl0.arc(Label(STATE_LABEL, module), asdl1)
asdl1.arc(Label(NEWLINE), asdl1)
asdl1.arc(Label(ENDMARKER), asdl2)


states = {
    'attr': attr,
    'attrs': attrs,
    'item': item,
    'stmt': stmt,
    'module': module,
    'asdl': asdl,
}
states = States(**states)
states.build_bootstrap()
