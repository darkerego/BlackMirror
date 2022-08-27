import asyncio
import asyncio
import logging
import os
import random
import signal
import time
import random
from gmqtt import Client as MQTTClient
from lib.mq.mqtt_que import MqttQue
import string
logging.basicConfig(filename='mqtt.log', level=logging.INFO)
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
            self.outgoing_msgs.append(str(data))

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
            self.outgoing_msgs.append(str(data))

message_que = MqttQue()

class MqttClient:
    def __init__(self, host, port, subscriptions=None, debug=True):
        if subscriptions is None:
            self.subscriptions = ['/stream', '/signals', '/echo']
        self.host = host
        self.port = port
        self.client = None
        self.cid = "blackmirror_"
        self.que = message_que
        self.debug = debug

        self.logger = logging.getLogger(__name__)
        self.STOP = asyncio.Event()

    def generate_client_id(self):
        for _ in range(8):
            self.cid += random.choice(string.ascii_letters)
        return self.cid

    def on_connect(self, client, flags, rc, properties):
        print('[+] Connected')

    def on_message(self, client, topic, payload, qos, properties):
        # print(f'RECV MSG: {topic} {payload}')
        self.que.append_incoming([topic, payload.decode()])

    def on_subscribe(self, client, mid, qos, properties):
        print('SUBSCRIBED')

    def on_disconnect(self, client, packet, exc=None):
        print('Disconnected')

    def ask_exit(self, *args):
        self.STOP.set()

    def subscribe(self, topic):

        print(f'Subscribing to {topic}')
        self.client.subscribe(topic)

    def publish(self, topic, message):
        print(f'Publishing ... {message} to {topic}')
        self.client.publish(topic, message, qos=1)

    async def publish_from_que(self):
        print('Start pub from que ..')
        while True:
            msg = self.que.read_outbox()
            if msg is not None:
                topic = msg[0]
                message = msg[1]
                self.publish(topic=topic, message=message)
            await asyncio.sleep(1)

    async def start_loop(self):
        cid = self.generate_client_id()
        self.cid = cid
        print(f'[+] MqTT connecting with unique client ID: {self.cid}')
        self.client = MQTTClient(client_id=self.cid)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect

        # Connect to mqtt proxy
        await self.client.connect(host=self.host, port=self.port)
        [self.subscribe(_) for _ in self.subscriptions]

        # await self.publish_from_que()
        await self.STOP.wait()
        await self.client.disconnect()


async def main(host='localhost', port='1883'):
    _mq = MqttClient(host=host, port=int(port))
    # loop = asyncio.get_event_loop()
    await _mq.start_loop()


if __name__ == '__main__':
    asyncio.run(main())
