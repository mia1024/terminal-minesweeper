import os
import signal
import sys
import time

from .config import config
from .debug import init_print, end_print


def print_slow(text: str, trailing_newline = True, prefix = '', suffix = '', delay = 0.015):
    """
    writes contents to stdout one character at a time,
    with delay seconds in between each print
    """
    sys.stdout.write(prefix)
    sys.stdout.flush()
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print(suffix, flush = True, end = '')
    if trailing_newline:
        print()


def check(condition: bool, name: str, error_message: str):
    """
    Checking if a condition is met before starting the game. Aborting
    the initialization if the condition isn't met.
    """
    if config.silent_checks:
        if not (condition or config.ignore_failures):
            print('\033[37mError: ' + error_message + '\033[0m')
            print('\033[?25h', end = '')  # reenable cursor
            sys.exit(1)
        else:
            return
    prefix = 'Checking ' + name + '...'
    print_slow(prefix, trailing_newline = False)
    if condition:
        print_slow('PASSED', prefix = '\033[92m', suffix = '\033[0m', )
    else:
        if not config.ignore_failures:
            print_slow('FAILED', prefix = '\033[91m', suffix = '\033[0m')
            print_slow(error_message)
            print('\033[37m', end = '')
            print_slow('Alternatively, you may pass in the --ignore-failure switch.', delay = 0.005)
            print_slow('However, you may encounter a curses error if you do so.', delay = 0.005)
            print('\033[0m', end = '')
            sys.exit(1)
        else:
            print_slow('FAILURE IGNORED', prefix = '\033[91m', suffix = '\033[0m')
            print()


def run():
    """Run the program. Put inside a function so it can be imported"""

    def sigint_handler(signum, frame):
        """
        SIGINT handler during the initialization. this will be replaced by a
        a different hanlder when the mainloop starts.
        """
        print('\033[0m\nAlright. Alright. We aren\'t sweeping any mines today (T＿T)')
        print('\033[?25h', end = '')  # reenable cursor
        sys.exit(2)

    system_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, sigint_handler)

    if not config.silent_checks:
        print('\033[?25l', end = '')  # disable cursor
        print_slow('Welcome to terminal minesweeper by Mia Celeste')
        if len(sys.argv) == 1:
            print()
            print_slow('No option was specified. Using default settings.')
            print_slow('To see a list of possible options, run this program with --help.')
        print_slow('\nCommencing system check.')

    # checking for python3.6+
    v = sys.version_info
    check(v.major == 3 and v.minor >= 6,
          'Python version',
          'Please use Python3.8 or above.'
          )

    # check if curses is present
    try:
        import curses
    except:
        curses_ok = False
    else:
        curses_ok = True

    check(curses_ok, 'if curses is present',
          'Cannot import curses, please check your Python installation.'
          ' Perhaps try installing Cygwin or windows-curses?' if sys.platform == 'win32' else ''
          )

    width, height = os.get_terminal_size()

    # check the window size to meet the minimum size requirement
    check(
        width >= config.min_width and height >= config.min_height,
        'window size',
        f'Please make sure your terminal window has at least '
        f'{f"{config.min_width} ({config.min_width - width} more) columns" if width < config.min_width else ""}'
        f'{" and " if width < config.min_width and height < config.min_height else ""}'
        f'{f"{config.min_height} ({config.min_height - height} more) rows" if height < config.min_height else ""}, '
        f'or specify a smaller board size.'
    )

    from .ui import main, calc_first_frame, FG, BG, UI_COLORS_USED

    if config.show_animation:
        print_slow("Testing terminal color support...",trailing_newline = False)
        for c in UI_COLORS_USED:
            if c!=BG:
                print_slow(f"{c}",prefix = f"\033[38;5;{c}m\033[48;5;{BG}m",suffix = "\033[0m ",trailing_newline = False)
        print("\n")
        print_slow('All system checks completed, ready to sweep some mines（＾ω＾）')
        print_slow('You have selected {} difficulty, which has a {}x{} grid with {} mines.\n'.format(
            config.difficulty, config.board_width, config.board_height, config.mine_count
        ))
        print_slow(r'Printing a window in the hope that it will come into life ◦°˚\(*❛ ‿ ❛)/˚°◦')
        print_slow('Please lend me your power, Python magic!\nBalabala pew (∩^o^)⊃━☆゜.*', trailing_newline = False)

    # only import everything after the system checks so we don't get random
    # SyntaxError or NameError for lower python versions

    if config.show_animation:
        # show a start up animation before going into curses for the scrolling effect
        for i, row in enumerate(calc_first_frame(height, width)):
            print()
            print_slow(row, delay = max(0.01 / (i + 1), 0.0005), prefix = f'\033[38;5;{FG}m\033[48;5;{BG}m',
                       suffix = '\033[0m',
                       trailing_newline = False)
            # speeding up so the user doesn't get too bored
            print('\033[0m', end = '')
        print('\033[0m', end = '')
        sys.stdout.flush()
    else:
        print()

    # restores the default SIGINT handler
    signal.signal(signal.SIGINT, system_sigint_handler)

    # initializes debug print and run the program
    init_print()
    exit_message, exit_status = main()
    end_print()

    # recalculate screen sizes in case it changed
    width, height = os.get_terminal_size()

    if exit_message:
        if config.show_animation:
            # clear the screen but with fast printing since the
            # program crashed.
            print('\033[0;2J\033[0;0H', end = '', flush = True)
        print('\033[91m' + exit_message + '\033[0m', flush = True)
    elif exit_status == 0 and config.show_animation:

        def sigint_handler(signum, frame):
            """
            sigint handler for impatient people. Skip the final animation.
            """
            print('\033[0;2J\033[0;0H', end = '', flush = True)
            sys.exit(exit_status)

        signal.signal(signal.SIGINT, sigint_handler)

        # do the reverse animation. using raw ansi sequences
        # to erase the previously printed static frame

        print(f'\033[0m', flush = True, end = '')
        frames = calc_first_frame(height, width)
        for y in range(height):
            for x in range(width):
                print(f'\r\033[38;5;{FG}m\033[48;5;{BG}m' + frames[height - y - 1][:width - x - 1] + '\033[0m' + ' ' * (
                        x + 1), end = '', flush = True)
                time.sleep(max(0.01 / (height - y), 0.0005))
            print('\033[F', end = '', flush = True)
        # erase screen and move cursor to top left corner
        print('\033[0;2J\033[0;0H', end = '', flush = True)
        print_slow('Thanks, Python magic. I knew you wouldn\'t fail me ⊂(´・ω・｀⊂)')
        print_slow('(You may skip this animation with the -q flag next time)',prefix="\033[38;5;244m", suffix="\033[0m",delay=0.0075)
    sys.exit(exit_status)
