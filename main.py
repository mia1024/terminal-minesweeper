import sys, os, time
from config import config
import signal


def sigint_handler(signum, frame):
    print('\033[0m\nAlright. Alright. You aren\'t sweeping any mines today')
    print('\033[?25h', end='')  # reenable cursor
    sys.exit(2)


system_sigint_handler = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, sigint_handler)


def print_slow(text: str, trailing_newline=True, prefix='', suffix='', delay=0.02):
    print(prefix, flush=True, end='')
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print(suffix, flush=True, end='')
    if trailing_newline: print()


def check(condition: bool, name: str, error_message: str):
    if config.silent_checks:
        if not (condition or config.ignore_failures):
            print('\033[37mError: ' + error_message + '\033[0m')
            sys.exit(1)
        else:
            return
    prefix = 'Checking ' + name + '...'
    print_slow(prefix, trailing_newline=False)
    if condition:
        print_slow('PASSED', prefix='\033[92m', suffix='\033[0m', )
    else:
        if not config.ignore_failures:
            print_slow('FAILED', prefix='\033[91m', suffix='\033[0m')
            print_slow(error_message)
            print('\033[37m', end='')
            print_slow('Alternatively, you may pass in the --ignore-failure switch.', delay=0.01)
            print_slow('However, you will probably encounter a curses error if you do so.', delay=0.01)
            print('\033[0m', end='')
            sys.exit(1)
        else:
            print_slow('FAILURE IGNORED', prefix='\033[91m', suffix='\033[0m')
            print()


if not config.silent_checks:
    print('\033[?25l', end='')  # disable cursor
    print_slow('Welcome to terminal minesweeper by Mia Celeste')
    print_slow('Commencing system check.')

v = sys.version_info
check(v.major == 3 and v.minor >= 8,
      'Python version',
      'Please use Python3.8 or above.'
      )

check('xterm-256color' in os.environ.get('TERM', ''),
      'terminal compatibility',
      'Please use an xterm-256color compatible terminal'
      ' such as MinTTY' if sys.platform == 'win32' else '.'
      )

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

min_width = config.board_width * 5 + 1 + 10 + 22
min_height = config.board_height * 2 + 4
check(width >= min_width, 'window width',
      f'Please make sure your terminal window has at least {min_width} ({min_width - width} more) columns.')
check(height >= min_height, 'window height',
      f'Please make sure your terminal window has at least {min_height} ({min_height - height} more) rows.')

if config.show_animation:
    print()
    print_slow('All system checks completed, ready to sweep some mines（＾ω＾）')
    print_slow('You have selected {} difficulty, which has a {}x{} grid with {} mines\n'.format(
        config.difficulty,config.board_width,config.board_height,config.mine_count
    ))
    print_slow(r'Printing a window in the hope that it will come into life ◦°˚\(*❛ ‿ ❛)/˚°◦')
    print_slow('Please lend me your power, Python magic!\nBalabala pew (∩^o^)⊃━☆゜.*', trailing_newline=False)

from ui import main, calc_first_frame, FG, BG

# only import everything after the system checks so we don't get random
# SyntaxError or NameError for lower python versions

if config.show_animation:
    for i, row in enumerate(calc_first_frame(height, width)):
        print()
        print_slow(row, delay=max(0.02 / (i + 1), 0.0005), prefix=f'\033[38;5;{FG}m\033[48;5;{BG}m', suffix='\033[0m',
                   trailing_newline=False)
        # speeding up so the user doesn't get too bored
        print('\033[0m', end='')
    print('\033[0m', end='')
    sys.stdout.flush()
else:
    print()

signal.signal(signal.SIGINT, system_sigint_handler)
exit_message, exit_status = main()
# if config.show_startup_animation: print()  # to consume the last \r
if exit_message:
    print('\033[91m' + exit_message + '\033[0m', flush=True)
elif exit_status == 0 and config.show_animation:
    width, height = os.get_terminal_size()
    # recalculate in case it changed
    print(f'\033[0m',flush=True,end='')
    frames=calc_first_frame(height,width)
    for y in range(height):
        for x in range(width):
            print(f'\r\033[38;5;{FG}m\033[48;5;{BG}m'+frames[height-y-1][:width-x-1]+'\033[0m'+' '*(x+1),end='',flush=True)
            time.sleep(max(0.02 / (y + 1), 0.0005))
        print('\033[F',end='',flush=True)
    print('\033[0;0H', end='', flush=True)
    # erase screen and move cursor to top left corner
sys.exit(exit_status)
