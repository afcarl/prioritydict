# -*- coding: utf-8 -*-

"""
PriorityDict Implementation
===========================

* TODO collections.Counter uses inequality rather than min/max for operators
* TODO review views (and abc impls)
* TODO update docs
* TODO test correct exception types raised on errors

PriorityDict is an Apache2 licensed implementation of a dictionary which
maintains key-value pairs in value sort order.

Compared with Counter
---------------------

* d.index(key) -> position
* d.bisect(value) -> position
* d.clean(value=0) rather than "+ Counter()"
  * Permits negative and zero counts after operations
* d.tally() rather than update(), update uses dict semantics
* Provides PriorityDict.count(...) for counter compatibility
* PriorityDict({0: 'a'}) + PriorityDict({1: 'b', 2: 'c'}) works
* Set-like subtraction, addition operators
* Set-like comparison operators
"""

from sortedcontainers import SortedList

from collections import Counter, MutableMapping, Set, Sequence
from collections import KeysView as AbstractKeysView
from collections import ValuesView as AbstractValuesView
from collections import ItemsView as AbstractItemsView

from functools import wraps
from itertools import chain, repeat
from sys import hexversion

def iter_items(dict_):
    if hexversion < 0x03000000:
        return dict_.iteritems()
    else:
        return iter(dict_.items())

_NotGiven = object()

class _Biggest:
    """An object that is greater than all others."""
    def __gt__(self, that):
        return True
    def __ge__(self, that):
        return True
    def __lt__(self, that):
        return False
    def __le__(self, that):
        return False
    def __eq__(self, that):
        return False
    def __ne__(self, that):
        return True

_Biggest = _Biggest()

def not26(func):
    """Function decorator for methods not implemented in Python 2.6."""

    @wraps(func)
    def errfunc(*args, **kwargs):
        raise NotImplementedError

    if hexversion < 0x02070000:
        return errfunc
    else:
        return func

class _IlocWrapper:
    def __init__(self, _dict):
        self._dict = _dict

    def __len__(self):
        return len(self._dict)

    def __getitem__(self, index):
        """
        Very efficiently return the key at index *index* in iteration. Supports
        negative indices and slice notation. Raises IndexError on invalid
        *index*.
        """
        _list = self._dict._list
        if isinstance(index, slice):
            return [key for value, key in _list[index]]
        else:
            return _list[index][1]

    def __delitem__(self, index):
        """
        Remove the ``sdict[sdict.iloc[index]]`` from *sdict*. Supports negative
        indices and slice notation. Raises IndexError on invalid *index*.
        """
        _list, _dict = self._dict._list, self._dict._dict
        if isinstance(index, slice):
            for key in (key for value, key in _list[index]):
                del _dict[key]
            del _list[index]
        else:
            key = _list[index][1]
            del _list[index]
            del _dict[key]

