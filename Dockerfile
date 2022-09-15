FROM python:3.10-alpine as build

WORKDIR /minesweeper
COPY . /minesweeper
RUN pip install . --compile
WORKDIR /

COPY mineshell.py /

RUN rm -rf /media /opt /srv /var
RUN rm -rf /usr/local/lib/python3.10/site-packages/p*  # pip
RUN rm -rf /usr/local/lib/python3.10/site-packages/s*  # setuptools
RUN rm -rf /usr/local/lib/python3.10/site-packages/t*  # terminal-minesweeper
RUN rm -rf /usr/local/lib/python3.10/site-packages/w*  # wheel
RUN rm -rf /minesweeper /usr/bin /usr/sbin /usr/share /bin/* /home /sbin /etc/ssl /etc/apk /root /etc/passwd /etc/shadow /etc/network /tmp

# Remove layers
FROM scratch
COPY --from=build / /

USER 65534

ENV PS1="$ "
ENV PATH="/usr/local/bin"
ENV TERM="xterm-256color"

ENTRYPOINT ["/usr/local/bin/python", "mineshell.py"]
