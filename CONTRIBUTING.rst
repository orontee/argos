=====================
Contributing to Argos
=====================

One can install dependencies and configure pre-commit hooks in a
dedicated virtual Python environment using ``poetry``::

  $ poetry shell
  $ poetry install --with=dev
  $ pre-commit install

Pre-commit hooks run ``mypy`` check and make sure code is properly
formatted (using ``black`` and ``isort``).

Build and run from sources (using Flatpak)
==========================================

Clone the source repository, then build and install for current user
(You may have to install the expected runtime, but Flatpak will warn
you about that)::

  $ flatpak-builder --user --install --force-clean builddir io.github.orontee.Argos.json

Then to start the application use your desktop environment launcher,
or from a shell run::

  $ flatpak run io.github.orontee.Argos

Debugging
---------

One can run a shell in sandbox and call the application through
``pdb``::

  $ flatpak run --devel --command=sh io.github.orontee.Argos
  [📦 io.github.orontee.Argos ~]$ python3 -m pdb /app/bin/argos --debug

It's also worth reading `GTK documentation on interactive debugging
<https://docs.gtk.org/gtk3/running.html#interactive-debugging>`_.

Build DEB package
=================

To build the DEB package *for a given version*, one can build a Docker
image and export the DEB file from that image::

  $ VERSION=$(poetry version | cut -d' ' -f 2)
  $ rm -rf builddir
  $ buildah bud -t argos-build:$VERSION --build-arg VERSION=${VERSION} .
  $ podman run --rm -v ${PWD}:/opt/argos argos-build:$VERSION bash -c "cp builddir/*.deb /opt/argos"

To manually build the DEB package *for current HEAD*, first install
the dependencies listed in the `Containerfile </Containerfile>`_, then run
the following commands::

  $ VERSION=$(poetry version | cut -d' ' -f 2)
  $ mkdir builddir
  $ git archive --prefix=builddir/argos-${VERSION}/ --format=tar.gz HEAD | tar xzf -
  $ pushd builddir/argos-${VERSION} && debuild -b -tc -us -uc && popd

The corresponding DEB package is generated in the ``builddir`` directory.

Translations
============

To update translation files::

  $ rm -rf builddir
  $ meson builddir && cd builddir
  builddir$ meson compile io.github.orontee.Argos-update-po

Dependencies
============

Runtime dependencies are listed in the file
`generated-poetry-sources.json </generated-poetry-sources.json>`_. It
is generated from ``poetry``'s lock file using `flatpak-builder-tools
<https://github.com/flatpak/flatpak-builder-tools>`_.

Build dependencies are listed in the `Containerfile </Containerfile>`_.

Tests
=====

Tests are implemented using the ``unittest`` framework from the
standard library. Thus to run all tests one can execute the following
command::

  $ poetry run python -m unittest discover tests/

For coverage reporting::

  $ poetry run coverage run -m unittest discover tests/
  $ poerty run coverage report

To run tests with a specific version of Python, say 3.10::

  $ buildah bud -t argos-dev --target dev .
  $ podman run --rm --env PYTHON_VERSION=3.10 -v ${PWD}:/opt/argos argos-dev \
           bash -c 'pushd /opt/argos/ && eval "$(pyenv init -)" && pyenv install -v ${PYTHON_VERSION} && export PYENV_VERSION=${PYTHON_VERSION} && poetry env use ${PYENV_VERSION} && poetry install --no-interaction --with=dev && poetry run python3 -m unittest discover tests/'

Architecture
============

Part of the architecture is documented using `Structurizr DSL
<https://github.com/structurizr/dsl/>`_ and adopt `C4 model
<https://c4model.com/>`_ for visualizing software architecture.

More details here: `Architecture </docs/architecture.rst>`_.

Updating architecture diagrams
------------------------------

To validate, export, etc. files using `Structurizr DSL
<https://github.com/structurizr/dsl/>`_, one must uses the
`Structurizr CLI <https://github.com/structurizr/cli/>`_. For example,
to export to SVG format (with Graphviz installed)::

  pushd docs
  podman pull --quiet structurizr/cli:latest
  podman run -it --rm -v $PWD:/usr/local/structurizr structurizr/cli export -workspace workspace.dsl -format dot
  for DOT_FILE in *.dot; do dot -Tsvg ${DOT_FILE} -o $(basename ${DOT_FILE} .dot | cut -d'-' -f2-).svg; done

Screenshots
===========

Since Argos is distributed through Flathub some restrictions apply to
screenshots (size, ratio, padding, etc.). The build will check those
restrictions for the URLs in the screenshots section of the `AppStream
metadata file <../data/io.github.orontee.Argos.appdata.xml.in>`_.

Thus one must push new image to a dedicated branch, update the URLs,
and build for new images to be checked.

To remove horizontal padding and resize to 900px width with
`ImageMagick <https://imagemagick.org/index.php>`_ installed::

  mkdir docs/cleaned_image
  pushd docs/cleaned_image
  for IMG_FILE in ../*.png; do
    convert ${IMG_FILE} -fuzz 1% -trim +repage -resize 900\> $(basename ${IMG_FILE});
  done
