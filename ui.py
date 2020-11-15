import curses.panel
import time
from board import Board
from config import config
import traceback
import sys
import random
from math import floor, ceil

FG = 232
BG = 255


class FPSMonitor:
    def __init__(self):
        self.data = [time.time() + i / 50 for i in range(100)]
    
    def tick(self):
        self.data.append(time.time())
        self.data.pop(0)
    
    @property
    def fps(self):
        return 1 / ((self.data[-1] - self.data[1]) / 100)


class UIError(Exception): pass


class Grid:
    """
    A helper class to render the grid with Unicode half characters
    so that the output is approximately square
    """
    
    VBAR = "┃"
    HBAR = "━"
    TOPLEFT = "┏"
    TOPRIGHT = "┓"
    BOTTOMLEFT = "┗"
    BOTTOMRIGHT = "┛"
    LEFT = "┣"
    RIGHT = "┫"
    TOP = "┳"
    BOTTOM = "┻"
    CENTER = "╋"
    SPACE = "　"
    
    def __init__(self, width, height):
        """
        the width and height does not include borders
        :param width: the width, in interpolated pixels
        :param height: the height, in interpolated pixels
        """
        self.width = width
        self.height = height
        self.grid = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                row.append(random.choice([self.SPACE]))
            self.grid.append(row)
    
    def put(self, row: int, col: int, char: str):
        if 0x30 <= (charcode := ord(char)) <= 0x40:
            charcode += 0xff10 - 0x30
            char = chr(charcode)
        self.grid[row][col] = char
    
    def render(self):
        res = []
        row = self.TOPLEFT
        for x in range(self.width - 1):
            row += self.HBAR * 4 + self.TOP
        row += self.HBAR * 4 + self.TOPRIGHT
        res.append(row)
        for y in range(self.height - 2):
            row = self.VBAR
            for x in range(self.width):
                row += ' ' + self.grid[y][x] + ' ' + self.VBAR
            res.append(row)
            
            row = self.LEFT
            for x in range(self.width - 1):
                row += self.HBAR * 4 + self.CENTER
            row += self.HBAR * 4 + self.RIGHT
            res.append(row)
        
        row = self.VBAR
        for x in range(self.width):
            row += ' ' + self.grid[-1][x] + ' ' + self.VBAR
        res.append(row)
        
        row = self.BOTTOMLEFT
        for x in range(self.width - 1):
            row += self.HBAR * 4 + self.BOTTOM
        row += self.HBAR * 4 + self.BOTTOMRIGHT
        res.append(row)
        
        return res


class UIManager:
    def __init__(self, win: curses.window):
        self.mwin = win
        self.board = Board()
        self.mouse_y = 0
        self.mouse_x = 0
        self.monitor = FPSMonitor()
        self.grid = Grid(config.board_width, config.board_height)
        self.should_exit = False
    
    def exit(self):
        self.should_exit = True
    
    def start(self):
        self.start_time = time.time()
    
    def tick(self):
        ch = self.mwin.getch()
        self.mwin.erase()
        winh, winw = self.mwin.getmaxyx()
        mouse_button = -1
        if ch == curses.KEY_MOUSE:
            try:
                _, self.mouse_x, self.mouse_y, z, mouse_button = curses.getmouse()
            except curses.error:
                pass
        cell_width = config.use_emojis + 1
        
        self.mwin.addch(self.mouse_y, self.mouse_x, curses.ACS_DIAMOND)
        
        # Draw the window
        self.mwin.addstr(1, 1, '╭' + '─' * (winw - 4) + '╮')
        self.mwin.addch(2, 1, '│')
        self.mwin.addch(2, winw - 2, '│')
        self.mwin.addstr(2, (winw - 24) // 2 + 2, 'TERMINAL MINESWEEPER')
        self.mwin.addstr(3, 1, '├' + '─' * (winw - 4) + '┤')
        for y in range(4, winh - 1):
            self.mwin.addch(y, 1, '│')
            self.mwin.addch(y, winw - 2, '│')
        self.mwin.addstr(winh - 1, 1, '╰' + '─' * (winw - 4) + '╯')
        
        self.mwin.addstr(4, 3, f'FPS: {round(self.monitor.fps, 2):0<5}')
        for i, row in enumerate(self.grid.render()):
            self.mwin.addstr(i + 6, 5, row)
        
        self.mwin.refresh()
        self.monitor.tick()


def mainloop(win: curses.window):
    win.clear()
    frame_delay = round(1000 / config.framerate)
    manager = UIManager(win)
    while True:
        manager.tick()
        curses.flushinp()
        last_frame_time = round((manager.monitor.data[-1] - manager.monitor.data[-2]) * 1000)
        curses.napms(frame_delay - (last_frame_time - frame_delay))


def calc_first_frame(height, width):
    """
    calculate the first frame to print for the startup animation
    :param height: height of the screen
    :param width: width of the screen
    :return: a list of strings, each representing a line
    """
    def pad(line, center=False):
        """a simple """
        if not center: return ' │' + line + ' ' * (width - len(line) - 4) + '│ '
        return ' │' + ' ' * floor((width - len(line) - 4) / 2) + line + ' ' * ceil((width - len(line) - 4) / 2) + '│ '
    
    frame = [' ' * width]  # first line is empty
    line = ' ╭' + '─' * (width - 4) + '╮ '
    frame.append(line)
    frame.append(pad('TERMINAL MINESWEEPER', center=True))
    line = ' ├' + '─' * (width - 4) + '┤ '
    frame.append(line)
    for y in range(height - 5):
        frame.append(pad(''))
    line = ' ╰' + '─' * (width - 4) + '╯ '
    frame.append(line)
    return frame


def main():
    try:
        stdscr = curses.initscr()
    except curses.error:
        return 'Cannot initialize curses', 1
    
    exit_message = None
    exit_status = 0
    
    try:
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        stdscr.nodelay(True)
        
        curses.mousemask(curses.REPORT_MOUSE_POSITION |
                         curses.ALL_MOUSE_EVENTS
                         )
        curses.mouseinterval(0)  # don't wait for mouse
        curses.curs_set(0)  # invisible cursor
        print('\033[?1003h', flush=True)
        # enable mouse tracking with the XTERM API
        # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking
        
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, FG, BG)
        stdscr.bkgd(' ', curses.color_pair(1))
        
        # initialization complete
        mainloop(stdscr)
    except UIError as err:
        exit_message = err.args[0]
        exit_status = 1
    except KeyboardInterrupt:
        pass
    except:
        exit_message = traceback.format_exc()
        exit_status = 1
    finally:
        # revert the terminal state
        print('\033[?1003l', flush=True)
        stdscr.keypad(False)
        curses.flushinp()
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        return exit_message, exit_status
