FROM debian:stable AS base

RUN apt-get update -y && apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils \
    tk-dev libffi-dev liblzma-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# argos build dependencies
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

FROM base AS dev

RUN apt-get update -y && apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        python3-pip python3-venv libcairo2-dev\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -
ENV PATH="/opt/poetry/bin:$PATH"

ENV PYENV_ROOT=/opt/pyenv
RUN curl https://pyenv.run | bash
ENV PATH="/opt/pyenv/bin:$PATH"

FROM base AS build

COPY . /src

WORKDIR /src

ARG VERSION
RUN [ -n "${VERSION}" ]
RUN mkdir builddir
RUN git archive --prefix=builddir/argos-${VERSION}/ --format=tar.gz v${VERSION} | tar xzf -
RUN cd builddir/argos-${VERSION} \
    && debuild -b -tc -us -uc
RUN ls builddir
