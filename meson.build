project('argos',
          version: '1.17.0a0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')

dependency('glib-2.0', version: '>= 2.64.0')
dependency('gobject-introspection-1.0', version: '>= 1.35.0')

subdir('data')
subdir('argos')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')

run_target('prepare-next-release',
  command : 'scripts/prepare-next-release')

run_target('release-version',
  command : 'scripts/release-version')

run_target('create-github-pre-release',
  command : 'scripts/create-github-pre-release')
