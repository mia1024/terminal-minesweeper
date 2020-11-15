from config import Config
from enum import IntFlag, auto
import random

config = Config()


class State(IntFlag):
    REVEALED = auto()
    EXPLODED = auto()
    MINE = auto()
    HIGHLIGHT = auto()
    FLAGGED = auto()


REVEALED = State.REVEALED
EXPLODED = State.EXPLODED
MINE = State.MINE
HIGHLIGHT = State.HIGHLIGHT
FLAGGED = State.FLAGGED


# yes i could have used a globals().update but my IDE isn't happy with that :(


class CellMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cls.__objs = {}
    
    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        cls.__objs[args] = obj
        return obj
    
    def __getitem__(cls, item):
        return cls.__objs[item]
    
    def __contains__(cls, item):
        return item in cls.__objs


class Cell(metaclass=CellMeta):
    __cells = {}
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = State(0)
        self.value = 0
        self.__cells[(x, y)] = self
    
    def flag(self):
        self.state |= FLAGGED
    
    def explode(self):
        self.state |= EXPLODED
    
    def set_mine(self):
        self.state |= MINE
    
    def reveal(self):
        self.state |= REVEALED
    
    def __str__(self):
        emo = config.use_emojis
        if FLAGGED in self.state: return '🚩' if emo else 'Ｆ'
        if EXPLODED in self.state: return '💥' if emo else 'Ｏ'
        if MINE | REVEALED in self.state: return '💣' if emo else 'Ｘ'
        if REVEALED in self.state and not self.value: return '　'
        if REVEALED in self.state: return chr(0xff10 + self.value)
        return '　'
    
    def __repr__(self):
        return f'<Cell {self.state}>'
    
    def calc_value(self):
        surroundings = (
            (self.x + 1, self.y + 1),
            (self.x + 1, self.y + 0),
            (self.x + 1, self.y - 1),
            (self.x - 1, self.y + 1),
            (self.x - 1, self.y + 0),
            (self.x - 1, self.y - 1),
            (self.x + 0, self.y + 1),
            (self.x + 0, self.y - 1),
        )
        for surr in surroundings:
            if surr in Cell:
                self.value += MINE in Cell[surr].state


class Board:
    def __init__(self):
        self._board = []
        cells = []
        for x in range(config.board_width):
            self._board.append([])
            for y in range(config.board_height):
                cell = Cell(x, y)
                self._board[-1].append(cell)
                cells.append(cell)
        for c in random.sample(cells, config.mine_count):
            c.set_mine()
        
        for c in cells:
            c.calc_value()
            c.reveal()
    
    def __iter__(self):
        return iter(self._board)
    
    def __str__(self):
        s = ''
        for row in self._board:
            for col in row:
                s += str(col)
            s += '\n'
        return s
