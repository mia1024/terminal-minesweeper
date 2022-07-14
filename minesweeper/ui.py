import curses.panel
import datetime
import signal
import time
import traceback
import sys
from math import ceil, floor, log10
from .board import Board, Cell, GameOver
from .config import config
from .debug import debug_print as _debug_print
from enum import IntFlag
from textwrap import dedent
from .box import box

# ANSI color code for each color
if config.dark_mode:
    FG = 231
    BG = 234
    UI_HIGHLIGHT_FG = FG
    UI_HIGHLIGHT_BG = 242
    UI_ALT_HIGHLIGHT_BG = 203
else:
    FG = 232
    BG = 231
    UI_HIGHLIGHT_FG = FG
    UI_HIGHLIGHT_BG = 250
    UI_ALT_HIGHLIGHT_BG = 203

# ANSI color code for each mine value
if config.dark_mode:
    VALUES = [238, 33, 46, 196, 213, 228, 195, 165, 253]
else:
    VALUES = [253, 21, 41, 160, 165, 208, 69, 92, 239]

UI_COLORS_USED = [FG, BG, UI_HIGHLIGHT_FG, UI_HIGHLIGHT_BG, UI_ALT_HIGHLIGHT_BG]
UI_COLORS_USED.extend(VALUES)
UI_COLORS_USED = sorted(list(set(UI_COLORS_USED)))  # remove duplicate and sort

DEFAULT = 1
UI_HIGHLIGHT = 2
UI_ALT_HIGHLIGHT = 3
SYSTEM_DEFAULT = 127

# a simple wrapper around the mouse events for easier bitmask processing
MouseEvent = IntFlag('MouseEvent',
                     [(v, getattr(curses, v)) for v in filter(lambda s: s.startswith('BUTTON'), dir(curses))] +
                     [('DRAG', 1 << (27 if sys.platform == 'darwin' else 28))]
                     )  # trials and errors suggest this is the code for drag


def pad_window(line, width, center = False):
    """Pad the side of a window to a width"""
    if not center:
        return ' │' + line + ' ' * (width - len(line) - 4) + '│ '
    return ' │' + ' ' * floor((width - len(line) - 4) / 2) + line + ' ' * ceil(
        (width - len(line) - 4) / 2) + '│ '


