ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY serve /usr/bin/serve
RUN chmod 777 /usr/bin/serve

ENTRYPOINT [ "/usr/bin/serve" ]