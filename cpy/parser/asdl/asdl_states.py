from ..grammar.state import Label, State, STATE_LABEL, States
from tokenize import NAME, OP, NEWLINE, ENDMARKER, ERRORTOKEN


attr = State(False, 'attr')
attr1 = State(False)
attr2 = State(False)
attr3 = State(True)
attr.arc(Label(NAME), attr1)
attr1.arc(Label(OP, '*'), attr2)
attr1.arc(Label(ERRORTOKEN, '?'), attr2)
attr1.arc(Label(NAME), attr3)
attr2.arc(Label(NAME), attr3)


attrs = State(False, 'attrs')
attrs1 = State(False)
attrs2 = State(False)
attrs3 = State(False)
attrs4 = State(True)
attrs.arc(Label(OP, '('), attrs1)
attrs1.arc(Label(STATE_LABEL, attr), attrs2)
attrs2.arc(Label(OP, ','), attrs3)
attrs2.arc(Label(OP, ')'), attrs4)
attrs3.arc(Label(STATE_LABEL, attr), attrs2)
attrs3.arc(Label(NEWLINE), attrs3)


item = State(False, 'item')
item1 = State(True)
item2 = State(True)
item.arc(Label(NAME), item1)
item.arc(Label(STATE_LABEL, attrs), item2)
item1.arc(Label(STATE_LABEL, attrs), item2)


stmt = State(False, 'stmt')
stmt1 = State(False)
stmt2 = State(False)
stmt3 = State(True)
stmt4 = State(False)
stmt5 = State(True)
stmt.arc(Label(NAME), stmt1)
stmt1.arc(Label(OP, '='), stmt2)
stmt2.arc(Label(STATE_LABEL, item), stmt3)
stmt3.arc(Label(NEWLINE), stmt3)
stmt3.arc(Label(OP, '|'), stmt2)
stmt3.arc(Label(NAME, 'attributes'), stmt4)
stmt4.arc(Label(STATE_LABEL, attrs), stmt5)


module = State(False, 'module')
module1 = State(False)
module2 = State(False)
module3 = State(False)
module4 = State(True)
module.arc(Label(NAME, 'module'), module1)
module1.arc(Label(NAME), module2)
module2.arc(Label(NEWLINE), module2)
module2.arc(Label(OP, '{'), module3)
module3.arc(Label(NEWLINE), module3)
module3.arc(Label(STATE_LABEL, stmt), module3)
module3.arc(Label(OP, '}'), module4)


asdl = State(False, 'asdl')
asdl1 = State(False)
asdl2 = State(True)
asdl.arc(Label(NEWLINE), asdl)
asdl.arc(Label(STATE_LABEL, module), asdl1)
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
