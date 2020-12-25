import curses.panel
import datetime
import signal
import time
import traceback
import sys
from math import ceil, floor
from .board import Board, Cell, GameOver
from .config import config
from .debug import debug_print as _debug_print
from enum import IntFlag
from .box import Box

# ANSI color code for each color
if config.dark_mode:
    FG = 255
    BG = 237
    UI_HIGHLIGHT_FG = FG
    UI_HIGHLIGHT_BG = 242
else:
    FG = 232
    BG = 231
    UI_HIGHLIGHT_FG = FG
    UI_HIGHLIGHT_BG = 250

VALUES = [
    FG, 12, 2, 9, 4, 1, 6, 0, 8
]

DEFAULT = 1
UI_HIGHLIGHT = 2
SYSTEM_DEFAULT = 127

# a simple wrapper around the mouse events for easier bitmask processing
MouseEvent = IntFlag('MouseEvent',
                     [(v, getattr(curses, v)) for v in filter(lambda s: s.startswith('BUTTON'), dir(curses))] +
                     [('DRAG', 1 << (27 if sys.platform == 'darwin' else 28))]
                     )  # trials and errors suggest this is the code for drag


def cell_color(value, highlight):
    """Calculates the color index of the given cell value and highlight state"""
    return (value << 3) + (highlight << 2) + 0b11 
    # at value = 0, highlight = 0 this will start from 3


def debug_print(*args, **kwargs):
    """
    a wrapper around the debug printing function so that frame counter
    is included.
    """
    _debug_print(f'Frame {Widget.root.frame_count}:', *args, **kwargs)


class InsufficientScreenSpace(Exception):
    """
    an exception that will be raised if the window is resized to below
    the minimum required size during runtime
    """


class FPSMonitor:
    """A class to hold the framerate data. It is displayed top left."""

    def __init__(self):
        """
        initializes the fps monitor. the result will not be stable until at
        lease 100 frames are rendered
        """
        cur_time = time.time()
        self.data = [cur_time + i / (config.framerate or 100) / 100 for i in range(100)]

    def tick(self):
        """rotates the saves frame rendering time"""
        self.data.append(time.time())
        self.data.pop(0)

    @property
    def fps(self):
        """calculates the fps, averaging on the past 100 frames"""
        return 1 / ((self.data[-1] - self.data[1]) / 100)

    @property
    def last_frame(self):
        """returns the last time a frame was rendered"""
        return self.data[-1]


class Widget:
    """
    A helper class to organize different areas of the board into widgets,
    so that they can handle and filter key presses or mouse hovering only
    for when the cursor is above themselves.
    """

    # this will be replaced by the instance of RootWidget when it is
    # initialized
    root = None

    def __init__(self, parent, y, x):
        """default widget initializer"""
        self.parent = parent
        self.x = x
        self.y = y
        self.subwidgets = []
        self._animation_frame = 0

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
        try:
            text = str(text)
            if config.show_animation:
                # TODO: change the animation to left to right
                if y <= self.animation_frame:
                    self.parent.addstr(y + self.y, x + self.x, text, *args, **kwargs)
            else:
                self.parent.addstr(y + self.y, x + self.x, text, *args, **kwargs)
        except curses.error:
            if not config.ignore_failures:
                raise InsufficientScreenSpace

    def mouse_event(self, y, x, mouse):
        """
        placeholder function for mouse event handling, override in subclasses
        """

    def keyboard_event(self, key):
        """
        placeholder function for keyboard event handling, override in subclasses
        """

    def dispatch_event(self, etype, *args):
        """
        dispatch the event of given type (mouse or keyboard) to all the child
        widgets recursively, then to self.
        """

        # debug_print(f'Dispatching event {etype} {args}')

        # widgets should receive events before the background
        if etype == 'mouse':
            y, x, mouse = args
            for w in self.subwidgets:
                if y >= w.y and x >= w.x:
                    # coordinate translation
                    w.dispatch_event('mouse', y - w.y, x - w.x, mouse)
            self.mouse_event(*args)
        elif etype == 'keyboard':
            # keyboard event should not be unconditionally passed to
            # children because they won't know who should receive it
            self.keyboard_event(*args)
        else:
            raise ValueError(f"Unknown event type {etype}")

    def render(self):
        """placeholder function for rendering, override in subclasses"""

    @property
    def animation_frame(self):
        """returns the animation frame counter for entering/exiting animation"""
        return self._animation_frame

    @animation_frame.setter
    def animation_frame(self, v):
        """chains the animation frame to subwidgets"""
        self._animation_frame = v
        for w in self.subwidgets:
            w.animation_frame = v


