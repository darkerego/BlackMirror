#!/usr/bin/env bash
##########################

echo "IMPORTANT! Checking for requirements ... !"
python3 -V >/dev/null 2>&1 || { echo '[~] Install python3!' ; exit ;}
pip3 -V >/dev/null 2>&1 || { echo '[~] Install pip3!' ; exit ;}
virtualenv -V >/dev/null 2>&1 || { echo '[~] Install virtualenv!' ; exit ;}
echo "Sweet! Now you can go smoke crack."


virtualenv env
source env/bin/activate
pip3 install -r requirements.txt
pip3 install websocket-client