class PriorityDict(MutableMapping):
    """
    A PriorityDict provides the same methods as a dict. Additionally, a
    PriorityDict efficiently maintains its keys in value sorted order.
    Consequently, the keys method will return the keys in value sorted order,
    the popitem method will remove the item with the highest value, etc.
    """
    def __init__(self, *args, **kwargs):
        """
        A PriorityDict provides the same methods as a dict. Additionally, a
        PriorityDict efficiently maintains its keys in value sorted order.
        Consequently, the keys method will return the keys in value sorted
        order, the popitem method will remove the item with the highest value,
        etc.

        An optional *iterable* provides an initial series of items to
        populate the PriorityDict. Like collections.Counter, items are
        counted from iterable.

        If keyword arguments are given, the keywords themselves with their
        associated values are added as items to the dictionary. If a key is
        specified both in the positional argument and as a keyword argument,
        the value associated with the keyword is retained in the dictionary.
        For example, these all return a dictionary equal to ``{"one": 2,
        "two": 3}``:

        * ``PriorityDict(one=2, two=3)``
        * ``PriorityDict({'one': 2, 'two': 3})``
        * ``PriorityDict(['one', 'two', 'one', 'two', 'two')``

        The first example only works for keys that are valid Python
        identifiers; the others work with any valid keys.
        """
        self._dict = dict()
        self._list = SortedList()
        self.iloc = _IlocWrapper(self)
        self.update(*args, **kwargs)

    def clear(self):
        """Remove all elements from the dictionary."""
        self._dict.clear()
        self._list.clear()

    def clean(self, value=0):
        """
        Remove all items with value less than or equal to `value`.
        Default `value` is 0.
        """
        _list, _dict = self._list, self._dict
        pos = self.bisect_right(value)
        for key in (key for value, key in _list[:pos]):
            del _dict[key]
        del _list[:pos]

    def __contains__(self, key):
        """Return True if and only if *key* is in the dictionary."""
        return key in self._dict

    def __delitem__(self, key):
        """
        Remove ``d[key]`` from *d*.  Raises a KeyError if *key* is not in the
        dictionary.
        """
        value = self._dict[key]
        self._list.remove((value, key))
        del self._dict[key]

    def __getitem__(self, key):
        """
        Return the priority of *key* in *d*.  Raises a KeyError if *key* is not
        in the dictionary.
        """
        return self._dict[key]

    def __iter__(self):
        """
        Create an iterator over the keys of the dictionary ordered by the value
        sort order.
        """
        return iter(key for value, key in self._list)

    def __reversed__(self):
        """
        Create an iterator over the keys of the dictionary ordered by the
        reversed value sort order.
        """
        return iter(key for value, key in reversed(self._list))

    def __len__(self):
        """Return the number of (key, value) pairs in the dictionary."""
        return len(self._dict)

    def __setitem__(self, key, value):
        """Set `d[key]` to *value*."""
        if key in self._dict:
            old_value = self._dict[key]
            self._list.remove((old_value, key))
        self._list.add((value, key))
        self._dict[key] = value

    def copy(self):
        """Create a shallow copy of the dictionary."""
        that = PriorityDict()
        that._dict = self._dict
        that._list = self._list
        that.iloc = self.iloc
        return that

    @classmethod
    def fromkeys(cls, iterable, value=0):
        """
        Create a new dictionary with keys from `iterable` and values set to
        `value`. The default *value* is 0.
        """
        return PriorityDict((key, value) for key in iterable)

    def get(self, key, default=None):
        """
        Return the value for *key* if *key* is in the dictionary, else
        *default*.  If *default* is not given, it defaults to ``None``,
        so that this method never raises a KeyError.
        """
        return self._dict.get(key, default)

    def has_key(self, key):
        """Return True if and only in *key* is in the dictionary."""
        return key in self._dict

    def pop(self, key, default=_NotGiven):
        """
        If *key* is in the dictionary, remove it and return its value,
        else return *default*. If *default* is not given and *key* is not in
        the dictionary, a KeyError is raised.
        """
        if key in self._dict:
            value = self._dict[key]
            self._list.remove((value, key))
            return self._dict.pop(key)
        else:
            if default == _NotGiven:
                raise KeyError
            else:
                return default

    def popitem(self, index=-1):
        """
        Remove and return item at *index* (default: -1). Raises IndexError if
        dict is empty or index is out of range. Negative indices are supported
        as for slice indices.
        """
        value, key = self._list.pop(index)
        del self._dict[key]
        return key, value

    def setdefault(self, key, default=0):
        """
        If *key* is in the dictionary, return its value.  If not, insert *key*
        with a value of *default* and return *default*.  *default* defaults to
        ``0``.
        """
        if key in self._dict:
            return self._dict[key]
        else:
            self._dict[key] = default
            self._list.add((default, key))
            return default

    def elements(self):
        """
        Return an iterator over elements repeating each as many times as its
        count. Elements are returned in value sort-order. If an element’s count
        is less than one, elements() will ignore it.
        """
        values = (repeat(key, value) for value, key in self._list)
        return chain.from_iterable(values)

    def most_common(self, count=None):
        """
        Return a list of the `count` highest priority elements with their
        priority. If `count` is not specified, `most_common` returns *all*
        elements in the dict. Elements with equal counts are ordered by key.
        """
        _list, _dict = self._list, self._dict

        if count is None:
            return [(key, value) for value, key in reversed(_list)]

        end = len(_dict) - 1
        start = max(end - count, -1)

        items = (_list[pos] for pos in xrange(end, start, -1))
        return [(key, value) for value, key in items]

    def subtract(self, elements):
        """
        Elements are subtracted from an iterable or from another mapping (or
        counter). Like dict.update() but subtracts counts instead of replacing
        them. Both inputs and outputs may be zero or negative.
        """
        self -= Counter(elements)

    def tally(self, *args, **kwargs):
        """
        Elements are counted from an iterable or added-in from another mapping
        (or counter). Like dict.update() but adds counts instead of replacing
        them. Also, the iterable is expected to be a sequence of elements, not a
        sequence of (key, value) pairs.
        """
        self += Counter(*args, **kwargs)

    @classmethod
    def count(self, *args, **kwargs):
        """
        Consume `args` and `kwargs` with a Counter and use that mapping to
        initialize a PriorityDict.
        """
        return PriorityDict(Counter(*args, **kwargs))

    def update(self, *args, **kwargs):
        """
        Update the dictionary with the key/value pairs from *other*, overwriting
        existing keys.

        *update* accepts either another dictionary object or an iterable of
        key/value pairs (as a tuple or other iterable of length two).  If
        keyword arguments are specified, the dictionary is then updated with
        those key/value pairs: ``d.update(red=1, blue=2)``.
        """
        _list, _dict = self._list, self._dict
        items = dict(*args, **kwargs)
        if (10 * len(items)) > len(_dict):
            _dict.update(items)
            _list.clear()
            _list.update((value, key) for key, value in iter_items(_dict))
        else:
            for key, value in iter_items(items):
                old_value = _dict[key]
                _list.remove((old_value, key))
                _dict[key] = value
                _list.add((value, key))

    def index(self, key):
        """
        Return the smallest *k* such that `d.iloc[k] == key`.  Raises KeyError
        if *key* is not present.
        """
        value = self._dict[key]
        return self._list.index((value, key))

    def bisect_left(self, value):
        """
        Similar to the ``bisect`` module in the standard library, this returns
        an appropriate index to insert *value* in PriorityDict. If *value* is
        already present in PriorityDict, the insertion point will be before (to
        the left of) any existing entries.
        """
        return self._list.bisect_left((value,))

    def bisect(self, value):
        """Same as bisect_left."""
        return self._list.bisect((value,))

    def bisect_right(self, value):
        """
        Same as `bisect_left`, but if *value* is already present in
        PriorityDict, the insertion point will be after (to the right
        of) any existing entries.
        """
        return self._list.bisect_right((value, _Biggest))

    def __iadd__(self, that):
        """Add values from `that` mapping."""
        _list, _dict = self._list, self._dict
        if len(_dict) == 0:
            _dict.update(that)
            _list.update((value, key) for key, value in iter_items(_dict))
        elif len(that) * 3 > len(_dict):
            _list.clear()
            for key, value in iter_items(that):
                if key in _dict:
                    _dict[key] += value
                else:
                    _dict[key] = value
            _list.update((value, key) for key, value in iter_items(_dict))
        else:
            for key, value in iter_items(that):
                if key in _dict:
                    old_value = _dict[key]
                    _list.remove((old_value, key))
                    value = old_value + value
                _dict[key] = value
                _list.add((value, key))
        return self

    def __isub__(self, that):
        """Subtract values from `that` mapping."""
        _list, _dict = self._list, self._dict
        if len(_dict) == 0:
            _dict.clear()
            _list.clear()
        elif len(that) * 3 > len(_dict):
            _list.clear()
            for key, value in iter_items(that):
                if key in _dict:
                    _dict[key] -= value
            _list.update((value, key) for key, value in iter_items(_dict))
        else:
            for key, value in iter_items(that):
                if key in _dict:
                    old_value = _dict[key]
                    _list.remove((old_value, key))
                    value = old_value - value
                    _dict[key] = value
                    _list.add((value, key))
        return self

    def __ior__(self, that):
        """Or values from `that` mapping (max(v1, v2))."""
        _list, _dict = self._list, self._dict
        if len(_dict) == 0:
            _dict.update(that)
            _list.update((value, key) for key, value in iter_items(_dict))
        elif len(that) * 3 > len(_dict):
            _list.clear()
            for key, value in iter_items(that):
                if key in _dict:
                    _dict[key] = max(_dict[key], value)
                else:
                    _dict[key] = value
            _list.update((value, key) for key, value in iter_items(_dict))
        else:
            for key, value in iter_items(that):
                if key in _dict:
                    old_value = _dict[key]
                    _list.remove((old_value, key))
                    value = max(old_value, value)
                _dict[key] = value
                _list.add((value, key))
        return self

    def __iand__(self, that):
        """And values from `that` mapping (min(v1, v2))."""
        _list, _dict = self._list, self._dict
        if len(_dict) == 0:
            _dict.clear()
            _list.clear()
        elif len(that) * 3 > len(_dict):
            _list.clear()
            for key, value in iter_items(that):
                if key in _dict:
                    _dict[key] = min(_dict[key], value)
            _list.update((value, key) for key, value in iter_items(_dict))
        else:
            for key, value in iter_items(that):
                if key in _dict:
                    old_value = _dict[key]
                    _list.remove((old_value, key))
                    value = min(old_value, value)
                    _dict[key] = value
                    _list.add((value, key))
        return self

    def __add__(self, that):
        """Add values from this and `that` mapping."""
        result = PriorityDict()
        _list, _dict = result._list, result._dict
        _dict.update(self._dict)
        for key, value in iter_items(that):
            if key in _dict:
                _dict[key] += value
            else:
                _dict[key] = value
        _list.update((value, key) for key, value in iter_items(_dict))
        return result

    def __sub__(self, that):
        """Subtract values in `that` mapping from this."""
        result = PriorityDict()
        _list, _dict = result._list, result._dict
        _dict.update(self._dict)
        for key, value in iter_items(that):
            if key in _dict:
                _dict[key] -= value
        _list.update((value, key) for key, value in iter_items(_dict))
        return result

    def __or__(self, that):
        """Or values from this and `that` mapping."""
        result = PriorityDict()
        _list, _dict = result._list, result._dict
        _dict.update(self._dict)
        for key, value in iter_items(that):
            if key in _dict:
                _dict[key] = max(_dict[key], value)
            else:
                _dict[key] = value
        _list.update((value, key) for key, value in iter_items(_dict))
        return result

    def __and__(self, that):
        """And values from this and `that` mapping."""
        result = PriorityDict()
        _list, _dict = result._list, result._dict
        _dict.update(self._dict)
        for key, value in iter_items(that):
            if key in _dict:
                _dict[key] = min(_dict[key], value)
        _list.update((value, key) for key, value in iter_items(_dict))
        return result

    def __eq__(self, that):
        """Compare two mappings for equality."""
        if isinstance(that, PriorityDict):
            that = that._dict
        return self._dict == that

    def __ne__(self, that):
        """Compare two mappings for inequality."""
        if isinstance(that, PriorityDict):
            that = that._dict
        return self._dict != that

    def __lt__(self, that):
        """Compare two mappings for less than."""
        if isinstance(that, PriorityDict):
            that = that._dict
        _dict = self._dict
        return (_dict != that and self <= that)

    def __le__(self, that):
        """Compare two mappings for less than equal."""
        if isinstance(that, PriorityDict):
            that = that._dict
        _dict = self._dict
        return (len(_dict) <= len(that) and
                all(_dict[key] <= that[key] if key in that else False
                    for key in _dict))

    def __gt__(self, that):
        """Compare two mappings for greater than."""
        if isinstance(that, PriorityDict):
            that = that._dict
        _dict = self._dict
        return (_dict != that and self >= that)

    def __ge__(self, that):
        """Compare two mappings for greater than equal."""
        if isinstance(that, PriorityDict):
            that = that._dict
        _dict = self._dict
        return (len(_dict) >= len(that) and
                all(_dict[key] >= that[key] if key in _dict else False
                    for key in that))

    def isdisjoint(self, that):
        """
        Return True if no key in `self` is also in `that`.
        This doesn't check that the value is greater than zero.
        To remove keys with value less than or equal to zero see *clean*.
        """
        return not any(key in self for key in that)

    def items(self):
        """
        In Python 2, returns a list of the dictionary's items (``(key, value)``
        pairs).

        In Python 3, returns a new ItemsView of the dictionary's items.  In
        addition to the methods provided by the built-in `view` the ItemsView is
        indexable (e.g., ``d.items()[5]``).
        """
        if hexversion < 0x03000000:
            return list((key, value) for value, key in self._list)
        else:
            return ItemsView(self)

    def iteritems(self):
        """Return an iterable over the items (``(key, value)`` pairs)."""
        return iter((key, value) for value, key in self._list)

    @not26
    def viewitems(self):
        """
        In Python 2.7 and later, return a new `ItemsView` of the dictionary's
        items.

        In Python 2.6, raise a NotImplementedError.
        """
        return ItemsView(self)

    def keys(self):
        """
        In Python 2, return a list of the dictionary's keys.

        In Python 3, return a new KeysView of the dictionary's keys.  In
        addition to the methods provided by the built-in `view` the KeysView is
        indexable (e.g., ``d.keys()[5]``).
        """
        if hexversion < 0x03000000:
            return list(key for value, key in self._list)
        else:
            return KeysView(self)

    def iterkeys(self):
        """Return an iterable over the keys of the dictionary."""
        return iter(key for value, key in self._list)

    @not26
    def viewkeys(self):
        """
        In Python 2.7 and later, return a new `KeysView` of the dictionary's
        keys.

        In Python 2.6, raise a NotImplementedError.
        """
        return KeysView(self)

    def values(self):
        """
        In Python 2, return a list of the dictionary's values.

        In Python 3, return a new :class:`ValuesView` of the dictionary's
        values.  In addition to the methods provided by the built-in `view`
        the ValuesView is indexable (e.g., ``d.values()[5]``).
        """
        return list(value for value, key in self._list)

    def itervalues(self):
        """Return an iterable over the values of the dictionary."""
        return iter(value for value, key in self._list)

    @not26
    def viewvalues(self):
        """
        In Python 2.7 and later, return a new `ValuesView` of the dictionary's
        values.

        In Python 2.6, raise a NotImplementedError.
        """
        return ValuesView(self)

    def __repr__(self):
        """Return string representation of PriorityDict."""
        return 'PriorityDict({0})'.format(repr(dict(self)))

    def _check(self):
        self._list._check()
        assert len(self._dict) == len(self._list)
        assert all(key in self._dict and self._dict[key] == value
                   for value, key in self._list)

