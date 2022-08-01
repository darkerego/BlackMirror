import logging, sys, time


class CustomLogger(logging.Logger):
    def __init__(
            self,
            log_file='customlogger.log',
            log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            *args,
            **kwargs
    ):
        self.file_handler = None
        self.stdout_handler = None
        self.formatter = logging.Formatter(log_format)
        self.log_file = log_file
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.ts = time.time()
        self.logfile = str(log_file)
        self.formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')


    def setup_stdout_handler(self):
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.stdout_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.stdout_handler)

    def setup_file_handler(self):
        self.file_handler = logging.FileHandler(self.logfile)
        self.file_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.file_handler)

    def get_stream_logger(self):
        self.setup_stdout_handler()
        return self.logger

    def get_logger(self):
        self.setup_file_handler()
        return self.logger


