ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN python3 -m pip --no-cache-dir install pynvml==12.0.0

COPY serve /usr/bin/serve
RUN chmod 777 /usr/bin/serve

ENTRYPOINT [ "/usr/bin/serve" ]