class KeysView(AbstractKeysView, Set, Sequence):
    """
    A KeysView object is a dynamic view of the dictionary's keys, which
    means that when the dictionary's keys change, the view reflects
    those changes.

    The KeysView class implements the Set and Sequence Abstract Base Classes.
    """
    def __init__(self, priority_dict):
        """
        Initialize a KeysView from a PriorityDict container as *priority_dict*.
        """
        self._list = priority_dict._list
        if hexversion < 0x03000000:
            self._view = priority_dict._dict.viewkeys()
        else:
            self._view = priority_dict._dict.keys()
    def __len__(self):
        """Return the number of entries in the dictionary."""
        return len(self._view)
    def __contains__(self, key):
        """
        Return True if and only if *key* is one of the underlying dictionary's
        keys.
        """
        return key in self._view
    def __iter__(self):
        """
        Return an iterable over the keys in the dictionary. Keys are iterated
        over in value sorted order.

        Iterating views while adding or deleting entries in the dictionary may
        raise a RuntimeError or fail to iterate over all entries.
        """
        return iter(key for value, key in self._list)
    def __getitem__(self, index):
        """
        Efficiently return key at *index* in iteration.

        Supports slice notation and negative indexes.
        """
        if isinstance(index, slice):
            return [key for value, key in self._list[index]]
        else:
            return self._list[index][1]
    def __reversed__(self):
        """
        Return a reversed iterable over the keys in the dictionary. Keys are
        iterated over in reverse value sort order.

        Iterating views while adding or deleting entries in the dictionary may
        raise a RuntimeError or fail to iterate over all entries.
        """
        return iter(key for value, key in reversed(self._list))
    def count(self, key):
        """Return the number of occurrences of *key* in the set."""
        return 1 if key in self._view else 0
    def __eq__(self, that):
        """Test set-like equality with *that*."""
        return self._view == that
    def __ne__(self, that):
        """Test set-like inequality with *that*."""
        return self._view != that
    def __lt__(self, that):
        """Test whether self is a proper subset of *that*."""
        return self._view < that
    def __gt__(self, that):
        """Test whether self is a proper superset of *that*."""
        return self._view > that
    def __le__(self, that):
        """Test whether self is contained within *that*."""
        return self._view <= that
    def __ge__(self, that):
        """Test whether *that* is contained within self."""
        return self._view >= that
    def __and__(self, that):
        """Return the intersection of self and *that*."""
        return self._view & that
    def __or__(self, that):
        """Return the union of self and *that*."""
        return self._view | that
    def __sub__(self, that):
        """Return the difference of self and *that*."""
        return self._view - that
    def __xor__(self, that):
        """Return the symmetric difference of self and *that*."""
        return self._view ^ that
    def isdisjoint(self, that):
        """Return True if and only if *that* is disjoint with self."""
        if version_info[0] == 2:
            return not any(key in self._view for key in that)
        else:
            return self._view.isdisjoint(that)
    def __repr__(self):
        return 'PriorityDict_keys({0})'.format(repr(list(self)))

