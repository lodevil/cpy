#!/usr/bin/env python

if __name__ == '__main__':
    import os
    import sys

    thisdir = os.path.dirname(__file__)
    sys.path.insert(0, os.path.realpath(os.path.join(thisdir, '../../../')))
    from cpy.parser.pygram_gen.grammar_parser import GrammarParser

    g = GrammarParser(open(os.path.join(thisdir, 'Grammar3.3')).read())
    open(os.path.join(thisdir, '..', 'pystates.py'), 'w').write(
        g.states.generate())
    exit(0)
