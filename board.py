from config import config
from enum import IntFlag, auto


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
R = State.REVEALED
E = State.EXPLODED
M = State.MINE
H = State.HIGHLIGHT
F = State.FLAGGED


# yes i could have used a globals().update but my IDE isn't happy with that :(

class Cell:
    def __init__(self, x, y, char=None):
        self.x = x
        self.y = y
        self.char = char or ' ' * (config.use_emojis + 1)
        self.is_mine = False
        self.color = 0
        self.state = State(0)
    
    def flag(self):
        if config.use_emojis:
            self.char = '🚩'
        else:
            self.char = 'F'
        self.state |= F
    
    def explode(self):
        if config.use_emojis:
            self.char = '💥'
        else:
            self.char = 'O'
        self.state |= E
    
    def mine(self):
        if config.use_emojis:
            self.char = '💣'
        else:
            self.char = 'X'
        self.state |= M


class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._board = []
        for x in range(width):
            self._board.append([])
            for y in range(height):
                self._board[-1].append(Cell(x, y))
    
    def __iter__(self):
        return iter(self._board)