class ValuesView(AbstractValuesView, Sequence):
    """
    A ValuesView object is a dynamic view of the dictionary's values, which
    means that when the dictionary's values change, the view reflects those
    changes.

    The ValuesView class implements the Sequence Abstract Base Class.
    """
    def __init__(self, priority_dict):
        """
        Initialize a ValuesView from a PriorityDict container as `priority_dict`.
        """
        self._list = priority_dict._list
        if hexversion < 0x03000000:
            self._view = priority_dict._dict.viewvalues()
        else:
            self._view = priority_dict._dict.values()
    def __len__(self):
        """Return the number of entries in the dictionary."""
        return len(self._view)
    def __contains__(self, value):
        """
        Return True if and only if *value* is on the underlying dictionary's
        values.
        """
        return value in self._view
    def __iter__(self):
        """
        Return an iterator over the values in the dictionary.  Values are
        iterated over in value sorted order.

        Iterating views while adding or deleting entries in the dictionary may
        raise a `RuntimeError` or fail to iterate over all entries.
        """
        return iter(value for value, key in self._list)
    def __getitem__(self, index):
        """
        Efficiently return value at *index* in iteration.

        Supports slice notation and negative indexes.
        """
        if isinstance(index, slice):
            return [value for value, key in self._list[index]]
        else:
            return self._list[index][0]
    def __reversed__(self):
        """
        Return a reverse iterator over the values in the dictionary.  Values are
        iterated over in reverse sort order of the values.

        Iterating views while adding or deleting entries in the dictionary may
        raise a `RuntimeError` or fail to iterate over all entries.
        """
        return iter(value for value, key in reversed(self._list))
    def index(self, value):
        """
        Return index of *value* in self.

        Raises ValueError if *value* is not found.
        """
        pos = self._list.bisect_left((value,))
        if pos == len(self._dict) or self._list[pos][0] != value:
            raise ValueError
        else:
            return pos
    def count(self, value):
        """Return the number of occurrences of *value* in self."""
        start = self._list.bisect_left((value,))
        end = self._list.bisect_right((value, _Biggest))
        return end - start
    def __lt__(self, that):
        raise TypeError
    def __gt__(self, that):
        raise TypeError
    def __le__(self, that):
        raise TypeError
    def __ge__(self, that):
        raise TypeError
    def __and__(self, that):
        raise TypeError
    def __or__(self, that):
        raise TypeError
    def __sub__(self, that):
        raise TypeError
    def __xor__(self, that):
        raise TypeError
    def __repr__(self):
        return 'PriorityDict_values({0})'.format(repr(list(self)))

