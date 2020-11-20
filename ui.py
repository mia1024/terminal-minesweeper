import curses.panel
import datetime
import signal
import time
import traceback
from math import ceil, floor
from board import Board, Cell, GameOver
from config import config
from utils import debug_print
from enum import IntFlag

FG = 232
BG = 231
VALUES = [
    FG, 12, 2, 9, 4, 1, 6, 0, 8
]
UI_HIGHLIGHT_FG = 232
UI_HIGHLIGHT_BG = 255

DEFAULT = 1
UI_HIGHLIGHT = 2
SYSTEM_DEFAULT = 127

tmp = {}
for var in dir(curses):
    if var.startswith('BUTTON'):
        tmp[var] = getattr(curses, var)

# a simple wrapper around the mouse events for easier processing
MouseEvent = IntFlag('MouseEvent',
                     [(v, getattr(curses, v)) for v in filter(lambda s: s.startswith('BUTTON'), dir(curses))] +
                     [['DRAG', 1 << 28]])  # trials and errors suggest this is the code


def cell_color(value, highlight):
    return (value << 3) + (highlight << 2)


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


class Widget:
    root = None

    def __init__(self, parent, y, x):
        self.parent = parent
        self.x = x
        self.y = y
        self.animation_frame = 0
        self.subwidgets = []

    def addstr(self, y: int, x: int, text, *args, **kwargs):
        """
        A patched version of curses.window.addstr to support animations
        :param y: the y coordinate
        :param x: the x coordinate
        :param text: the text to add
        :param args: extra arguments passing to curses.window.addstr
        :param kwargs: extra keywords passing to curses.window.addstr
        :return: None
        """

        text = str(text)
        if config.show_animation:
            # TODO: change the animation to left to right
            if y <= self.animation_frame:
                self.parent.addstr(y + self.y, x + self.x, text, *args, **kwargs)
        else:
            self.parent.addstr(y + self.y, x + self.x, text, *args, **kwargs)

    def key_event(self, y, x, keyboard, mouse):
        pass

    def dispatch_event(self, y, x, keyboard, mouse):
        # widgets should receive events before the background
        # if not isinstance(self, RootWidget):
        #     debug_print(self.__class__, 'received event', (y, x), key)
        for w in self.subwidgets:
            if y >= w.y and x >= w.x:
                w.dispatch_event(y - w.y, x - w.x, keyboard, mouse)
        self.key_event(y, x, keyboard, mouse)

    def render(self):
        pass


class CellWidget(Widget):
    highlighted = []
    last_clear = 0

    def __init__(self, parent, y, x, cell: Cell):
        super().__init__(parent, y, x)
        self.cell = cell

    @classmethod
    def clear_highlight(cls):
        while len(cls.highlighted):
            cls.highlighted.pop().highlight()
        cls.last_clear = cls.root.frame_count

    def key_event(self, y, x, keyboard, mouse):
        if (y != 0 or x > 4) or (Widget.root.game_over and not Widget.root.game_start):
            # debug_print(f"Event in {repr(self.cell)} ignored")
            return

        keyboard = keyboard.lower()
        if keyboard != '\0' or mouse:
            debug_print(f'{repr(self.cell)}: {(self.y, self.x)} {keyboard} {mouse}')

        if (MouseEvent.BUTTON2_PRESSED in mouse or
                (self.root.button2_pressed and MouseEvent.DRAG in mouse)):
            debug_print(f'{repr(self.cell)} area highlight')
            self.clear_highlight()
            for c in self.cell.surroundings:
                c.highlight()
                self.highlighted.append(c)
        elif (MouseEvent.BUTTON2_RELEASED in mouse) or keyboard == ' ':
            debug_print(f'{repr(self.cell)} area reveal')
            self.clear_highlight()
            self.cell.area_reveal(True)
        elif MouseEvent.BUTTON1_RELEASED in mouse or keyboard == 'r':
            debug_print(f'{repr(self.cell)} reveal')
            if self.root.game_start:
                self.root.game_start = False
                self.root.game_over = False
                self.root.time_started = datetime.datetime.now()
                self.root.board.init_mines(self.cell)

            self.cell.reveal(True)

        elif MouseEvent.BUTTON3_RELEASED in mouse or keyboard == 'f':
            debug_print(f'{repr(self.cell)}: {(self.y, self.x)} flag')
            if not self.root.game_start and not self.root.game_over:
                self.cell.flag()
        else:
            if self.cell not in self.highlighted:
                self.cell.highlight()
                self.highlighted.append(self.cell)

    def render(self):
        try:
            v = int(str(self.cell))
        except ValueError:
            if self.cell.is_highlighted():
                self.addstr(0, 0, f' {self.cell} ', curses.color_pair(UI_HIGHLIGHT))
            else:
                self.addstr(0, 1, self.cell)
        else:
            if self.cell.is_highlighted():
                self.addstr(0, 0, ' ', curses.color_pair(UI_HIGHLIGHT))
                self.addstr(0, 3, ' ', curses.color_pair(UI_HIGHLIGHT))
            attrs = curses.color_pair(cell_color(self.cell.value, self.cell.is_highlighted()))
            if v != 0:
                attrs |= curses.A_BOLD
            self.addstr(0, 1, self.cell, attrs)

        # clear highlight after the rendering, so if a highlight is added
        # back in the next tick the screen won't flicker
        if not self.root.button2_pressed and self.root.frame_count > self.last_clear + self.root.monitor.fps / 20:
            self.clear_highlight()