def cell_color(value, highlight):
    """Calculates the color index of the given cell value and highlight state"""
    return (value << 4) | (highlight << 3) | 0b111
    # at value = 0, highlight = 0 this will start from 7


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
        self.data = [cur_time - (100 - i) / (config.framerate or 60) for i in range(100)]

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

    def anchor(self, y: int, x: int):
        """Set the x and y of the widget"""
        self.y = y
        self.x = x

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
        self.h = 1
        self.w = 4

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

        if (y != 0 or x > 4) or (Widget.root.game_over and not Widget.root.game_start) or Widget.root.help.is_active:
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
        elif key == 'r':
            self.reveal()
        elif key == 'f':
            self.flag()

    def render(self):
        """
        renders the cell
        """

        try:
            v = int(str(self.cell))  # a quick test for non-numbered cell
        except ValueError:  # mine, flag, or blank
            if self.cell.is_highlighted:
                self.addstr(0, 0, f' {self.cell} ',
                            curses.color_pair(UI_ALT_HIGHLIGHT if self.cell.is_flagged else UI_HIGHLIGHT))
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
        self.h = self.board.height * 2 + 1
        self.w = self.board.width * 5 + 1

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
                    self.addstr(y * 2 + 1, 0, box(up=tl,down=tl))
                    self.addstr(y * 2 + 3, 0, box(up=bl,down=bl))
                    self.addstr(y * 2 + 2, 0, box(up=tl,down=bl,right=tl or bl))

                # special case for last column
                if x == self.board.width - 2:
                    self.addstr(y * 2 + 1, x * 5 + 10, box(up=tr,down=tr))
                    self.addstr(y * 2 + 3, x * 5 + 10, box(up=br,down=br))
                    self.addstr(y * 2 + 2, x * 5 + 10, box(up=tr,down=br,left=tr or br))

                # special case for first row
                if not y:
                    self.addstr(y * 2, x * 5 + 1, box(left=tl,right=tl) * 4)
                    self.addstr(y * 2, x * 5 + 6, box(left=tr,right=tr) * 4)
                    self.addstr(y * 2, x * 5 + 5, box(left=tl,right=tr,down=tl or tr))

                # special case for last row
                if y == self.board.height - 2:
                    self.addstr(y * 2 + 4, x * 5 + 1, box(left=bl,right=bl) * 4)
                    self.addstr(y * 2 + 4, x * 5 + 6, box(left=br,right=br) * 4)
                    self.addstr(y * 2 + 4, x * 5 + 5, box(left=bl,right=br,up=bl or br))

                # horizontal lines
                self.addstr(y * 2 + 2, x * 5 + 1, box(left=tl or bl,right=tl or bl) * 4)
                self.addstr(y * 2 + 2, x * 5 + 6, box(left=tr or br,right=tr or br) * 4)

                # vertical lines
                self.addstr(y * 2 + 1, x * 5 + 5, box(up=tl or tr,down=tl or tr))
                self.addstr(y * 2 + 3, x * 5 + 5, box(up=bl or br,down=bl or br))

                # the center of the cluster
                self.addstr(y * 2 + 2, x * 5 + 5, box(tl or tr, bl or br, tl or bl, tr or br))

        tl = not self.board[0][0].is_revealed  # top left
        tr = not self.board[0][-1].is_revealed  # top right
        bl = not self.board[-1][0].is_revealed  # bottom left
        br = not self.board[-1][-1].is_revealed  # bottom right

        # add the corners of the board
        self.addstr(0, 0, box(right=tl,down=tl))
        self.addstr(0, width - 1, box(left=tr,down=tr))
        self.addstr(height - 1, 0, box(up=bl,right=bl))
        self.addstr(height - 1, width - 1, box(up=br,left=br))

        if self.root.keyboard_mode:
            self.subwidgets[self.selected_cell].highlight(True)

        for w in self.subwidgets:
            w.render()

        # clears highlight every 50ms in case the cursor leaves the screen
        if not self.root.button2_pressed and self.root.frame_count > CellWidget.last_clear + self.root.monitor.fps / 20:
            CellWidget.clear_highlight()

        if not (self.root.button2_pressed or self.root.button1_pressed or self.root.game_over):
            # restore the face because we don't know
            # if it was triggered by keyboard
            self.root.status.status = '🙂'

    def keyboard_event(self, key):
        """
        handles keyboard event for the grid, also controls
        whether the program is in keyboard-only mode
        """
        cell_count = len(self.subwidgets)
        if key in ('up', 'w', 'j'):
            self.selected_cell -= self.board.width
        elif key in ('down', 's', 'k'):
            self.selected_cell += self.board.width
        elif key in ('left', 'a', 'h'):
            self.selected_cell -= 1
        elif key in ('right', 'd', 'l'):
            self.selected_cell += 1
        else:
            self.subwidgets[self.selected_cell].keyboard_event(key)
            return

        self.root.keyboard_mode = True
        self.selected_cell %= cell_count  # prevent index error


class FPSWidget(Widget):
    def __init__(self, parent: Widget, y: int, x: int):
        super().__init__(parent, y, x)
        self.h = 1
        self.set_fps(1)  # we don't want to take log10 of 0

    def set_fps(self, fps: int):
        self.fps = fps
        self.str = f'FPS: {round(self.fps, 3 - floor(log10(self.fps))):0<5}'

    def render(self):
        self.addstr(0, 0, self.str)

    @property
    def w(self):
        return len(self.str)


class TextboxWidget(Widget):
    def __init__(self, parent: Widget, y: int, x: int):
        super().__init__(parent, y, x)
        self.h = 1
        self.set_text("")

    def set_text(self, text: str):
        self.text = text

    def render(self):
        self.addstr(0, 0, self.text)

    @property
    def w(self):
        return len(self.text)


class FlagWidget(Widget):
    def __init__(self, parent: Widget, y: int, x: int):
        super().__init__(parent, y, x)
        self.h = 1
        self.flags = config.mine_count

    def set_flag_counts(self, n: int):
        self.flags = n

    def render(self):
        if config.use_emojis:
            self.addstr(0, 0, f'🚩 × {self.flags}')
        else:
            self.addstr(0, 0, f'Ｆ × {self.flags}')


