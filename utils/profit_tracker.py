class SessionProfits:
    def __init__(self, instrument):
        self.instrument = instrument
        self.pnl = 0.0

    def update(self, value):
        if float(value) > 0:
            self.pnl += value
        else:
            self.pnl -= value

    def get(self):
        return self.pnl

