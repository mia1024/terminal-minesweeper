import random
from enum import IntFlag
from typing import List
from config import Config
from debug import debug_print

config = Config()


class State(IntFlag):
    """A helper class to hold the state of a cell. It's a subclass of enum.IntFlag"""
    REVEALED = 1 << 0
    EXPLODED = 1 << 1
    MINE = 1 << 2
    HIGHLIGHT = 1 << 3
    FLAGGED = 1 << 4


# expose the variables to global scope like in C
# yes i could have used a globals().update() but my IDE isn't happy with that :(
REVEALED = State.REVEALED
EXPLODED = State.EXPLODED
MINE = State.MINE
HIGHLIGHT = State.HIGHLIGHT
FLAGGED = State.FLAGGED


class GameOver(Exception): pass


class CellMeta(type):
    """
    A simple metaclass for the Cell class so that `Cell[y,x]` and
     `(y,x) in Cell` are legal
     """

    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.__objs = {}

    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)

        # This technically caches all arguments. But since we know the
        # signature of the cell args==(y,x), it's never a problem. Also,
        # since only one copy of the board will ever be initialized,
        # we don't need to worry about cells with duplicate indices.
        cls.__objs[args] = obj
        return obj

    def __getitem__(cls, item):
        return cls.__objs[item]

    def __contains__(cls, item):
        return item in cls.__objs


class Cell(metaclass = CellMeta):

    def __init__(self, y, x):
        self.x = x
        self.y = y
        self.state = State(0)
        self.value = 0
        self.surroundings = []  # this will be initialized in self.calc_values()

    def flag(self):
        """Flag the cell. If it's flagged, unflag it"""
        if REVEALED not in self.state:
            debug_print(f'{repr(self)} toggle flag')
            self.state ^= FLAGGED
            self.state ^= HIGHLIGHT
            # manually bypass the highlight lock after flagging

    def explode(self):
        """Set the cell to have exploded"""
        debug_print(f'{repr(self)} set exploded')
        self.state |= EXPLODED

    def set_mine(self):
        """Set the cell to be a mine"""
        debug_print(f'{repr(self)} set mine')
        self.state |= MINE

    @property
    def is_revealed(self):
        return REVEALED in self.state

    @property
    def is_highlighted(self):
        return HIGHLIGHT in self.state

    def highlight(self, force = False):
        if not force and not (REVEALED in self.state or FLAGGED in self.state):
            debug_print(f'{repr(self)} toggle highlight')
            self.state ^= HIGHLIGHT

    def reveal(self, chain = False, force = False):
        """
        Reveal the content of a cell
        :param chain: whether the reveal should be chained to the surrounding
        :param force: whether the reveal is forced
        :return: a list of cells, potentially empty, that should be revealed next
        """
        if FLAGGED in self.state and not force:
            return []  # A flagged cell can't be revealed until unflagged
        debug_print(f'{repr(self)} reveal')
        self.state |= REVEALED
        self.state &= ~HIGHLIGHT
        if MINE in self.state and not force:
            raise GameOver(self)
        if self.value == 0:
            to_reveal = []

            for cell in self.surroundings:
                if REVEALED not in cell.state:
                    to_reveal.append(cell)
            # debug_print(to_reveal)
            if chain:
                for cell in to_reveal:
                    cell.reveal(True, force)
                return []
            else:
                return to_reveal
        return []

    def __str__(self):
        emo = config.use_emojis
        if EXPLODED in self.state:
            return '💥' if emo else '＊'
        if MINE | FLAGGED | REVEALED in self.state:
            return '⛳' if emo else 'Ｘ'
        if MINE | REVEALED in self.state:
            return '💣' if emo else 'Ｏ'
        if FLAGGED in self.state:
            return '🚩' if emo else 'Ｆ'
        # if REVEALED in self.state and not self.value:
        #     return '　'
        if REVEALED in self.state:
            if self.value == 0:
                return '　'
            return chr(0xff10 + self.value)
        return '　'

    def __repr__(self):
        return f'<Cell {self.value} at {(self.y, self.x)} {self.state}>'

    def calc_value(self):
        """Calculate the value of the cell (the number of mines in vicinity) based on its surroundings"""
        surroundings = (
            (self.y + 1, self.x + 1),
            (self.y + 1, self.x + 0),
            (self.y + 1, self.x - 1),
            (self.y - 1, self.x + 1),
            (self.y - 1, self.x + 0),
            (self.y - 1, self.x - 1),
            (self.y + 0, self.x + 1),
            (self.y + 0, self.x - 1),
        )
        for surr in surroundings:
            if surr in Cell:
                self.value += MINE in Cell[surr].state
                self.surroundings.append(Cell[surr])

    def area_reveal(self, chain = False):
        if not REVEALED in self.state:
            return []
        flags = sum(FLAGGED in s.state for s in self.surroundings)
        to_reveal = []
        if flags == self.value:
            for cell in self.surroundings:
                if FLAGGED not in cell.state:
                    to_reveal.extend(cell.reveal(chain))
        return to_reveal

    def __hash__(self):
        return hash((self.y,self.x))

class Board:
    def __init__(self):
        self.board = []
        self.cells = []
        self.width = config.board_width
        self.height = config.board_height
        for x in range(self.width):
            self.board.append([])
            for y in range(self.height):
                cell = Cell(x, y)
                self.board[-1].append(cell)
                self.cells.append(cell)

    def __iter__(self):
        for row in self.board:
            for cell in row:
                yield cell

    def init_mines(self, clicked: Cell):
        """
        Deferred initialization of mines to guarantee the first click is not
        a mine.
        :param avoid: the position that will not be a mine
        :return: None
        """

        while True:
            for c in random.sample(self.cells, config.mine_count):
                c.set_mine()  # initialize the mines

            for c in self.cells:
                c.calc_value()

            if clicked.value != 0 or MINE in clicked.state:
                self.reset()
            else:
                return

    def __getitem__(self, item):
        """a proxy function to translate all indexes to the underlying list"""
        if isinstance(item, tuple) and len(item) == 2:
            return self.board[item[0]][item[1]]
        return self.board[item]

    def __str__(self):
        """
        :return: the string of cell in which each cell is turned into it's
        character
        """
        s = ''
        for row in self.board:
            for col in row:
                s += str(col)
            s += '\n'
        return s

    def check_win(self):
        """
        :return: a boolean indicating whether the game has been won
        """
        return all(REVEALED in c.state or MINE in c.state for c in self.cells)

    def reveal_all(self):
        for cell in self:
            cell.reveal(force = True)

    def reset(self):
        for cell in self.cells:
            cell.state = State(0)
            cell.value = 0
            cell.surroundings = []
