import argparse
import sys


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
        self.framerate = 60
        self.board_width = 16
        self.board_height = 16
        self.mine_count = 40
        self.silent_checks = False
        self.ignore_failures = False
        self.show_animation = True
        self.difficulty = 'intermediate'
        self.debug = False


config = Config()
parser = argparse.ArgumentParser(prog = 'terminal-minesweeper', add_help = False)
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
                   metavar = ('width', 'height', 'mines'),
                   help = 'Set a custom game difficulty.')

g.add_argument('--silent-checks', action = 'store_true',
               help = 'Performs the initial system checks quickly and quietly.')
g.add_argument('--no-animation', action = 'store_true',
               help = 'Skip the startup and closing animations.'
                      'May cause a significant screen flicker when the program '
                      'starts.')
g.add_argument('-q', '--quick', action = 'store_true',
               help = 'A shortcut argument that is the equivalent of supplying'
                      'both --silent-checks and --no-animation.')
g.add_argument('--ignore-failures', action = 'store_true',
               help = 'Ignore all failures in the initial system checks.'
                      ' Not recommended.')
g.add_argument('--no-emoji', action = 'store_true',
               help = 'Use unicode characters to replace all the emojis.'
                      'Note that all emojis used by this program are from'
                      'Emoji v1.0 released in 2015.')
g.add_argument('-d', '--debug', help = 'Enable debug mode.', action = 'store_true')

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

if args.easy:
    config.board_width = 9
    config.board_height = 9
    config.mine_count = 10
    config.difficulty = 'easy'
elif args.hard:
    config.board_width = 16
    config.board_height = 30
    config.mine_count = 99
    config.difficulty = 'hard'
elif args.custom:
    config.difficulty = 'custom'
    config.board_width, config.board_height, config.mine_count = args.custom
