import os
import sys


ESCAPE_SEQ = '\033[%dm'
BOLD = ESCAPE_SEQ % 1
RESET = ESCAPE_SEQ % 0
COLORS = ['black', 'red', 'green', 'yellow',
          'blue', 'magenta', 'cyan', 'white']
COLORS = dict((c, 30 + i) for i, c in enumerate(COLORS))


def colorize(text, color, is_bold=True):
    if not os.isatty(sys.stdout.fileno()):
        return text

    t = (ESCAPE_SEQ % COLORS[color])
    if is_bold:
        t += BOLD
    t += text
    t += RESET
    return t
