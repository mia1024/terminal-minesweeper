from functools import partial

BOX_PAINTING_SYMBOLS = {
    # order: (up, down, left, right)
    # properties: (0: None, 1: light, 2: heavy)
    (0, 0, 1, 1): '─',
    (0, 0, 2, 2): '━',
    (1, 1, 0, 0): '│',
    (2, 2, 0, 0): '┃',
    (0, 1, 0, 1): '┌',
    (0, 1, 0, 2): '┍',
    (0, 2, 0, 1): '┎',
    (0, 2, 0, 2): '┏',
    (0, 1, 1, 0): '┐',
    (0, 2, 1, 0): '┑',
    (0, 1, 2, 0): '┒',
    (0, 2, 2, 0): '┓',
    (1, 0, 0, 1): '└',
    (1, 0, 0, 2): '┕',
    (2, 0, 0, 1): '┖',
    (2, 0, 0, 2): '┗',
    (1, 0, 1, 0): '┘',
    (1, 0, 2, 0): '┙',
    (2, 0, 1, 0): '┚',
    (2, 0, 2, 0): '┛',
    (1, 1, 0, 1): '├',
    (1, 1, 0, 2): '┝',
    (2, 1, 0, 1): '┞',
    (1, 2, 0, 1): '┟',
    (2, 2, 0, 1): '┠',
    (2, 1, 0, 2): '┡',
    (1, 2, 0, 2): '┢',
    (2, 2, 0, 2): '┣',
    (1, 1, 1, 0): '┤',
    (1, 1, 2, 0): '┥',
    (2, 1, 1, 0): '┦',
    (1, 2, 1, 0): '┧',
    (2, 2, 1, 0): '┨',
    (2, 1, 2, 0): '┩',
    (1, 2, 2, 0): '┪',
    (2, 2, 2, 0): '┫',
    (0, 1, 1, 1): '┬',
    (0, 1, 2, 1): '┭',
    (0, 1, 1, 2): '┮',
    (0, 1, 2, 2): '┯',
    (0, 2, 1, 1): '┰',
    (0, 2, 2, 1): '┱',
    (0, 2, 1, 2): '┲',
    (0, 2, 2, 2): '┳',
    (1, 0, 1, 1): '┴',
    (1, 0, 2, 1): '┵',
    (1, 0, 1, 2): '┶',
    (1, 0, 2, 2): '┷',
    (2, 0, 1, 1): '┸',
    (2, 0, 2, 1): '┹',
    (2, 0, 1, 2): '┺',
    (2, 0, 2, 2): '┻',
    (1, 1, 1, 1): '┼',
    (1, 1, 2, 1): '┽',
    (1, 1, 1, 2): '┾',
    (1, 1, 2, 2): '┿',
    (2, 1, 1, 1): '╀',
    (1, 2, 1, 1): '╁',
    (2, 2, 1, 1): '╂',
    (2, 1, 2, 1): '╃',
    (2, 1, 1, 2): '╄',
    (1, 2, 2, 1): '╅',
    (1, 2, 1, 2): '╆',
    (2, 1, 2, 2): '╇',
    (1, 2, 2, 2): '╈',
    (2, 2, 2, 1): '╉',
    (2, 2, 1, 2): '╊',
    (2, 2, 2, 2): '╋',
}


def box(up, down, left, right):
    """A convenient function for indexing the box drawing symbols"""
    return BOX_PAINTING_SYMBOLS[up, down, left, right]


class Box:
    """
    A convenient function to increase the readability of rest of the code,
    although this class itself might not be super readable. It should
    be able to be used anywhere that expects a string.
    """

    def __init__(self, up = -1, down = -1, left = -1, right = -1):
        """
        Initialize the instance
        """
        self._up = up + 1
        self._down = down + 1
        self._left = left + 1
        self._right = right + 1

    def __repr__(self):
        """
        convert self to a string
        """
        return box(self._up, self._down, self._left, self._right)

    def __mul__(self, other):
        """
        multiplies self as if multiplying a string
        """
        return str(self) * other

    def __add__(self, other):
        """
        add self to other as if adding strings
        """
        return str(self) + str(other)

    def up(self_or_value = 0, value = 0):
        """
        set the up value of an instance to the first argument passed in + 1
        """
        if isinstance(self_or_value, int):
            return Box(up = self_or_value)
        else:
            self_or_value._up = value + 1
            return self_or_value

    def down(self_or_value = 0, value = 0):
        """
        set the down value of an instance to the first argument passed in + 1
        """
        if isinstance(self_or_value, int):
            return Box(down = self_or_value)
        else:
            self_or_value._down = value + 1
            return self_or_value

    def left(self_or_value = 0, value = 0):
        """
        set the left value of an instance to the first argument passed in + 1
        """
        if isinstance(self_or_value, int):
            return Box(left = self_or_value)
        else:
            self_or_value._left = value + 1
            return self_or_value

    def right(self_or_value = 0, value = 0):
        """
        set the right value of an instance to the first argument passed in + 1
        """
        if isinstance(self_or_value, int):
            return Box(right = self_or_value)
        else:
            self_or_value._right = value + 1
            return self_or_value
