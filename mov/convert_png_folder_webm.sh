#!/bin/bash
QUALITY="1M"
FRAMERATE="10"
ffmpeg -framerate $FRAMERATE -f image2 -i ./%03d.png -c:v libvpx -crf 10 -b:v $QUALITY -auto-alt-ref 0 output.webm
