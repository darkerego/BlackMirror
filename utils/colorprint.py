import random
from colored import fg, attr, bg


class NewColorPrint:
    def __init__(self):
        self.i = 0
        self.bright_colors = [1, 3, 5, 8, 32, 44,
                              45, 46, 55, 73, 77, 80, 82, 88, 107, 125,
                              155, 160, 167, 169, 186, 197, 203, 222, 226]

    def purple(self, data):
        print(f'{fg(207)}{data}{attr(0)}')

    def green(self, data):
        print(f'{fg(46)}{data}{attr(0)}')

    def yellow(self, data):
        print(f'{fg(226)}{data}{attr(0)}')

    def red(self, data):
        print(f'{fg(9)}{data}{attr(0)}')

    def blue(self, data):
        print(f'{fg(39)}{data}{attr(0)}')

    def navy(self, data):
        print(f'{fg(27)}{data}{attr(0)}')

    def white(self, data):
        print(f'{fg(231)}{data}{attr(0)}')

    def green_black(self, data):
        print(f'{fg(47)}{bg(0)}{attr(4)}{data}{attr(0)}')

    def blue_black(self, data):
        print(f'{fg(4)}{bg(0)}{data}{attr(0)}')

    def white_black(self, data):
        print(f'{fg(253)}{bg(0)}{data}{attr(0)}')

    def dark(self, data):
        print(f'{fg(57)}{bg(0)}{data}{attr(0)}')

    def alert(self, data):
        print(f'{fg(196)}{bg(0)}{attr(1)}{data}{attr(0)}')

    def ticker_up(self, data):
        print(f'{fg(83)}{bg(0)}{attr(21)}{data}{attr(0)}')

    def ticker_down(self, data):
        print(f'{fg(207)}{bg(0)}{attr(21)}{data}{attr(0)}')

    def iterate_(self, data):
        i = 0
        for f in str(data).strip('\n\r'):
            try:
                print(f'{fg(self.i)}{f}{attr(0)}', end='')
            except KeyError:
                pass
            finally:
                print('\n')
                self.i += 1
        if self.i == 256:
            self.i = 0

    def random_color(self, data, static_set=None):
        if static_set is None:
            color = random.randint(0, 255)
        elif static_set == 'bright':
            color = random.choice(self.bright_colors)
        else:
            color = random.choice(static_set)
        print(f'{fg(color)}{data}{attr(0)}')

    def random_pulse(self, data, static_set='bright'):
        if static_set is None:
            color = random.randint(0, 255)
        elif static_set == 'bright':
            color = random.choice(self.bright_colors)
        else:
            color = random.choice(static_set)
        print(f'{bg(0)}{fg(color)}{data}{attr(0)}')

    def debug(self, data):
        print(f'[debug] {fg(255)}{bg(0)}{data}{attr(0)}')

    def pulse(self, data):
        print(f'{fg(82)}{bg(0)}{attr(21)}{attr(1)}{data}{attr(0)}')