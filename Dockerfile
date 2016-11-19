FROM ubuntu:16.04

RUN apt-get -y update
RUN apt-get -y install python3.5 python3-pip libsdl2-dev libsdl2-ttf-dev libsdl2-image-dev libsdl2-mixer-dev gstreamer1.0-plugins-{good,base,bad,ugly} libgstreamer1.0-dev libxine2-ffmpeg libsmpeg-dev libswscale-dev libavformat-dev libavcodec-dev libjpeg-dev libtiff5-dev libx11-dev libmtdev-dev build-essential libgl1-mesa-dev libgles2-mesa-dev xvfb pulseaudio;
