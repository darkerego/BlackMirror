class MessageQue:
    messages = []

    def append(self, data):
        self.messages.append(data)

    def get(self):
        try:
            return self.messages.pop()
        except IndexError:
            return False