FROM       jsreid13/py_dreal4:stable
MAINTAINER jsreid13@gmail.com

WORKDIR /home

RUN apt update \
    && apt install -y --no-install-recommends wget \
	&& wget https://bootstrap.pypa.io/get-pip.py \
	&& python3 get-pip.py
# Install OpenModellica
RUN for deb in deb deb-src; do echo "$deb http://build.openmodelica.org/apt `awk -F"[)(]+" '/VERSION=/ {print $2}' /etc/os-release | awk '{print $1}' | awk '{ print tolower($0) }'` stable"; done | tee /etc/apt/sources.list.d/openmodelica.list
RUN wget -q http://build.openmodelica.org/apt/openmodelica.asc -O- | apt-key add - \
    && apt update \
    && apt install -y --no-install-recommends openmodelica \
    && python3 -m pip install -U https://github.com/OpenModelica/OMPython/archive/master.zip
# Install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY tests ./
