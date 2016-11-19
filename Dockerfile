FROM ubuntu:16.04

RUN apt-get -y update
RUN apt-get -y install python3.4 python3-pip
#RUN apt-get -y install python python-all-dev python-pip libyaml-dev
#RUN pip install pyyaml
