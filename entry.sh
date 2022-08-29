#!/bin/bash
source env/bin/activate
 python -c 'from websocket import WebSocketApp'|| pip3 install websocket-client==0.37.0
python3 app.py "$@"
