class MqttQue:
    msgs = []

    def __mq__signal__(self):
        try:
            return self.msgs.pop()
        except IndexError:
            return None

    def append(self, data):
        self.msgs.append(data)