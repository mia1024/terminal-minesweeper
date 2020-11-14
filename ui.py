import curses.panel
import time
from board import Board
from config import config
import traceback
import sys


class FPSMonitor:
    def __init__(self):
        self.data = [60 - i for i in range(60)]
    
    def tick(self):
        self.data.append(time.time())
        self.data.pop(0)
    
    @property
    def fps(self):
        return 1 / ((self.data[-1] - self.data[1]) / 60)


class UIError(Exception): pass


class Grid:
    """
    A helper class to render the grid with Unicode half characters
    so that the output is approximately square
    """
    
    SPACE = '\u3000'
    VBAR = '\u2551'
    HBAR = '\u2550'
    TOPLEFT = '\u2554'
    TOPRIGHT = '\u2557'
    BOTTOMLEFT = '\u255a'
    BOTTOMRIGHT = '\u255d'
    LEFT = '\u2560'
    RIGHT = '\u2563'
    TOP = '\u2566'
    BOTTOM = '\u2569'
    CENTER = '\u256c'
    
    def __init__(self, width, height):
        """
        the width and height does not include borders
        :param width: the width, in interpolated pixels
        :param height: the height, in interpolated pixels
        """
        self.width = width
        self.height = height
        self.grid = [[chr(0xff10+(i%10)) for i in range(height)]] * width
    
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
        self.board = Board(config.board_width, config.board_height)
        self.mouse_y = 0
        self.mouse_x = 0
        self.monitor = FPSMonitor()
        self.grid=Grid(config.board_width,config.board_height)
    
    def start(self):
        self.start_time = time.time()
    
    def tick(self):
        ch = self.mwin.getch()
        self.mwin.erase()
        mouse_button = -1
        if ch == curses.KEY_MOUSE:
            try:
                _, self.mouse_x, self.mouse_y, z, mouse_button = curses.getmouse()
            except curses.error:
                pass
        cell_width = config.use_emojis + 1
        
        self.mwin.addch(self.mouse_y, self.mouse_x, curses.ACS_DIAMOND)
        #
        # UPPER = '\u2580'
        # LOWER = '\u2584'
        # FULL = '\u2588'
        #
        self.mwin.addstr(1, 1, f'FPS: {round(self.monitor.fps, 1)}')
        # self.mwin.addstr(2, 1, FULL + UPPER * 4 + FULL + UPPER * 4 + FULL)
        # self.mwin.addstr(3, 1, '\u2588 \uff16 \u2588 \uff17 \u2588')
        # self.mwin.addstr(4, 1, FULL + LOWER * 4 + FULL + LOWER * 4 + FULL)
        # self.mwin.addstr(5, 1, FULL + UPPER * 4 + FULL + UPPER * 4 + FULL)
        # self.mwin.addstr(6, 1, FULL + ' ' + '\uff18' + ' ' + FULL + ' \uff19' + ' ' + FULL)
        # self.mwin.addstr(7, 1, FULL + LOWER * 4 + FULL + LOWER * 4 + FULL)
        #
        # self.mwin.addstr(2, 16, FULL + UPPER * 3 + FULL + UPPER * 3 + FULL)
        # self.mwin.addstr(3, 16, FULL + ' \u2076 ' + FULL + ' \u2077 ' + FULL)
        # self.mwin.addstr(4, 16, FULL + UPPER * 3 + FULL + UPPER * 3 + FULL)
        # self.mwin.addstr(5, 16, FULL + ' \u2078 ' + FULL + ' \u2079 ' + FULL)
        # self.mwin.addstr(6, 16, UPPER + UPPER * 3 + UPPER + UPPER * 3 + UPPER)
        #
        # self.mwin.addstr(10, 1, FULL * 10)
        # self.mwin.addstr(11, 1, FULL * 2 + '\uff16' + FULL * 2 + '\uff17' + FULL * 2)
        # self.mwin.addstr(12, 1, FULL * 10)
        # self.mwin.addstr(13, 1, FULL * 2 + '\uff18' + FULL * 2 + '\uff19' + FULL * 2)
        # self.mwin.addstr(14, 1, FULL * 10)
        #
        # self.mwin.addstr(10, 16, FULL * 18)
        # self.mwin.addstr(11, 16, FULL * 2 + ' ' * 6 + FULL * 2 + ' ' * 6 + FULL * 2)
        # self.mwin.addstr(12, 16, FULL * 2 + '  \uff16  ' + FULL * 2 + '  \uff17  ' + FULL * 2)
        # self.mwin.addstr(13, 16, FULL * 2 + ' ' * 6 + FULL * 2 + ' ' * 6 + FULL * 2)
        # self.mwin.addstr(14, 16, FULL * 18)
        # self.mwin.addstr(15, 16, FULL * 2 + ' ' * 6 + FULL * 2 + ' ' * 6 + FULL * 2)
        # self.mwin.addstr(16, 16, FULL * 2 + '  \uff18  ' + FULL * 2 + '  \uff19  ' + FULL * 2)
        # self.mwin.addstr(17, 16, FULL * 2 + ' ' * 6 + FULL * 2 + ' ' * 6 + FULL * 2)
        # self.mwin.addstr(18, 16, FULL * 18)
        #
        # self.mwin.addstr(16, 1, '\u2554\u2550\u2550\u2550\u2550\u2566\u2550\u2550\u2550\u2550\u2557')
        # self.mwin.addstr(17, 1, '\u2551 \uff16 \u2551 \uff17 \u2551')
        # self.mwin.addstr(18, 1, '\u2560\u2550\u2550\u2550\u2550\u256c\u2550\u2550\u2550\u2550\u2563')
        # self.mwin.addstr(19, 1, '\u2551 \uff18 \u2551 \uff19 \u2551')
        # self.mwin.addstr(20, 1, '\u255a\u2550\u2550\u2550\u2550\u2569\u2550\u2550\u2550\u2550\u255d')
        
        for i,row in enumerate(self.grid.render()):
            self.mwin.addstr(i+3,3,row)
        
        self.mwin.box()
        self.mwin.refresh()
        self.monitor.tick()


def mainloop(win: curses.window):
    win.clear()
    frame_delay = 1000 // config.framerate
    manager = UIManager(win)
    while True:
        manager.tick()
        # curses.flushinp()
        # curses.napms(frame_delay)


def main():
    exit_message = None
    exit_status = 0
    
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(True)
    
    curses.mousemask(curses.REPORT_MOUSE_POSITION |
                     curses.ALL_MOUSE_EVENTS
                     )
    curses.mouseinterval(0)  # don't wait for mouse
    curses.curs_set(0)  # invisible cursor
    print('\033[?1003h',flush=True)  
    # enable mouse tracking with the XTERM API
    # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking
    
    curses.start_color()
    curses.use_default_colors()
    
    try:
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
        print('\033[?1003l',flush=True)  
        stdscr.keypad(False)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        if exit_message:
            print(f'\033[91m{exit_message}\033[0m')
        sys.exit(exit_status)


if __name__ == '__main__':
    main()
