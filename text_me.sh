#!/bin/bash

MESSAGE=$1

cd /home/ghormann/src/christmasnamechecker
source env/bin/activate
python text_me.py "$MESSAGE"
