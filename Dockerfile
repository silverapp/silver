FROM python:2.7.11-alpine
MAINTAINER Presslabs ping@presslabs.com

# Ensure that Python outputs everything that's printed inside
# the application rather than buffering it, maily for logging purposes
ENV PYTHONUNBUFFERED 1

# Set default django settings module
ENV DJANGO_SETTINGS_MODULE settings

# silver app runs on port 8080
EXPOSE 8080

RUN set -ex && mkdir -p /silver
WORKDIR /silver

# Install silver
COPY ./requirements /silver/requirements

RUN set -ex \
    && apk update \
    && apk add --no-cache \
        mariadb-client-libs \
        libjpeg-turbo \
        jpeg \
        zlib \
        ca-certificates wget \
        openssl \
        libffi-dev \
    && apk add --no-cache --virtual .build-deps \
        build-base \
        mariadb-dev \
        jpeg-dev \
        zlib-dev \
    && update-ca-certificates \
    && pip install --no-cache-dir -r requirements/common.txt \
    && pip install --no-cache-dir gunicorn==19.4.5 \
    && pip install --no-cache-dir mysql-python \
    && apk del .build-deps \
    && wget -qO- https://github.com/jwilder/dockerize/releases/download/v0.2.0/dockerize-linux-amd64-v0.2.0.tar.gz | tar -zxf - -C /usr/bin \
    && chown root:root /usr/bin/dockerize

COPY ./ /silver

VOLUME /silver

CMD ["/docker-entrypoint"]
