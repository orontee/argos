FROM debian:stable AS build

RUN apt-get update -y && apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        build-essential \
        cmake \
        debhelper \
        devscripts \
        fakeroot \
        git \
        lintian \
        meson \
        pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update -y && apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        libglib2.0-dev \
        libgirepository1.0-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . /src

WORKDIR /src

ARG VERSION=1.1.2
RUN mkdir builddir
RUN git archive --prefix=builddir/argos-${VERSION}/ --format=tar.gz v${VERSION} | tar xzf -
RUN cd builddir/argos-${VERSION} \
    && debuild -b -tc -us -uc
RUN ls builddir