class HelpWidget(Widget):
    HELP_WINDOW = dedent("""\
        ╭────┬───────────────────────────────────────────────╮
        │    │                   HELP                        │
        ├────┴────────────────────┬──────────────────────────┤
        │         Keyboard        │           Mouse          │
        ├─────────────────────────┼──────────────────────────┤
        │     [W]         [↑]     │                          │
        │  [A][S][D]   [←][↓][→]  │           Move           │
        │                         │          Cursor          │
        │      [h][j] [k][l]      │                          │
        │                         │                          │
        │  Flag:        [F]       │  Flag:   [Left click]    │
        │  Reveal:      [R]       │  Reveal: [Right click]   │
        │  Chord:       [Space]   │  Chord:  [Middle click]  │
        │  Restart:     [Enter]   │                          │
        │  Help:        [I]       │                          │
        │  Exit Game:   [Ctrl-C]  │                          │
        ╰─────────────────────────┴──────────────────────────╯
        """)

    def __init__(self, parent: Widget, y: int, x: int):
        super().__init__(parent, y, x)
        self.is_active = False

    @property
    def w(self):
        if not self.is_active:
            # +1 for the full width character ⓘ
            return len("ⓘ press i for help") + 1
        else:
            return 54

    @property
    def h(self):
        if not self.is_active:
            return 1
        else:
            return 16

    def mouse_x(self):
        return Widget.root.mouse_x - self.x

    def mouse_y(self):
        return Widget.root.mouse_y - self.y

    def render(self):
        if not self.is_active:
            self.addstr(0, 0, "ⓘ press i for help")
        else:
            mouse_y = self.mouse_y()
            mouse_x = self.mouse_x()

            for i, row in enumerate(self.HELP_WINDOW.splitlines()):
                self.addstr(i, 0, row)

            if mouse_y < self.h and mouse_x < self.w:
                try:
                    if self.HELP_WINDOW[mouse_y * (self.w + 1) + mouse_x] == ' ':
                        Widget.root.window.addch(Widget.root.mouse_y, Widget.root.mouse_x, curses.ACS_DIAMOND)
                except IndexError:
                    pass

            if mouse_y == 1 and 1 <= mouse_x <= 4:
                self.addstr(1, 1, ' Ｘ ', curses.color_pair(UI_HIGHLIGHT))
            else:
                self.addstr(1, 2, 'Ｘ')

        # emo = config.use_emojis
        # self.addstr(self.status_y_offset + 14, self.status_x_offset + 11, 'Symbols')
        # self.addstr(self.status_y_offset + 15, self.status_x_offset + 6, ('💥' if emo else '＊') + ' Exploded mine')
        # self.addstr(self.status_y_offset + 16, self.status_x_offset + 6, ('🏁' if emo else 'Ｘ') + ' Flagged mine')
        # self.addstr(self.status_y_offset + 17, self.status_x_offset + 6, ('💣' if emo else 'Ｏ') + ' Unflagged mine')
        # self.addstr(self.status_y_offset + 18, self.status_x_offset + 6, ('🚩' if emo else 'Ｆ') + ' Flag')

    def keyboard_event(self, key):
        if key == "i":
            self.is_active = not self.is_active
            self.parent.force_rerender = True

    def mouse_event(self, y, x, mouse):
        if MouseEvent.BUTTON1_RELEASED in mouse:
            if not self.is_active:
                if y == 0 and x == 0:
                    self.is_active = True
                    self.parent.force_rerender = True
            else:
                if y == 1 and 1 <= x <= 4:
                    self.is_active = False
                    self.parent.force_rerender = True


