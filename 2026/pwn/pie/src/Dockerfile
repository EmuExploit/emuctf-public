FROM ghcr.io/downunderctf/docker-vendor/nsjail:ubuntu-24.04

ENV JAIL_CWD=/chal
ENV PORT=9000
COPY ./nsjail.cfg /home/ctf
COPY ./flag.txt /home/ctf/chal
COPY ./chal /home/ctf/chal/pwn
