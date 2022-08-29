#!/usr/bin/env bash
##########################

echo "IMPORTANT! Checking for requirements ... !"
python3 -V >/dev/null 2>&1 || { echo '[~] Install python3!' ; exit ;}
pip3 -V >/dev/null 2>&1 || { echo '[~] Install pip3!' ; exit ;}
python3 -m virtualenv -V >/dev/null 2>&1 || { echo '[~] Install virtualenv!' ; exit ;}
echo "Sweet! Now you can go smoke crack."

echo 'Need to install talib ...  will need root at some point'
python3 -c 'import talib' ||  (wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz; \
tar -xf ta*.tar.gz;cd ta-lib*;./configure;make;sudo make install;pip3 install ta-lib)

echo 'Attempting to install all the dependencies. If this fails, just keep running app.py and installing whatever is missing until it runs.'


python3 -m virtualenv env
source env/bin/activate
pip3 install -r req.txt
pip3 install websocket-client
