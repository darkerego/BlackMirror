import threading


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, *init_args, **init_kwargs):
        threading.Thread.__init__(self, *init_args, **init_kwargs)
        self._return = None

    def run(self):
        self._return = self._target(*self._args, **self._kwargs)

    def join(self):
        threading.Thread.join(self)
        return self._return


def logwrapper(func):
    '''Decorator that reports the execution time.'''

    def wrap(*args, **kwargs):
        for a in kwargs:
            if a == 'n':
                print(a)
        result = func(*args, **kwargs)
        # end = time.time()

        # print(func.__name__, end - start)
        return result

    return wrap


@logwrapper
def countdown(n):
    '''Counts down'''
    while n > 0:
        n -= 1