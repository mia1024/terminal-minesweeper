from array import array

BOX_PAINTING_SYMBOLS_DICT = {
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

BOX_PAINTING_SYMBOLS = array("u", [" "] * (3 ** 4))
for t, s in BOX_PAINTING_SYMBOLS_DICT.items():
    up, down, left, right = t
    BOX_PAINTING_SYMBOLS[up * 3 ** 3 + down * 3 ** 2 + left * 3 + right] = s


def box(up: int = -1, down: int = -1, left: int = -1, right: int = -1) -> str:
    """A convenient function for indexing the box drawing symbols"""
    return BOX_PAINTING_SYMBOLS[(up + 1) * 3 ** 3 + (down + 1) * 3 ** 2 + (left + 1) * 3 + (right + 1)]