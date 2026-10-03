project('argos',
          version: '1.19.5',
    meson_version: '>= 1.7.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')

subdir('data')
subdir('argos')
subdir('docs')
subdir('po')
subdir('tests')

meson.add_install_script('build-aux/meson/postinstall.py')

run_target('prepare-next-release',
  command : 'scripts/prepare-next-release')

run_target('release-version',
  command : 'scripts/release-version')

run_target('create-github-pre-release',
  command : 'scripts/create-github-pre-release')
