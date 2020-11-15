import argparse, sys


class SingletonMeta(type):
    def __call__(cls, *args, **kwargs):
        if hasattr(cls, '_instance'):
            return cls._instance
        else:
            obj = cls.__new__(cls, *args, **kwargs)
            obj.__init__(*args, **kwargs)
            cls._instance = obj
            return obj


class Config(metaclass=SingletonMeta):
    def __init__(self):
        self.use_emojis = True
        self.framerate = 60
        self.board_width = 16
        self.board_height = 16
        self.mine_count = 40
        self.silent_checks = False
        self.ignore_failures = False
        self.show_startup_animation = True


config = Config()
parser = argparse.ArgumentParser(prog='terminal-minesweeper', add_help=False)
g = parser.add_argument_group('Options')
group = g.add_mutually_exclusive_group()
group.add_argument('-e', '--easy', action='store_true',
                   help='Set the game difficulty to easy (9x9 board with 10 mines)')
group.add_argument('-i', '--intermediate', action='store_true',
                   help='Set the game difficulty to intermediate (16x16 board with 40 mines). This is the default.')
group.add_argument('-h', '--hard', action='store_true',
                   help='Set the game difficulty to hard (16x30 board with 99 mines).')
group.add_argument('-c', '--custom', nargs=3, type=int, metavar=('width', 'height', 'mines'),
                   help='Set a custom game difficulty.')

g.add_argument('--silent-checks', action='store_true',
               help='Performs the initial system checks quickly and quietly.')
g.add_argument('--no-startup-animation', action='store_true',
               help='Skip the startup animation and starts the game'
                    'directly. May cause a significant screen flicker when the'
                    'program starts.')
g.add_argument('--ignore-failures', action='store_true',
               help='Ignore all failures in the initial system checks. Not recommended.')

g.add_argument('--help', action='store_true', help='Show this help message and exit.')
args = parser.parse_args()

if args.help:
    parser.print_help()
    sys.exit(0)

config.ignore_failures = args.ignore_failures
config.silent_checks = args.silent_checks
config.show_startup_animation = not args.no_startup_animation

if args.easy:
    config.board_width = 9
    config.board_height = 9
    config.mine_count = 10
elif args.hard:
    config.board_width = 16
    config.board_height = 30
    config.mine_count = 99
elif args.custom:
    config.board_width, config.board_height, config.mine_count = args.custom
