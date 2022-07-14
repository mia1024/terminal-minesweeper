import argparse
import sys
import os


class SingletonMeta(type):
    """
    A straightforward metaclass for implementing singleton so that changes to
    the config object during runtime is kept the same across different modules
    """

    def __call__(cls, *args, **kwargs):
        """
        constructs the object if it's never constructed before, else return
        the copy constructed last time. This does mean that on subsequent
        invocation of this function, no args or kwargs need to be passed even
        if the object constructor requires some. Yes the IDE will complain about
        the missing argument but that's what the ignore error button is for.

        :param args: args passed to the object constructor and initializer
        :param kwargs: kwargs passed to the object constructor and initializer
        :return: the object, whether newly created or cached
        """
        if hasattr(cls, '_instance'):
            return cls._instance
        else:
            obj = cls.__new__(cls, *args, **kwargs)
            obj.__init__(*args, **kwargs)
            cls._instance = obj
            return obj


class Config(metaclass = SingletonMeta):
    """
    A simple class holding all the important game configurations. It's a
    singleton
    """

    def __init__(self):
        "Initialize the object to default values"
        self.use_emojis = True
        self.framerate = 0
        self.board_width = 9
        self.board_height = 9
        self.mine_count = 10
        self.silent_checks = False
        self.ignore_failures = False
        self.show_animation = True
        self.difficulty = 'easy'
        self.debug = False
        self.dark_mode = False

    @property
    def min_width(self):
        # board width + 2 for each side
        return max(self.board_width * 5 + 1 + 4, 54 + 4)

    @property
    def min_height(self):
        # board height + 3 top for window + 1 bottom for window
        # + 1 status row + 1 fps row + 1 smiley face
        return max(self.board_height * 2 + 1 + 3 + 4, 16 + 4)


force_fps = None
try:
    force_fps = int(os.environ.get("MINESWEEPER_FORCE_FPS"))
except (TypeError, ValueError):
    pass

config = Config()
parser = argparse.ArgumentParser(prog = 'minesweeper', add_help = False)
g = parser.add_argument_group('Options')
group = g.add_mutually_exclusive_group()
group.add_argument('-e', '--easy', action = 'store_true',
                   help = 'Set the game difficulty to easy (9x9 board with 10'
                          ' mines)')
group.add_argument('-i', '--intermediate', action = 'store_true',
                   help = 'Set the game difficulty to intermediate (16x16 board'
                          ' with 40 mines). This is the default.')
group.add_argument('-h', '--hard', action = 'store_true',
                   help = 'Set the game difficulty to hard (16x30 board with 99'
                          ' mines).')
group.add_argument('-c', '--custom', nargs = 3, type = int,
                   metavar = ('WIDTH', 'HEIGHT', 'MINES'),
                   help = 'Set a custom game difficulty.')
g.add_argument('-d', '--dark-mode', help = 'Enable dark mode.', action = 'store_true')

if not force_fps:
    g.add_argument('-f', '--framerate', type = int, default = 0,
                   help = 'Cap the framerate. Set to 0 to disable, '
                          'which is the default. If MINESWEEPER_FORCE_FPS env '
                          'is set, this option will be ignored.')

g.add_argument('--silent-checks', action = 'store_true',
               help = 'Performs the initial system checks quickly and quietly.')
g.add_argument('--no-animation', action = 'store_true',
               help = 'Skip the startup and closing animations. '
                      'May cause a significant screen flicker when the program '
                      'starts.')
g.add_argument('-q', '--quick', action = 'store_true',
               help = 'A shortcut argument that is the equivalent of supplying '
                      'both --silent-checks and --no-animation.')
g.add_argument('--ignore-failures', action = 'store_true',
               help = 'Ignore all failures in the initial system checks.'
                      ' Not recommended.')
g.add_argument('--no-emoji', action = 'store_true',
               help = 'Use unicode characters to replace all the emojis. '
                      'Note that all emojis used by this program are from '
                      'Emoji v1.0 released in 2015.')
g.add_argument('--debug', help = 'Enable debug mode.', action = 'store_true')

g.add_argument('--help', action = 'store_true',
               help = 'Show this help message and exit.')
args = parser.parse_args()

if args.help:
    parser.print_help()
    sys.exit(0)

config.ignore_failures = args.ignore_failures
config.debug = args.debug
config.silent_checks = args.silent_checks or args.quick
config.show_animation = not (args.no_animation or args.quick)
config.use_emojis = not args.no_emoji
config.dark_mode = bool(args.dark_mode)
if force_fps:
    config.framerate = force_fps
else:
    config.framerate = args.framerate

if args.intermediate:
    config.board_width = 16
    config.board_height = 16
    config.mine_count = 40
    config.difficulty = 'intermediate'
elif args.hard:
    config.board_width = 30
    config.board_height = 16
    config.mine_count = 99
    config.difficulty = 'hard'
elif args.custom:
    config.difficulty = 'custom'
    config.board_width, config.board_height, config.mine_count = args.custom