class SmileyWidget(Widget):
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
        self.w = 2
        self.h = 1

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
    def __init__(self, win):
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

        # some useful variables
        self.should_exit = False
        self.force_rerender = False
        self.game_start = True
        self.game_over = True
        self.time_taken = '00:00.00'
        self.time_started = datetime.datetime.now()

        self.frame_count = 0
        self.last_rerender = 0

        self.button1_pressed = False
        self.button2_pressed = False
        self.button3_pressed = False

        self.keyboard_mode = True

        Widget.root = self

        # initialize widgets
        self.grid = GridWidget(self, 0, 0, self.board)
        self.subwidgets.append(self.grid)

        self.status = SmileyWidget(self, 0, 0)
        self.subwidgets.append(self.status)

        self.fps = FPSWidget(self, 0, 0)
        self.subwidgets.append(self.fps)

        self.timer = TextboxWidget(self, 0, 0)
        self.timer.set_text(self.time_taken)
        self.subwidgets.append(self.timer)

        self.flags = FlagWidget(self, 0, 0)
        self.subwidgets.append(self.flags)

        self.help = HelpWidget(self, 0, 0)
        self.subwidgets.append(self.help)

        self.calc_widget_locations()

    def calc_widget_locations(self):
        """Reanchor all sub widgets"""
        winh, winw = self.window.getmaxyx()
        grid_top = floor((winh - self.grid.h) / 2) + 2
        grid_bottom = grid_top + self.grid.h

        grid_left = (winw - self.grid.w) // 2
        grid_right = grid_left + self.grid.w

        self.grid.anchor(grid_top, grid_left)
        self.status.anchor(grid_top - 2, (winw - self.status.w) // 2)
        self.fps.anchor(grid_bottom, grid_right - self.fps.w)
        self.timer.anchor(grid_top - 1, grid_right - self.timer.w)
        self.flags.anchor(grid_top - 1, grid_left)
        if self.help.is_active:
            self.help.anchor((winh - self.help.h) // 2, (winw - self.help.w) // 2)
        else:
            self.help.anchor(grid_bottom, grid_left)

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
        all_events_processed = False
        while not all_events_processed:
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
                # check resize
                if ch == curses.KEY_RESIZE:
                    winh, winw = self.window.getmaxyx()
                    if not config.ignore_failures and (winh < config.min_height or winw < config.min_width):
                        raise InsufficientScreenSpace
                    char = '\0'
                    self.force_rerender = True
                # keyboard input
                elif ch == -1 or self.button2_pressed:
                    # block middle button paste on linux
                    char = '\0'
                    all_events_processed = True
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
        if config.framerate:
            self.render()
            curses.napms(floor((1/config.framerate-(time.time()-self.monitor.last_frame))*1000))
        else:
            self.render()
            curses.napms(1) # voluntary context switch

    def render(self):
        """renders the entire window{"""

        self.frame_count += 1
        if not self.help.is_active:
            # fps also counts rendering time
            # pause fps while help is active
            self.monitor.tick()

        # populate widgets
        self.fps.set_fps(self.monitor.fps)
        self.flags.set_flag_counts(config.mine_count - self.board.flag_count())
        if not self.game_over and not self.help.is_active:
            time_taken = datetime.datetime.now() - self.time_started
            minute, second = divmod(time_taken.seconds, 60)
            msec = str(time_taken.microseconds).zfill(2)[:2]
            self.time_taken = f'{minute:0>2}:{second:0>2}.{msec}'
            self.timer.set_text(self.time_taken)

        self.window.erase()
        self.calc_widget_locations()
        try:
            self.window.addch(self.mouse_y, self.mouse_x, curses.ACS_DIAMOND)
        except curses.error:
            pass  # sometimes mouse fly around and that's ok

        # check winning condition
        if not self.game_over and self.board.check_win():
            self.status.status = '😎'
            self.game_over = True
            self.board.reveal_all()

        for w in self.subwidgets:
            if self.help.is_active and isinstance(w, GridWidget):
                # Hide the grid while help is active
                continue
            w.render()

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
        if self.force_rerender:
            self.force_rerender = False
            self.window.clear()
        self.window.refresh()

    def mouse_event(self, y, x, mouse):
        """handles mouse events for root"""

        # handling close button
        if y == 1 and 2 <= x <= 5:
            if self.button1_pressed:
                self.exit()

        # do the surprised face
        if not self.game_over:
            if self.button1_pressed or self.button2_pressed:
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


def mainloop(win):
    """the mainloop of the program. blocks until exit"""
    win.clear()
    root = RootWidget(win)

    signal.signal(signal.SIGINT, lambda signum, frame: root.exit())
    signal.signal(signal.SIGTERM, lambda signum, frame: root.exit())
    signal.signal(signal.SIGQUIT, lambda signum, frame: root.exit())
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
                # wait until animation ends
                signal.signal(signal.SIGINT, signal.SIG_IGN)
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

    frame = []
    line = ' ╭' + '─' * (width - 4) + '╮ '
    frame.append(line)
    frame.append(pad_window('TERMINAL MINESWEEPER', width, center = True))
    line = ' ├' + '─' * (width - 4) + '┤ '
    frame.append(line)
    for y in range(height - 4):
        frame.append(pad_window('', width))
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
        curses.init_pair(UI_ALT_HIGHLIGHT, UI_HIGHLIGHT_FG, UI_ALT_HIGHLIGHT_BG)
        curses.init_pair(SYSTEM_DEFAULT, -1, -1)
        for i in range(9):
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
