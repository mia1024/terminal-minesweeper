FROM python:3.12-alpine as clean
FROM python:3.12-alpine as build

WORKDIR /minesweeper
COPY . /minesweeper
RUN pip install . --compile
WORKDIR /

COPY mineshell.py /

RUN rm -rf /media /opt /srv /var /mnt
RUN rm -rf /usr/local/share /usr/local/include 
RUN rm -rf /lib/libsqlite3.so.0.8.6  /lib/libcrypto.so.3 /lib/libssl.so.3 /lib/libapk.so.2.14.0 /lib/apk /usr/lib/krb5 /usr/lib/libkrb5.so.3.3 /usr/lib/libsqlite3.so.0.8.6

RUN rm -rf /usr/local/lib/python3.12/site-packages/p*  # pip
RUN rm -rf /usr/local/lib/python3.12/site-packages/s*  # setuptools
RUN rm -rf /usr/local/lib/python3.12/site-packages/t*  # terminal-minesweeper
RUN rm -rf /usr/local/lib/python3.12/site-packages/w*  # wheel

WORKDIR /usr/local/lib/python3.12
RUN rm -rf asyncio tkinter xml ensurepip venv idlelib json urllib __pycache__ email unittest logging

RUN rm -rf /minesweeper /usr/bin /usr/sbin /usr/share /bin/* /home /sbin /etc/ssl /etc/apk /root /etc/passwd /etc/shadow /etc/network /tmp

COPY --from=clean /bin/sh /bin/sh

# Remove layers
FROM scratch
COPY --from=build / /

USER 65534

ENV PS1="$ "
ENV PATH="/usr/local/bin"
ENV TERM="xterm-256color"

ENTRYPOINT ["/usr/local/bin/python", "mineshell.py"]
