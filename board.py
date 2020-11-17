import random
from enum import auto, IntFlag

from config import Config

config = Config()


class State(IntFlag):
    """A helper class to hold the state of a cell. It's a subclass of enum.IntFlag"""
    REVEALED = auto()
    EXPLODED = auto()
    MINE = auto()
    HIGHLIGHT = auto()
    FLAGGED = auto()

# expose the variables to global scope like in C
# yes i could have used a globals().update() but my IDE isn't happy with that :(
REVEALED = State.REVEALED
EXPLODED = State.EXPLODED
MINE = State.MINE
HIGHLIGHT = State.HIGHLIGHT
FLAGGED = State.FLAGGED



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

    def flag(self):
        """Flag the cell"""
        self.state |= FLAGGED

    def explode(self):
        """Set the cell to have exploded"""
        self.state |= EXPLODED

    def set_mine(self):
        """Set the cell to be a mine"""
        self.state |= MINE

    def reveal(self):
        """Reveal the content of a cell"""
        self.state |= REVEALED

    def __str__(self):
        emo = config.use_emojis
        if FLAGGED in self.state:
            return '🚩' if emo else 'Ｆ'
        if EXPLODED in self.state:
            return '💥' if emo else 'Ｏ'
        if MINE | REVEALED in self.state:
            return '💣' if emo else 'Ｘ'
        if REVEALED in self.state and not self.value:
            return '　'
        if REVEALED in self.state:
            return chr(0xff10 + self.value)
        return '　'

    def __repr__(self):
        return f'<Cell {self.state}>'

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


class Board:
    def __init__(self):
        self.board = []
        self.cells = []
        self.width=config.board_width
        self.height=config.board_height
        for x in range(self.width):
            self.board.append([])
            for y in range(self.height):
                cell = Cell(x, y)
                self.board[-1].append(cell)
                self.cells.append(cell)

    def __iter__(self):
        return iter(self.board)

    def init_mines(self,avoid:tuple):
        """
        Deferred initialization of mines to guarantee the first click is not
        a mine.
        :param avoid: the position that will not be a mine
        :return: None
        """

        cells=self.cells.copy()
        cells.remove(avoid)
        for c in random.sample(cells, config.mine_count):
            c.set_mine() # initialize the mines

        for c in cells:
            c.calc_value()

    def __getitem__(self, item):
        """a proxy function to translate all indexes to the underlying list"""
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
        return all(REVEALED in c.state or FLAGGED in c.state for c in self.cells)