class CellWidget(Widget):
    """
    Each cell is a widget. This widget handles all the important
    events in the game, such as flagging and revealing
    """

    highlighted = set()
    last_clear = 0

    def __init__(self, parent, y, x, cell: Cell):
        """initializes the cell"""
        super().__init__(parent, y, x)
        self.cell = cell

    @classmethod
    def clear_highlight(cls):
        """clears all the highlighted cells"""
        while len(cls.highlighted):
            cls.highlighted.pop().highlight()
        cls.last_clear = cls.root.frame_count

    def area_reveal(self):
        """
        Attempts to reveals the 3x3 area centered at self,
        which will succeed only if the number of flags around
        self is the same as the value of self. clears prevous highlights.
        """
        debug_print(f'{repr(self.cell)}: area reveal')
        self.clear_highlight()
        self.cell.area_reveal(True)

    def area_highlight(self):
        """
        highlights the 3x3 area centered at self, excluding
        any flagged or revealed cell. clears previous highlights.
        """
        debug_print(f'{repr(self.cell)}: area highlight')
        self.clear_highlight()
        for c in self.cell.surroundings:
            c.highlight()
            self.highlighted.add(c)
        self.cell.highlight()
        self.highlighted.add(self.cell)

    def reveal(self):
        """
        reveals self. may raise GameOver exception if self is a mine
        """
        debug_print(f'{repr(self.cell)}: reveal')
        if self.root.game_start:
            self.root.game_start = False
            self.root.game_over = False
            self.root.time_started = datetime.datetime.now()
            self.root.board.init_mines(self.cell)
        self.cell.reveal(True)

    def flag(self):
        """
        flags self and clear highlight on self
        """
        debug_print(f'{repr(self.cell)}: flag')
        if not self.root.game_start and not self.root.game_over:
            self.cell.flag()

    def highlight(self, force = False):
        """
        highlights self and adds self to the set of highlighted cells
        """
        if not self.cell.is_highlighted:
            self.cell.highlight(force)
            self.highlighted.add(self.cell)

    def mouse_event(self, y, x, mouse):
        """
        handles various mouse events
        """

        if (y != 0 or x > 4) or (Widget.root.game_over and not Widget.root.game_start):
            # ignores the event as it is not relevant
            return

        if (MouseEvent.BUTTON2_RELEASED in mouse):
            # handles area reveal
            self.area_reveal()

        if (MouseEvent.BUTTON2_PRESSED in mouse or
                (self.root.button2_pressed and MouseEvent.DRAG in mouse)):
            # handles area highlight
            self.area_highlight()

        if MouseEvent.BUTTON1_RELEASED in mouse:
            # reveal the cell (GameOver exception will be caught in root)
            self.reveal()

        if MouseEvent.BUTTON3_RELEASED in mouse:
            # flag a cell
            self.flag()

        self.highlight()
        self.parent.selected_cell = self.cell.y * self.parent.board.width + self.cell.x

    def keyboard_event(self, key):
        """
        handles keyboard events for the cell
        """
        if key == ' ':
            self.area_reveal()
            self.area_highlight()
        elif key == 'q':
            self.reveal()
        elif key == 'e':
            self.flag()

    def render(self):
        """
        renders the cell
        """

        try:
            v = int(str(self.cell))  # a quick test for non-numbered cell
        except ValueError:  # mine, flag, or blank
            if self.cell.is_highlighted:
                self.addstr(0, 0, f' {self.cell} ', curses.color_pair(UI_HIGHLIGHT))
            else:
                self.addstr(0, 1, self.cell)
        else:
            if self.cell.is_highlighted:
                self.addstr(0, 0, ' ', curses.color_pair(UI_HIGHLIGHT))
                self.addstr(0, 3, ' ', curses.color_pair(UI_HIGHLIGHT))
            attrs = curses.color_pair(cell_color(v, self.cell.is_highlighted))
            attrs |= curses.A_BOLD  # make them bold
            self.addstr(0, 1, self.cell, attrs)

        # clear highlight after the rendering, so if a highlight is added
        # back in the next tick the screen won't flicker


