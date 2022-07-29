import json
class Tally:
    def __init__(self, sql):
        self.sql = sql

    def get(self, value=None):
        x = self.sql.get_list('stats')
        xx = eval(json.loads(json.dumps(x[0])))
        if value is None:
            return xx
        return xx.get(value)

    def write(self, value):
        self.sql.clear('stats')
        self.sql.append(value, 'stats')

    def loss(self):
        stats = self.get()
        losses = stats.get('losses')
        losses +=1
        stats['losses'] = losses
        self.write(json.dumps(stats))

    def win(self):
        stats = self.get()
        wins = stats.get('wins')
        wins += 1
        stats['wins'] = wins
        self.write(json.dumps(stats))

    def increment_contracts(self, value):
        stats = self.get()
        ct = stats.get('contracts_traded')
        ct = float(ct)
        ct += value
        stats['contracts_traded'] = ct
        self.write(stats)

    def reset(self):
        self.write(json.dumps({'wins': 0, 'losses': 0, 'contracts_traded': 0.0}))