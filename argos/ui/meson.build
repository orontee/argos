vcs_tag = ''
git = find_program('git', required : false)
if git.found()
  vcs_tag = run_command('git', 'rev-parse', '--short', 'HEAD').stdout().strip()
endif
if vcs_tag == ''
  vcs_tag = 'devel'
else
  vcs_tag = '@0@'.format(vcs_tag)
endif
conf = configuration_data()
conf.set('package_version', '@0@ (@1@)'.format(meson.project_version(), vcs_tag))
conf.set('application_id', 'io.github.orontee.Argos')

about_ui = configure_file(
  input: 'about.ui.in',
  output: 'about.ui',
  configuration: conf
)