class GridWidget(Widget):
    """
    A helper class to render the grid with Unicode full-width characters
    so that the output is approximately square
    """

    def __init__(self, parent, y, x, board: Board):
        """
        the width and height does not include borders
        :param width: the width, in interpolated pixels
        :param height: the height, in interpolated pixels
        """
        super().__init__(parent, y, x)
        self.board = board
        for cell in board.cells:
            self.subwidgets.append(CellWidget(self, cell.y * 2 + 1, cell.x * 5 + 1, cell))
        self.selected_cell = 0

    def render(self):
        """
        renders the grid. this function is probably the most computationally
        heavy function of the entire program and takes the most amount of
        rendering time due to several double for loops.
        """

        width = self.board.width * 5 + 1
        height = self.board.height * 2 + 1

        # paint the entire board excluding the 4 corners
        for x in range(self.board.width - 1):
            for y in range(self.board.height - 1):
                # the grid is divided into 2x2 clusters so that the character of
                # the center can be calculated, kinda like the convolution in
                # a CNN

                tl = not self.board[y, x].is_revealed  # top left
                tr = not self.board[y, x + 1].is_revealed  # top right
                bl = not self.board[y + 1, x].is_revealed  # bottom left
                br = not self.board[y + 1, x + 1].is_revealed  # bottom right

                # special case for first column
                if not x:
                    self.addstr(y * 2 + 1, 0, Box.up(tl).down(tl))
                    self.addstr(y * 2 + 3, 0, Box.up(bl).down(bl))
                    self.addstr(y * 2 + 2, 0, Box.up(tl).down(bl).right(tl or bl))

                # special case for last column
                if x == self.board.width - 2:
                    self.addstr(y * 2 + 1, x * 5 + 10, Box.up(tr).down(tr))
                    self.addstr(y * 2 + 3, x * 5 + 10, Box.up(br).down(br))
                    self.addstr(y * 2 + 2, x * 5 + 10, Box.up(tr).down(br).left(tr or br))

                # special case for first row
                if not y:
                    self.addstr(y * 2, x * 5 + 1, Box.left(tl).right(tl) * 4)
                    self.addstr(y * 2, x * 5 + 6, Box.left(tr).right(tr) * 4)
                    self.addstr(y * 2, x * 5 + 5, Box.left(tl).right(tr).down(tl or tr))

                # special case for last row
                if y == self.board.height - 2:
                    self.addstr(y * 2 + 4, x * 5 + 1, Box.left(bl).right(bl) * 4)
                    self.addstr(y * 2 + 4, x * 5 + 6, Box.left(br).right(br) * 4)
                    self.addstr(y * 2 + 4, x * 5 + 5, Box.left(bl).right(br).up(bl or br))

                # horizontal lines
                self.addstr(y * 2 + 2, x * 5 + 1, Box.left(tl or bl).right(tl or bl) * 4)
                self.addstr(y * 2 + 2, x * 5 + 6, Box.left(tr or br).right(tr or br) * 4)

                # vertical lines
                self.addstr(y * 2 + 1, x * 5 + 5, Box.up(tl or tr).down(tl or tr))
                self.addstr(y * 2 + 3, x * 5 + 5, Box.up(bl or br).down(bl or br))

                # the center of the cluster
                self.addstr(y * 2 + 2, x * 5 + 5, Box(tl or tr, bl or br, tl or bl, tr or br))

        tl = not self.board[0][0].is_revealed  # top left
        tr = not self.board[0][-1].is_revealed  # top right
        bl = not self.board[-1][0].is_revealed  # bottom left
        br = not self.board[-1][-1].is_revealed  # bottom right

        # add the corners of the board
        self.addstr(0, 0, Box.right(tl).down(tl))
        self.addstr(0, width - 1, Box.left(tr).down(tr))
        self.addstr(height - 1, 0, Box.up(bl).right(bl))
        self.addstr(height - 1, width - 1, Box.up(br).left(br))

        if self.root.keyboard_mode:
            self.subwidgets[self.selected_cell].highlight(True)

        for w in self.subwidgets:
            w.render()

        # clears highlight every 50ms in case the cursor leaves the screen
        if not self.root.button2_pressed and self.root.frame_count > CellWidget.last_clear + self.root.monitor.fps / 20:
            CellWidget.clear_highlight()
            if not self.root.game_over:
                # restore the face because we don't know
                # if it was triggered by keyboard
                self.root.status.status = '🙂'

    def keyboard_event(self, key):
        """
        handles keyboard event for the grid, also controls
        whether the program is in keyboard-only mode
        """
        cell_count = len(self.subwidgets)
        if key in ('up', 'w'):
            self.selected_cell -= self.board.width
        elif key in ('down', 's'):
            self.selected_cell += self.board.width
        elif key in ('left', 'a'):
            self.selected_cell -= 1
        elif key in ('right', 'd'):
            self.selected_cell += 1
        else:
            self.subwidgets[self.selected_cell].keyboard_event(key)
            return

        self.root.keyboard_mode = True
        self.selected_cell %= cell_count  # prevent index error


