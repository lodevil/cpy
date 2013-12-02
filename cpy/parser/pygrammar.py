from .grammar import Grammar
from .pystates import single_input, file_input, eval_input, symbols


grammar = Grammar(symbols, {
    'single_input': single_input,
    'file_input': file_input,
    'eval_input': eval_input})
