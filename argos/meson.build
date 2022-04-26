pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'argos')
gnome = import('gnome')

gnome.compile_resources('argos',
  'app.argos.Argos.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('application_id', 'app.argos.Argos')
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'argos.in',
  output: 'argos',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

argos_sources = [
  'app.py',
  'download.py',
  'http.py',
  '__init__.py',
  'message.py',
  'model.py',
  'session.py',
  'time.py',
  'utils.py',
  'window.py',
  'ws.py'
]

install_data(argos_sources, install_dir: moduledir)
install_subdir('widgets', install_dir: moduledir)
