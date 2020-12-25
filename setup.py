from setuptools import setup

setup(
    name = 'terminal-minesweeper',
    description='A pure Python implementation of minesweeper using curses.',
    version = '0.1.0',
    author = 'Mia Celeste',
    author_email = 'mia@miaceleste.dev',
    url = 'https://github.com/mia1024/terminal-minesweeper',
    python_requires = '>=3.8',
    scripts = ['minesweeper/minesweeper'],
    packages = ['minesweeper'],
    install_requires = [
        "windows-curses ; platform_system == 'windows'"
    ]
)
