from trade_engine import api_wrapper
import argparse


class FundManager:
    def __init__(self, currency, destination):
        self.currency = currency
        self.destination = destination
        self.api = api_wrapper.debug_api()

    def check_balances(self):
        return self.api.balances()