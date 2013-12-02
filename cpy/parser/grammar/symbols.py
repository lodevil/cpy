import six


class SymbolsMeta(type):
    def __new__(cls, name, bases, attrs):
        syms = {}
        reverse = {}
        for k, v in attrs.items():
            if not k.startswith('_') and isinstance(v, int):
                syms[k] = v
                reverse[v] = k
        attrs['_symbols'] = syms
        attrs['_reverse_symbols'] = reverse
        return type.__new__(cls, name, bases, attrs)


@six.add_metaclass(SymbolsMeta)
class Symbols(object):
    def __getitem__(self, k):
        if isinstance(k, str):
            return self._symbols[k]
        elif isinstance(k, int):
            return self._reverse_symbols[k]
        raise AttributeError(k)