class StatusWidget(Widget):
    """
    This widget is the smiley face to the right
    of the window. Will display a dead face on
    game end and a surprised face on area
    highlight. Clicking on the face will restart
    the game just like on Windows XP
    """

    def __init__(self, parent, y, x):
        """initializes the status"""
        super().__init__(parent, y, x)
        self.status = '🙂'

    def mouse_event(self, y, x, mouse):
        """handles left click on the face (restart)"""
        if (MouseEvent.BUTTON1_PRESSED in mouse
                and y == 0 and x <= 2
                and config.use_emojis):
            self.root.restart()

    def render(self):
        """adds the emoji"""
        if config.use_emojis:
            self.addstr(0, 0, self.status)


class RootWidget(Widget):
    def __init__(self, win: curses.window):
        """
        initializes the root widget
        """

        # the window is the root widget's parent
        super().__init__(win, 0, 0)
        self.window = win
        self.board = Board()
        self.mouse_y = 0
        self.mouse_x = 0
        self.monitor = FPSMonitor()

        # initializes the grid (where all the mines are)
        self.grid = GridWidget(self, 6, 5, self.board)
        self.subwidgets.append(self.grid)

        # initializes the status widget (the right sidebar)
        self.status_x_offset = 5 + self.board.width * 5 + 4
        self.status_y_offset = 4
        self.status = StatusWidget(self, self.status_y_offset + 1, self.status_x_offset + 14)
        self.subwidgets.append(self.status)

        # some useful variables
        self.should_exit = False
        self.game_start = True
        self.game_over = True
        self.time_taken = '00:00.00'
        self.time_started = datetime.datetime.now()

        self.frame_count = 0

        self.button1_pressed = False
        self.button2_pressed = False
        self.button3_pressed = False

        self.keyboard_mode = True

        Widget.root = self

    def exit(self):
        """
        flagged to exit on the next iteration of the mainloop
        """
        self.should_exit = True

    def restart(self):
        """
        restarts the game
        """
        self.game_start = True
        self.board.reset()
        self.game_over = True
        self.time_taken = '00:00.00'
        self.status.status = '🙂'

    def paint_window(self):
        """
        draw the initial window. always identical to the one
        produced by calc_first_frame()
        """
        winh, winw = self.window.getmaxyx()
        self.window.addstr(0, 1, '╭' + '─' * (winw - 4) + '╮')
        self.window.addch(1, 1, '│')
        self.window.addch(1, winw - 2, '│')
        self.window.addstr(1, (winw - 24) // 2 + 2, 'TERMINAL MINESWEEPER')
        self.window.addstr(2, 1, '├' + '─' * (winw - 4) + '┤')
        for y in range(3, winh - 1):
            self.window.addch(y, 1, '│')
            self.window.addch(y, winw - 2, '│')
        self.window.addstr(winh - 1, 1, '╰' + '─' * (winw - 4) + '╯')

    def tick(self):
        """
        this function is called for each iteration of the mainloop,
        it is responsible for processing and dispatching keyboard
        events and scheduling each widget to render
        """
        ch = self.window.getch()

        # handles mouse input
        if ch == curses.KEY_MOUSE:
            try:
                _, mouse_x, mouse_y, z, mouse_button = curses.getmouse()
                mouse = MouseEvent(mouse_button)

                # curses can't recognized any tracking (1003) mode, so it
                # just spams the previous events (button x released) when
                # it's just hover, so a lock for each button is necessary

                # additionally, it might be the case that the user presses
                # a button and then hover outside of the screen, which
                # can results in some strange mouse events unless a lock
                # is in place

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

                if mouse_x != self.mouse_x or mouse_y != self.mouse_y or mouse:
                    self.keyboard_mode = False
                self.mouse_y, self.mouse_x = mouse_y, mouse_x
            except curses.error:
                mouse = MouseEvent(0)
            etype = 'mouse'
            args = (self.mouse_y, self.mouse_x, mouse)
        else:
            # keyboard input
            if ch == -1 or self.button2_pressed:
                # block middle button paste on linux
                char = '\0'
            else:
                char = {curses.KEY_UP   : 'up',
                        curses.KEY_DOWN : 'down',
                        curses.KEY_LEFT : 'left',
                        curses.KEY_RIGHT: 'right', }.get(ch, chr(ch).lower())
            etype = 'keyboard'
            args = (char,)

        try:
            if etype == 'keyboard' and char != '\0':
                self.dispatch_event('keyboard', *args)
            elif etype == 'mouse':
                self.dispatch_event('mouse', *args)
            elif not self.keyboard_mode:
                # hover
                self.dispatch_event('mouse', self.mouse_y, self.mouse_x, MouseEvent(0))

        except GameOver as exc:
            self.game_over = True
            self.status.status = '😵'
            exc.args[0].explode()
            self.board.reveal_all()

        # caps the framerate by postponing rendering
        # while still processing events as fast as possible
        if config.framerate:
            elapsed = time.time() - self.monitor.last_frame
            if elapsed * config.framerate >= 1:
                self.render()
        else:
            self.render()

    def render(self):
        """renders the entire window{"""

        self.frame_count += 1
        self.monitor.tick()
        # so that fps will also count the rendering time

        self.window.erase()
        try:
            self.window.addch(self.mouse_y, self.mouse_x, curses.ACS_DIAMOND)
        except curses.error:
            pass  # sometimes mouse fly around and that's ok
        self.addstr(4, 5, f'FPS: {round(self.monitor.fps, 2):0<5}')

        # adding legends
        if not self.game_over:
            time_taken = datetime.datetime.now() - self.time_started
            minute, second = divmod(time_taken.seconds, 60)
            msec = str(time_taken.microseconds).zfill(2)[:2]
            self.time_taken = f'{minute:0>2}:{second:0>2}.{msec}'

        self.addstr(self.status_y_offset, self.status_x_offset + 11, self.time_taken)

        self.addstr(self.status_y_offset + 3, self.status_x_offset, '          Navigation')
        self.addstr(self.status_y_offset + 4, self.status_x_offset, '   [W]        [↑]      Move ')
        self.addstr(self.status_y_offset + 5, self.status_x_offset, '[A][S][D]  [←][↓][→]  cursor')

        self.addstr(self.status_y_offset + 7, self.status_x_offset, '          Operation')
        self.addstr(self.status_y_offset + 8, self.status_x_offset, 'Reveal cell       [LMB]/[Q] ')
        self.addstr(self.status_y_offset + 9, self.status_x_offset, 'Reveal area       [MMB]/[Space]')
        self.addstr(self.status_y_offset + 10, self.status_x_offset, 'Flag cell         [RMB]/[E] ')
        self.addstr(self.status_y_offset + 11, self.status_x_offset, 'Restart           [Enter]')
        self.addstr(self.status_y_offset + 12, self.status_x_offset, 'Toggle emojis     [T] ')

        emo = config.use_emojis
        self.addstr(self.status_y_offset + 14, self.status_x_offset + 11, 'Symbols')
        self.addstr(self.status_y_offset + 15, self.status_x_offset + 6, ('💥' if emo else '＊') + ' Exploded mine')
        self.addstr(self.status_y_offset + 16, self.status_x_offset + 6, ('🏁' if emo else 'Ｘ') + ' Flagged mine')
        self.addstr(self.status_y_offset + 17, self.status_x_offset + 6, ('💣' if emo else 'Ｏ') + ' Unflagged mine')
        self.addstr(self.status_y_offset + 18, self.status_x_offset + 6, ('🚩' if emo else 'Ｆ') + ' Flag')

        # flag counts
        flags = config.mine_count - self.board.flag_count()
        if config.use_emojis:
            if flags <= 10:
                self.addstr(self.status_y_offset + 20,
                            self.status_x_offset + 14 - flags,
                            '🚩' * (config.mine_count - self.board.flag_count()))
            else:
                self.addstr(self.status_y_offset + 20,
                            self.status_x_offset + 10,
                            f'🚩 × {flags}')
        else:
            self.addstr(self.status_y_offset + 20,
                        self.status_x_offset + 10,
                        f'Ｆ × {flags}')

        # check winning condition
        if not self.game_over and self.board.check_win():
            self.status.status = '😎'
            self.game_over = True
            self.board.reveal_all()

        self.grid.render()
        self.status.render()

        # overwrite all other widgets
        self.paint_window()

        # overwrite the close button onto the window
        self.addstr(0, 6, '┬')
        self.addstr(1, 6, '│')
        self.addstr(2, 6, '┴')
        if self.mouse_y == 1 and 2 <= self.mouse_x <= 5:
            self.addstr(1, 2, ' Ｘ ', curses.color_pair(UI_HIGHLIGHT))
        else:
            self.addstr(1, 3, 'Ｘ')

        # debug_print('Window render')
        self.window.refresh()

    def mouse_event(self, y, x, mouse):
        """handles mouse events for root"""

        # handling close button
        if y == 1 and 2 <= x <= 5:
            if MouseEvent.BUTTON1_PRESSED in mouse:
                self.exit()

        # do the surprised face
        if not self.game_over:
            if MouseEvent.BUTTON2_PRESSED in mouse:
                self.status.status = '😲'

    def keyboard_event(self, key):
        """
        handle keyboard events for root
        """

        if key == 't':  # toggle emojis
            config.use_emojis = bool(1 - config.use_emojis)
        elif key == '\n':
            self.restart()
        elif key == ' ':
            if not self.game_over:
                self.status.status = '😲'

        for w in self.subwidgets:
            w.dispatch_event('keyboard', key)


def mainloop(win: curses.window):
    """the mainloop of the program. blocks until exit"""
    win.clear()
    root = RootWidget(win)

    signint_handler = lambda signum, frame: root.exit()
    signal.signal(signal.SIGINT, signint_handler)
    # so it only shuts down after a full frame is rendered
    while True:
        winh, winw = win.getmaxyx()
        in_animation = root.animation_frame < winh
        root.animation_frame += in_animation
        root.tick()
        if config.show_animation and in_animation:
            curses.flushinp()
            curses.napms(20)
        if root.should_exit:
            if config.show_animation:
                while root.animation_frame > 0:
                    # manager.animation_direction='reversed'
                    root.animation_frame -= 1
                    root.tick()
                    curses.napms(20)
            return


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
        curses.flushinp()
    except curses.error:
        return 'Cannot initialize curses window', 1

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
        stdscr.bkgd(' ', curses.color_pair(DEFAULT))

        # initialization complete
        mainloop(stdscr)
    except InsufficientScreenSpace:
        exit_message = 'Insufficient screen space'
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
