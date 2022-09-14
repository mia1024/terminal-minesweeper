FROM python:3.10-alpine as build

WORKDIR /minesweeper
COPY . /minesweeper
RUN pip install . --compile
WORKDIR /
RUN rm -rf /minesweeper

COPY mineshell.py /

# Remove layers
FROM scratch
COPY --from=build / /

USER 1000

ENV PS1="$ "
ENV TERM="xterm-256color"

ENTRYPOINT ["/usr/local/bin/python", "mineshell.py"]
