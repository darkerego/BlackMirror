class MqttQue:
    incoming_msgs = []
    outgoing_msgs = []

    def read_incoming(self):
        try:
            return self.incoming_msgs.pop()
        except IndexError:
            return None

    def append_incoming(self, data):
        try:
            assert list(data) and len(data) == 2
        except AssertionError:
            print(f'[!] Must supply [topic, message]')
            return False
        else:
            self.incoming_msgs.append(data)

    def read_outbox(self):
        try:
            return self.outgoing_msgs.pop()
        except IndexError:
            return None

    def append_outbox(self, data):
        try:
            assert list(data) and len(data) == 2
        except AssertionError:
            print(f'[!] Must supply [topic, message]')
            return False
        else:
            self.outgoing_msgs.append(data)
