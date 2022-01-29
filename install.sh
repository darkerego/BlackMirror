#!/usr/bin/env bash
##########################
python3 -V >/dev/null 2>&1 || { echo '[~] Install python3!' ; exit ;}
pip3 install -r requirements.txt
pip3 install websocket-client
