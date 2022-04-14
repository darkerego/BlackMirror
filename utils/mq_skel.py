from datetime import datetime

import numpy as np
import paho.mqtt.client as mqtt
import random

from utils import mqtt_que
#from ftxtool import mqtt_que
mqtt_que = mqtt_que.MqttQue()
#from utils import sql_lib
import pandas as pd



klines = {}

#sql = sql_lib.SQLLiteConnection()

class MqSkel:
    def __init__(self, host='localhost', port=1883, topic='/signals', debug=False):
        self.streamid = 'blackmirror_'
        for _ in (x for x in random.sample('abcdefghijkl', 5)):
            self.streamid += _
        self.host = host
        self.port = port
        self.debug = False
        self.CLIENTS = {}
        # SUBSCRIPTIONS = [("/incoming/" + v, 0)  for v in PAIRS]
        self.SUBSCRIPTIONS = [(f'{topic}', 0), ('/echo', 0)]
        print(f'[m] Starting MqTT Receiver ... Topic is: {topic}')
        self.mqStart(streamId=self.streamid)

    def mqConnect(self, client, userdata, flags, rc):
        """ MQTT Connect Event Listener
        :param client:      Client instance
        :param userdata:    Private userdata as set in Client() or userdata_set()
        :param flags:       Dict of broker reponse flags
        :param rc:          Int of connection state from 0-255:
                                0: Successful
                                1: Refused: Incorrect Protocol
                                2: Refused: Invalid Client ID
                                3: Refused: Server Unavailable
                                4: Refused: Incorrect User/Password
                                5: Refused: Not Authorised
        """
        if rc == 0:
            print("Connected Successfully")
        else:
            print("Refused %s" % rc)


    def mqDisconnect(self, client, userdata, rc):
        """ MQTT Connect Event Listener
        :param client:      Client instance
        :param userdata:    Private userdata as set in Client() or userdata_set()
        :param rc:          Int of disconnection state:
                                0: Expected Disconnect IE: We called .disconnect()
                                _: Unexpected Disconnect
        """
        if rc == 0:
            print("Disconnected")
        else:
            print("Error: Unexpected Disconnection")


    def mqParse(self, client, userdata, message):
        """
        1499040000000,      // Open time
            "0.01634790",       // Open
            "0.80000000",       // High
            "0.01575800",       // Low
            "0.01577100",       // Close
            "148976.11427815",  // Volume
            1499644799999,      // Close time
            "2434.19055334",    // Quote asset volume
            308,                // Number of trades
            "1756.87402397",    // Taker buy base asset volume
            "28.46694368",      // Taker buy quote asset volume
            "17928899.62484339" // Ignore.
          ]
        """

        if "/echo" in message.topic:
            print(message.payload)
        elif f'{self.topic}' in message.topic:
            print(message.payload.decode())
            mqtt_que.append(message.payload.decode())


    def mqPublish(self, payload, topic, qos=0, retain=False, id=None):
        """ MQTT Publish Message to a Topic
        :param id           String of the Client ID
        :param topic:       String of the message topic
        :param payload:     String of the message body
        :param qos:         Int of QoS state:
                                0: Sent once without confirmation
                                1: Sent at least once with confirmation required
                                2: Sent exactly once with 4-step handshake.
        :param retain:      Bool of Retain state
        :return             Tuple (result, mid)
                                result: MQTT_ERR_SUCCESS or MQTT_ERR_NO_CONN
                                mid:    Message ID for Publish Request
        """
        id = self.streamid
        global CLIENTS

        client = self.CLIENTS.get(id, False)
        if not client:
            raise ValueError("Could not find an MQTT Client matching %s" % id)
        client.publish(topic, payload=payload, qos=qos, retain=retain)


    def mqStart(self, streamId):
        """ Helper function to create a client, connect, and add to the Clients recordset
        :param streamID:    MQTT Client ID
        :returns mqtt client instance
        """
        global CLIENTS
        client = mqtt.Client(streamId, clean_session=False)
        # client.username_pw_set(config.mq_user, config.mq_pass)
        # Event Handlers
        client.on_connect = self.mqConnect
        client.on_disconnect = self.mqDisconnect
        client.on_message = self.mqParse
        # Client.message_callback_add(sub, callback) TODO Do we want individual handlers?
        # Connect to Broker
        client.connect(self.host, port=self.port,
                       keepalive=60)
        # Subscribe to Topics
        client.subscribe(self.SUBSCRIPTIONS)  # TODO Discuss QoS States
        client.loop_start()
        self.CLIENTS[streamId] = client
        return client