class GridWidget(Widget):
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

    def __init__(self, parent, y, x, board: Board):
        """
        the width and height does not include borders
        :param width: the width, in interpolated pixels
        :param height: the height, in interpolated pixels
        """
        super().__init__(parent, y, x)
        self.width = board.width
        self.height = board.height
        self.board = board
        for cell in board.cells:
            self.subwidgets.append(CellWidget(self, cell.y * 2 + 1, cell.x * 5 + 1, cell))

    def get_cell(self, y, x):
        """return a matched cell, or None, based on the coordinate passed in"""
        debug_print(f'Grid received coord {(y, x)}')
        if y % 2 == 0 or x % 5 == 0:
            return None
        y //= 2
        x //= 5
        try:
            cell = self.board[y, x]
            debug_print('Grid returning ', repr(cell))
            return cell
        except KeyError:
            raise

    def render(self):
        width = self.width * 5 + 1
        self.addstr(0, 0, self.TOPLEFT)
        self.addstr(0, 1, (self.HBAR * 4 + self.TOP) * (self.width - 1))
        self.addstr(0, width - 5, self.HBAR * 4 + self.TOPRIGHT)

        for w in self.subwidgets:
            w.render()


class StatusWidget(Widget):
    def __init__(self, parent, y, x):
        super().__init__(parent, y, x)
        self.status = '🙂' if config.use_emojis else ''

    def key_event(self, y, x, keyboard, mouse):
        if MouseEvent.BUTTON1_PRESSED in mouse and y == 0 and x <= 2:
            self.root.restart()

    def render(self):
        self.addstr(0, 0, self.status)


