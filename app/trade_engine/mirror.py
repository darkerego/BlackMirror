import time

from trade_engine.api_wrapper import FtxApi


class TradeMirror:
    def __init__(self, master: str, clients: list, markets: list, api: FtxApi):
        self.master = master
        self.clients = clients
        self.markets = markets
        self.api = api
        self.order_queue = []

    def parse_order(self, order: dict):
        pass

    def start_loop(self):

        while True:
            orders = self.api.ws_order_stream()
            conditional = self.api.rest_trigger_order_history()
            if len(orders):
                for order in orders:
                    self.order_queue.append(order)
                for c_order in conditional:
                    self.order_queue.append(c_order)
            time.sleep(0.5)
