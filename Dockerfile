FROM       jsreid13/py_dreal4:initial
MAINTAINER jsreid13@gmail.com

RUN apt-get update && apt-get install -y python3-pip \
      && python3 -m pip install networkx