class RootWidget(Widget):
    def __init__(self, win: curses.window):
        super().__init__(win, 0, 0)
        self.win = win
        self.board = Board()
        self.mouse_y = 0
        self.mouse_x = 0
        self.monitor = FPSMonitor()

        self.grid = GridWidget(self, 6, 5, self.board)
        self.subwidgets.append(self.grid)

        self.status_x_offset = self.grid.x + self.board.width * 5 + 4
        self.status_y_offset = self.grid.y + 1
        self.status = StatusWidget(self, self.status_y_offset + 1, self.status_x_offset + 12)
        self.subwidgets.append(self.status)

        self.should_exit = False
        self.game_start = True
        self.game_over = True
        self.time_taken = '00:00.000'
        self.time_started = datetime.datetime.now()

        self.frame_count = 0

        self.button1_pressed = False
        self.button2_pressed = False
        self.button3_pressed = False

        Widget.root = self

    def exit(self):
        self.should_exit = True

    def restart(self):
        self.game_start = True
        self.board.reset()
        self.game_over = True
        self.time_taken = '00:00.000'
        self.status.status = '🙂' if config.use_emojis else ''

    def paint_window(self):
        """
        draw the initial window. always identical to the one
        produced by calc_first_frame()
        """

        winh, winw = self.win.getmaxyx()
        self.win.addstr(0, 1, '╭' + '─' * (winw - 4) + '╮')
        self.win.addch(1, 1, '│')
        self.win.addch(1, winw - 2, '│')
        self.win.addstr(1, (winw - 24) // 2 + 2, 'TERMINAL MINESWEEPER')
        self.win.addstr(2, 1, '├' + '─' * (winw - 4) + '┤')
        for y in range(3, winh - 1):
            self.win.addch(y, 1, '│')
            self.win.addch(y, winw - 2, '│')
        self.win.addstr(winh - 1, 1, '╰' + '─' * (winw - 4) + '╯')

    def render(self):
        self.frame_count += 1

        ch = self.win.getch()
        self.win.erase()
        self.paint_window()

        # overwrite the close button onto the window
        self.addstr(1, 3, 'Ｘ')
        self.addstr(0, 6, '┬')
        self.addstr(1, 6, '│')
        self.addstr(2, 6, '┴')

        if ch == curses.KEY_MOUSE:
            keyboard = '\0'
            try:
                _, self.mouse_x, self.mouse_y, z, mouse_button = curses.getmouse()
                mouse = MouseEvent(mouse_button)
                if MouseEvent.BUTTON1_PRESSED in mouse:
                    if self.button1_pressed:
                        mouse &= ~MouseEvent.BUTTON1_PRESSED
                    else:
                        self.button1_pressed = True
                if MouseEvent.BUTTON2_PRESSED in mouse:
                    if self.button2_pressed:
                        mouse &= ~MouseEvent.BUTTON2_PRESSED
                    else:
                        self.button2_pressed = True
                if MouseEvent.BUTTON3_PRESSED in mouse:
                    if self.button3_pressed:
                        mouse &= ~MouseEvent.BUTTON3_PRESSED
                    else:
                        self.button3_pressed = True

                # curses can't recognized any tracking (1003) mode, so it
                # just spams the previous events (button x released) when
                # it's just hover, so a lock for each button is necessary

                if MouseEvent.BUTTON1_RELEASED in mouse:
                    if not self.button1_pressed:
                        mouse &= ~MouseEvent.BUTTON1_RELEASED
                    else:
                        self.button1_pressed = False

                if MouseEvent.BUTTON2_RELEASED in mouse:
                    if not self.button2_pressed:
                        mouse &= ~MouseEvent.BUTTON2_RELEASED
                    else:
                        self.button2_pressed = False

                if MouseEvent.BUTTON3_RELEASED in mouse:
                    if not self.button3_pressed:
                        mouse &= ~MouseEvent.BUTTON3_RELEASED
                    else:
                        self.button3_pressed = False
            except curses.error:
                mouse = MouseEvent(0)
        else:
            mouse = MouseEvent(0)
            if ch == -1 or self.button2_pressed:
                # block middle button pasting on linux
                keyboard = '\0'
            else:
                keyboard = chr(ch)
        try:
            self.dispatch_event(self.mouse_y, self.mouse_x, keyboard, mouse)
        except GameOver as exc:
            self.game_over = True
            self.status.status = '😵' if config.use_emojis else 'You lost'
            exc.args[0].explode()
            self.board.reveal_all()

        self.addstr(4, 5, f'FPS: {round(self.monitor.fps, 2):0<5}')

        # adding legends
        if not self.game_over:
            time_taken = datetime.datetime.now() - self.time_started
            minute, second = divmod(time_taken.seconds, 60)
            msec = str(time_taken.microseconds).zfill(3)[:3]
            self.time_taken = f'{minute:0>2}:{second:0>2}.{msec}'

        self.addstr(self.status_y_offset, self.status_x_offset + 9, self.time_taken)
        self.addstr(self.status_y_offset + 4, self.status_x_offset, '        Operations:')
        self.addstr(self.status_y_offset + 5, self.status_x_offset, 'Reveal cell    [LMB]/[R] ')
        self.addstr(self.status_y_offset + 7, self.status_x_offset, 'Reveal area    [MMB]/[Space]')
        self.addstr(self.status_y_offset + 6, self.status_x_offset, 'Flag cell      [RMB]/[F] ')
        self.addstr(self.status_y_offset + 7, self.status_x_offset, 'Restart        [Enter]')
        self.addstr(self.status_y_offset + 8, self.status_x_offset, 'Toggle emojis  [T] ')

        emo = config.use_emojis
        self.addstr(self.status_y_offset + 11, self.status_x_offset + 10, 'Symbols')
        self.addstr(self.status_y_offset + 12, self.status_x_offset + 5, ('💥' if emo else '＊:') + ' Exploded mine')
        self.addstr(self.status_y_offset + 13, self.status_x_offset + 5, ('⛳' if emo else 'Ｘ:') + ' Correct flag')
        self.addstr(self.status_y_offset + 14, self.status_x_offset + 5, ('💣' if emo else 'Ｏ:') + ' Remaining mine')
        self.addstr(self.status_y_offset + 15, self.status_x_offset + 5, ('🚩' if emo else 'Ｆ:') + ' Incorrect flag')

        if not self.game_over and self.board.check_win():
            self.status.status = '😎' if config.use_emojis else 'You won'
            self.game_over = True
            self.board.reveal_all()

        self.grid.render()
        self.status.render()
        self.win.refresh()
        self.monitor.tick()

    def key_event(self, y, x, keyboard, mouse):
        try:
            self.win.addch(self.mouse_y, self.mouse_x, curses.ACS_DIAMOND)
        except curses.error:
            pass  # sometimes mouse fly around and that's ok

        if keyboard == 't':  # toggle emojis
            config.use_emojis = bool(1 - config.use_emojis)
        elif keyboard == '\n':
            self.restart()

        # handling close button
        if self.mouse_y == 1 and 2 <= self.mouse_x <= 5:
            if MouseEvent.BUTTON1_PRESSED in mouse:
                self.exit()
            else:
                self.addstr(1, 2, ' Ｘ ', curses.color_pair(2))


def mainloop(win: curses.window):
    win.clear()
    frame_delay = round(1000 / config.framerate)
    root = RootWidget(win)

    signint_handler = lambda signum, frame: root.exit()
    signal.signal(signal.SIGINT, signint_handler)
    # so it only shuts down after a full frame is rendered
    while True:
        winh, winw = win.getmaxyx()
        in_animation = root.animation_frame < winh
        root.animation_frame += in_animation
        root.render()
        if config.show_animation and in_animation:
            curses.napms(20)
        if root.should_exit:
            if config.show_animation:
                while root.animation_frame > 0:
                    # manager.animation_direction='reversed'
                    root.animation_frame -= 1
                    root.render()
                    curses.napms(20)
            return
        # curses.flushinp()
        # last_frame_time = round((manager.monitor.data[-1] - manager.monitor.data[-2]) * 1000)
        # curses.napms(frame_delay - (last_frame_time - frame_delay))


def calc_first_frame(height, width):
    """
    calculate the first frame to print for the startup animation
    :param height: height of the screen
    :param width: width of the screen
    :return: a list of strings, each representing a line
    """

    def pad(line, center = False):
        """a simple """
        if not center:
            return ' │' + line + ' ' * (width - len(line) - 4) + '│ '
        return ' │' + ' ' * floor((width - len(line) - 4) / 2) + line + ' ' * ceil(
            (width - len(line) - 4) / 2) + '│ '

    frame = []
    line = ' ╭' + '─' * (width - 4) + '╮ '
    frame.append(line)
    frame.append(pad('TERMINAL MINESWEEPER', center = True))
    line = ' ├' + '─' * (width - 4) + '┤ '
    frame.append(line)
    for y in range(height - 4):
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
        print('\033[?1003h', flush = True)
        # enable mouse tracking with the XTERM API
        # https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Mouse-Tracking

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(DEFAULT, FG, BG)
        curses.init_pair(UI_HIGHLIGHT, UI_HIGHLIGHT_FG, UI_HIGHLIGHT_BG)
        curses.init_pair(SYSTEM_DEFAULT, -1, -1)
        for i in range(8):
            curses.init_pair(cell_color(i, True), VALUES[i], UI_HIGHLIGHT_BG)
            curses.init_pair(cell_color(i, False), VALUES[i], BG)
        stdscr.bkgd(' ', curses.color_pair(1))

        # initialization complete
        mainloop(stdscr)
    except UIError as err:
        exit_message = err.args[0]
        exit_status = 1
    except:
        exit_message = traceback.format_exc()
        exit_status = 1
    finally:
        # revert the terminal state
        print('\033[?1003l', flush = True)
        curses.flushinp()
        curses.qiflush()
        stdscr.keypad(False)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        return exit_message, exit_status
