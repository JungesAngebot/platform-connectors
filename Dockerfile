FROM python:3.5

RUN apt-get update
RUN apt-get --yes --force-yes upgrade
ADD connector /connector
ADD *.py /
ADD config /config
ADD Makefile /Makefile
ADD requirements.txt /requirements.txt
ADD entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
RUN mkdir log
RUN mkdir data

RUN ["make", "init"]
EXPOSE 5000

ENTRYPOINT [ "./entrypoint.sh" ]