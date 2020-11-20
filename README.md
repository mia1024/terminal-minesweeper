A known bug prevents the program from running correctly in konsole.
https://bugs.kde.org/show_bug.cgi?id=423333

## Run
```sh
git clone git@github.com:mia1024/terminal-minesweeper
python3 terminal-minesweeper # no need for cd
```

## Usage
```
usage: terminal-minesweeper [-e | -i | -h | -c WIDTH HEIGHT MINES]
                            [-f FRAMERATE] [--silent-checks] [--no-animation]
                            [-q] [--ignore-failures] [--no-emoji] [-d]
                            [--help]

Options:
  -e, --easy            Set the game difficulty to easy (9x9 board with 10
                        mines)
  -i, --intermediate    Set the game difficulty to intermediate (16x16 board
                        with 40 mines). This is the default.
  -h, --hard            Set the game difficulty to hard (16x30 board with 99
                        mines).
  -c WIDTH HEIGHT MINES, --custom WIDTH HEIGHT MINES
                        Set a custom game difficulty.
  -f FRAMERATE, --framerate FRAMERATE
                        Cap the framerate. Set to 0 to disable, which is the
                        default.
  --silent-checks       Performs the initial system checks quickly and
                        quietly.
  --no-animation        Skip the startup and closing animations. May cause a
                        significant screen flicker when the program starts.
  -q, --quick           A shortcut argument that is the equivalent of
                        supplying both --silent-checks and --no-animation.
  --ignore-failures     Ignore all failures in the initial system checks. Not
                        recommended.
  --no-emoji            Use unicode characters to replace all the emojis. Note
                        that all emojis used by this program are fromEmoji
                        v1.0 released in 2015.
  -d, --debug           Enable debug mode.
  --help                Show this help message and exit.
```
