import json


class Tally:
    """
    Stores stats about the bot's history, such as
    win/loss rate and volume.
    """
    def __init__(self, sql):
        self.sql = sql

    def get(self, value=None):
        x = self.sql.get_list('stats')
        xx = eval(json.loads(json.dumps(x[0])))
        if value is None:
            return xx
        return float(xx.get(value))

    def write(self, value):
        self.sql.clear('stats')
        self.sql.append(value, 'stats')

    def loss(self):
        stats = self.get()
        losses = stats.get('losses')
        losses = int(losses)
        losses += int(1)
        stats['losses'] = losses
        self.write(json.dumps(stats))

    def win(self):
        stats = self.get()
        wins = stats.get('wins')
        wins = int(wins)
        wins += int(1)
        stats['wins'] = wins
        self.write(json.dumps(stats))

    def increment_contracts(self, value):
        stats = self.get()
        ct = stats.get('contracts_traded')
        ct = float(ct)
        ct += float(value)
        stats['contracts_traded'] = ct
        self.write(stats)

    def pnl(self, change, direction=0):
        """
        dir 0: up
        dir 1: down
        """
        stats = self.get()
        ct = stats.get('session_pnl')
        ct += float(change)
        stats['session_pnl'] = ct
        self.write(stats)

    def reset(self):
        self.write(json.dumps({'wins': 0, 'losses': 0, 'contracts_traded': 0.0, 'session_pnl': 0.0}))