class ItemsView(AbstractItemsView, Set, Sequence):
    """
    An ItemsView object is a dynamic view of the dictionary's ``(key,
    value)`` pairs, which means that when the dictionary changes, the
    view reflects those changes.

    The ItemsView class implements the Set and Sequence Abstract Base Classes.
    However, the set-like operations (``&``, ``|``, ``-``, ``^``) will only
    operate correctly if all of the dictionary's values are hashable.
    """
    def __init__(self, priority_dict):
        """
        Initialize an ItemsView from a PriorityDict container as `priority_dict`.
        """
        self._list = priority_dict._list
        if hexversion < 0x03000000:
            self._view = priority_dict._dict.viewitems()
        else:
            self._view = priority_dict._dict.items()
    def __len__(self):
        """Return the number of entries in the dictionary."""
        return len(self._view)
    def __contains__(self, item):
        """
        Return True if and only if *item* is one of the underlying dictionary's
        items.
        """
        return item in self._view
    def __iter__(self):
        """
        Return an iterable over the items in the dictionary. Items are iterated
        over in value sorted order.

        Iterating views while adding or deleting entries in the dictionary may
        raise a RuntimeError or fail to iterate over all entries.
        """
        return iter((key, value) for value, key in self._list)
    def __getitem__(self, index):
        """Return the item as position *index*."""
        if isinstance(index, slice):
            return [(key, value) for value, key in self._list[index]]
        else:
            value, key  = self._list[index]
            return (key, value)
    def __reversed__(self):
        """
        Return a reversed iterable over the items in the dictionary. Items are
        iterated over in reverse value sort order.

        Iterating views while adding or deleting entries in the dictionary may
        raise a RuntimeError or fail to iterate over all entries.
        """
        return iter((key, value) for value, key in reversed(self._list))
    def __eq__(self, that):
        """Test set-like equality with *that*."""
        return self._view == that
    def __ne__(self, that):
        """Test set-like inequality with *that*."""
        return self._view != that
    def __lt__(self, that):
        """Test whether self is a proper subset of *that*."""
        return self._view < that
    def __gt__(self, that):
        """Test whether self is a proper superset of *that*."""
        return self._view > that
    def __le__(self, that):
        """Test whether self is contained within *that*."""
        return self._view <= that
    def __ge__(self, that):
        """Test whether *that* is contained within self."""
        return self._view >= that
    def __and__(self, that):
        """Return the intersection of self and *that*."""
        return self._view & that
    def __or__(self, that):
        """Return the union of self and *that*."""
        return self._view | that
    def __sub__(self, that):
        """Return the difference of self and *that*."""
        return self._view - that
    def __xor__(self, that):
        """Return the symmetric difference of self and *that*."""
        return self._view ^ that
    def isdisjoint(self, that):
        """Return True if and only if *that* is disjoint with self."""
        if hexversion < 0x03000000:
            for item in that:
                if item in self._view:
                    return False
            return True
        else:
            return self._view.isdisjoint(that)
    def __repr__(self):
        return 'PriorityDict_items({0})'.format(repr(list(self)))
