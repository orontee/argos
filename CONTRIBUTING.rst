=======================
 Contributing to Argos
=======================

One can install dependencies and configure pre-commit hooks in a
dedicated virtual Python environment using ``poetry``::

  $ poetry env activate
  $ poetry install --with=dev
  $ poetry run pre-commit install

Pre-commit hooks run ``mypy`` check and make sure code is properly
formatted (using ``black`` and ``isort``).

Build and run from sources
==========================

The `Meson Build System <https://mesonbuild.com>`_ is configured to
build, install, manage translations, and run tests.

Setup the ``builddir`` build directory::

  $ poetry run meson setup --wipe --prefix="${PWD}/install" builddir

Then run the application with::

  $ poetry run meson compile -c builddir
  $ poetry run meson install -c builddir
  $ PYTHONPATH="${PWD}/install/share/argos:${PYTHONPATH}" \
       poetry run install/bin/argos


Using Flatpak
~~~~~~~~~~~~~

Build and install for current user with::

  $ flatpak-builder --user --install --force-clean builddir io.github.orontee.Argos.json

You may have to install the expected runtime, but Flatpak will warn
you about that.

Then to start the application use your desktop environment launcher,
or from a shell run::

  $ flatpak run io.github.orontee.Argos

Note that the Python interpreter of the Flatpak environment is CPython
3.10.

To debug when using Flatpak, one can run a shell in sandbox and call
the application through ``pdb``::

  $ flatpak run --devel --command=sh io.github.orontee.Argos
  [📦 io.github.orontee.Argos ~]$ G_MESSAGES_DEBUG=all python3 -m pdb /app/bin/argos --debug

It's also worth reading `GTK documentation on interactive debugging
<https://docs.gtk.org/gtk3/running.html#interactive-debugging>`_.

Dependencies
============

Python runtime dependencies can be added using ``poetry add``. Once
the code is ready, one must update the file used respectively
Flatpak packaging.

Flatpak builder install runtime dependencies described in the file
`pypi-dependencies.yaml </pypi-dependencies.yaml>`_.

It can be updated from poetry lock file in two steps using
`flatpak-builder-tools
<https://github.com/flatpak/flatpak-builder-tools>`_::

  $ poetry run pip freeze > requirements.txt
  $ flatpak-pip-generator --runtime=org.gnome.Sdk//49 \
                          --requirements-file=requirements.txt \
                          --yaml --output=pypi-dependencies

Note that one may have to reorder dependencies and switch to
different sources depending on what is available in the runtime to
build packages.

Build dependencies are listed in the `Containerfile </Containerfile>`_.

Dependencies are locked from Poetry point of view. In order to list
possible dependencies updates run ``poetry show --latest
--top-level``.

Tests
=====

Run checks for metadata validity and unit tests through::

  $ poetry run meson setup --wipe builddir
  $ poetry run meson test --verbose -C builddir

Unit tests are implemented using the ``unittest`` framework from the
standard library.

For coverage reporting::

  $ poetry run coverage run -m unittest discover tests/
  $ poetry run coverage report

To run tests with a specific version of Python, say 3.11::

  $ buildah bud -t argos-dev --target dev .
  $ podman run --rm --env PYTHON_VERSION=3.11 -v ${PWD}:/opt/argos argos-dev \
       bash -c 'pushd /opt/argos/ &&
                eval "$(pyenv init -)" &&
                pyenv install -v ${PYTHON_VERSION} &&
                export PYENV_VERSION=${PYTHON_VERSION} &&
                poetry env use ${PYENV_VERSION} &&
                poetry install --no-interaction --with=dev &&
                poetry run meson setup builddir --wipe &&
                poetry run meson test --verbose -C builddir'


Checks for metadata validity are also provided through::

  $ poetry run meson setup builddir
  $ poetry run meson test --verbose -C builddir

Release
=======

First, prepare the release with::

  $ poetry run ./scripts/release-version

Review, complete or update the suggested changes carefully; Make sure
translations and screenshots are up-to-date. Commit, tag and push with::

  $ git commit -a -m "Update to version $(poetry version --short)"
  $ git tag $(poetry version --short)
  $ git push origin; git push --tags origin

Use ``flatpak-builder`` to build locally.

Make a pull request to the technical repository
`flathub/io.github.orontee.Argos
<https://github.com/flathub/io.github.orontee.Argos>`_ to publish the
release through Flathub.

Update the Git repository underlying the dedicated `AUR package
<https://aur.archlinux.org/packages/argos>`_.

Finally, run the following command to commit version bump for next
release::

  $ poetry run ./scripts/prepare-next-release

Architecture
============

Part of the architecture is documented using `Structurizr DSL
<https://github.com/structurizr/dsl/>`_ and adopt `C4 model
<https://c4model.com/>`_ for visualizing software architecture.

More details here: `Architecture </docs/architecture.rst>`_.

Updating architecture diagrams
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To validate, export, etc. files using `Structurizr DSL
<https://github.com/structurizr/dsl/>`_, one must uses the
`Structurizr CLI <https://github.com/structurizr/cli/>`_. For example,
to export to SVG format (with Graphviz installed)::

  $ pushd docs
  $ podman pull --quiet structurizr/cli:latest
  $ podman run -it --rm -v $PWD:/usr/local/structurizr \
               structurizr/cli \
               export -workspace workspace.dsl -format dot
  $ for DOT_FILE in *.dot; do \
      dot -Tsvg ${DOT_FILE} -o \
          $(basename ${DOT_FILE} .dot \
          | cut -d'-' -f2-).svg; \
    done

Screenshots
===========

Since Argos is distributed through Debian, its content must respect
the `Debian Social Contract
<https://www.debian.org/social_contract>`_, screenshots included: Make
sure that the album art visible in screenshots is under `CC BY-SA
<https://creativecommons.org/licenses/by-sa/4.0/>`_.

To this end, a fake music library is provided under
``/tests/data/fake-music-library``; All image files in that library are
under `CC BY-SA
<https://creativecommons.org/licenses/by-sa/4.0/>`_.

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
    convert ${IMG_FILE} -trim +repage -resize 900\> $(basename ${IMG_FILE});
  done
