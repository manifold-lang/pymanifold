FROM ubuntu:bionic
MAINTAINER jsreid13@gmail.com

RUN echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/yes && \
    apt-get update

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
    # tzdata is installed and requires human input, this disables that
    apt-get -y install tzdata

# RUN apt-get -y build-dep libcurl4-openssl-dev && \
RUN apt-get -y install libcurl4-openssl-dev

RUN apt-get install -y git  \
                       apt-utils  \
                       make  \
                       asciidoc  \
                       pandoc  \
                       gettext  \
                       po4a  \
                       dblatex  \
                       texlive-xetex  \
                       fonts-vlgothic  \
                       source-highlight  \
                       texlive-lang-english  \
                       # texlive-lang-french  \
                       # texlive-lang-italian  \
                       # texlive-lang-japanese  \
                       # texlive-lang-polish  \
                       # texlive-lang-spanish  \
                       # texlive-lang-cyrillic  \
                       # texlive-lang-german  \
                       bzr  \
                       bzrtools  \
                       build-essential  \
                       cmake  \
                       cmake-curses-gui  \
                       debhelper  \
                       doxygen  \
                       grep  \
                       libbz2-dev  \
                       libcairo2-dev  \
                       libglew-dev  \
                       libglm-dev  \
                       libssl-dev  \
                       libwxgtk3.0-dev  \
                       wget  \
                       curl  \
                       libcurl4-gnutls-dev  \
                       # libcurl4-openssl-dev  \
                       libboost-all-dev  \
                       python-dev  \
                       python-wxgtk3.0-dev  \
                       swig

COPY kicad-4.0.7/ /kicad-4.0.7/

WORKDIR /kicad-4.0.7/build/release

RUN bzr whoami "Josh <jsreid13@gmail.com>"

RUN cmake -W -Wno-deprecated -Werror=deprecated -Wno-error=deprecated -Wno-dev -DCMAKE_BUILD_TYPE=Release ../../

RUN make -is -j4

RUN make install -is -j4

RUN apt-get install libcanberra-gtk-module libcanberra-gtk3-module

# Replace 1000 with your user / group id
RUN export uid=1000 gid=1000 && \
    mkdir -p /home/developer && \
    mkdir -p /etc/sudoers.d && \
    echo "developer:x:${uid}:${gid}:Developer,,,:/home/developer:/bin/bash" >> /etc/passwd && \
    echo "developer:x:${uid}:" >> /etc/group && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/developer && \
    chmod 0440 /etc/sudoers.d/developer && \
    chown ${uid}:${gid} -R /home/developer

RUN mv pcbnew pcbnew-dir && \
    cp -r pcbnew-dir/* ./kicad

USER developer

ENV HOME /home/developer

RUN mkdir -p /home/developer/.local/share

CMD ./kicad/kicad
