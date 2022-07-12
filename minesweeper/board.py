import random
from .config import Config
from .debug import debug_print

config = Config()


class GameOver(Exception):
    """
    This exception will be raised by a cell during the revealing routing
    if it is a mine
    """


class CellMeta(type):
    """
    A straightforward metaclass for the Cell class so that `Cell[y,x]` and
     `(y,x) in Cell` are legal
     """

    def __init__(cls, *args, **kwargs):
        """add the objs dict to the class"""
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
        """enabling Cell[y,x] and maps to the underlying object dict"""
        return cls.__objs[item]

    def __contains__(cls, item):
        """enabling (y,x) in cell and maps to the underlying object dict"""
        return item in cls.__objs


class Cell(metaclass = CellMeta):
    """The class for a cell in on the minesweeper board"""

    def __init__(self, y, x):
        """Initializes the cell"""
        self.x = x
        self.y = y
        self.is_revealed=False
        self.is_flagged=False
        self.is_highlighted=False
        self.is_exploded=False
        self.is_mine=False
        self.is_mine=False
        self.value = 0
        self.surroundings = []  # this will be initialized in self.calc_values()

    def flag(self):
        """Flag the cell. If it's flagged, unflag it"""
        if not self.is_revealed:
            debug_print(f'{repr(self)} toggle flag')
            self.is_flagged = not self.is_flagged

    def explode(self):
        """Set the cell to have exploded"""
        debug_print(f'{repr(self)} set exploded')
        self.is_exploded=True

    def set_mine(self):
        """Set the cell to be a mine"""
        debug_print(f'{repr(self)} set mine')
        self.is_mine=True

    def highlight(self, force = False):
        """
        Toggles the highlghting state of the cell. blocks the highlight if the
        cell is revealed or flagged
        """
        if force:
            debug_print(f'{repr(self)} toggle highlight (force)')
            self.is_highlighted=not self.is_highlighted
        elif not self.is_revealed:
            debug_print(f'{repr(self)} toggle highlight')
            self.is_highlighted = not self.is_highlighted
        else:
            debug_print(f'{repr(self)} remove highlight')
            self.is_highlighted=False

    def reveal(self, chain = False, force = False):
        """
        Reveal the content of a cell
        :param chain: whether the reveal should be chained to the surrounding
        :param force: whether the reveal is forced
        :return: a list of cells, potentially empty, that should be revealed next
        """
        if self.is_flagged and not force:
            return []  # A flagged cell can't be revealed until unflagged
        debug_print(f'{repr(self)} reveal')
        self.is_revealed=True
        self.is_highlighted=False
        if self.is_mine and not force:
            raise GameOver(self)
        if self.value == 0:
            to_reveal = []

            for cell in self.surroundings:
                if not cell.is_revealed:
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
        """
        converts the cell to appropriate emoji (or not) to be displayed
        """
        emo = config.use_emojis
        if self.is_exploded:
            return '💥' if emo else '＊'
        if self.is_revealed and self.is_mine:
            if self.is_flagged:
                return '🏁' if emo else 'Ｘ'
            return '💣' if emo else 'Ｏ'
        if self.is_flagged:
            return '🚩' if emo else 'Ｆ'
        if self.is_revealed:
            # if self.value == 0:
            #     return '　'
            return chr(0xff10 + self.value)
        return '　'

    def __repr__(self):
        """
        returns the string representation of the cell including all the necessary data
        """
        return f'<Cell {self.value} at {(self.y, self.x)}>'

    def calc_value(self):
        """
        Calculate the value of the cell (the number of mines in vicinity) based on its surroundings
        """
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
                self.value += Cell[surr].is_mine
                self.surroundings.append(Cell[surr])

    def area_reveal(self, chain = False):
        """
        Reveals all the cell around this cell if the number of cells flagged
        in its surrounding is the same as the number of mines there are
        """
        if not self.is_revealed:
            return []
        flags = sum(s.is_flagged for s in self.surroundings)
        to_reveal = []
        if flags == self.value:
            for cell in self.surroundings:
                if not cell.is_flagged:
                    to_reveal.extend(cell.reveal(chain))
        return to_reveal

    def __hash__(self):
        """
        returns a hash so that the cell can be added to a hashtable
        """
        return self.y * config.board_height + self.x


class Board:
    """
    This class holds the data for the game board, including all the cells.
    it is primarily responsible for managing initializing a new game
    and restart
    """

    def __init__(self):
        """
        Initializes the board
        """
        self.board = []
        self.cells = []
        self.width = config.board_width
        self.height = config.board_height
        for y in range(self.height):
            self.board.append([])
            for x in range(self.width):
                cell = Cell(y, x)
                self.board[-1].append(cell)
                self.cells.append(cell)

    def __iter__(self):
        """
        allows iteration over the board object, exposes all the cells
        """
        return iter(self.cells)

    def init_mines(self, clicked: Cell):
        """
        Deferred initialization of mines to guarantee the first click is a
        white space.
        :param avoid: the position that will not be a mine
        :return: None
        """

        count = 0
        while True:
            for c in random.sample(self.cells, config.mine_count):
                # if the there are more mines than cells this call
                # will raise an error, however we let the game
                # crash because the player definitely expected
                # this when they entered the mine counts

                c.set_mine()  # initialize the mines

            for c in self.cells:
                c.calc_value()

            if clicked.value != 0 or clicked.is_mine:
                if count < len(self.cells):
                    self.reset()
                else:
                    # give up. the player sets an impossible option
                    # such as 3x3 board with 5 mines
                    return
            else:
                return

            count += 1

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
        return all(c.is_revealed or c.is_mine for c in self.cells)

    def reveal_all(self):
        """
        force reveal all the cells when game is over
        """
        for cell in self:
            cell.reveal(force = True)

    def reset(self):
        """
        reset the board. because of the cell metaclass new cell instances
        should not be constructed, so we clear the attributes instead
        """
        for cell in self.cells:
            cell.is_revealed = False
            cell.is_flagged = False
            cell.is_highlighted = False
            cell.is_exploded = False
            cell.is_mine = False
            cell.value = 0
            cell.surroundings = []

    def flag_count(self):
        """
        calculates total number of flaged cells
        """
        return sum(s.is_flagged for s in self.cells)
