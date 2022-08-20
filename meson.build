project('argos',
          version: '1.1.0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')

dependency('glib-2.0', version: '>= 2.66.0')
dependency('gobject-introspection-1.0', version: '>= 1.35.0')

subdir('data')
subdir('argos')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')
