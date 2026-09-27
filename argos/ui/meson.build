fs = import('fs')

package_version = meson.project_version()
git = find_program('git', required : false)
if git.found() and fs.exists(meson.project_source_root() / '.git')
  on_tag = run_command(
    git, 'describe', '--tags', '--exact-match',
    check : false
  )
  if on_tag.returncode() != 0
    rev = run_command(
      git, 'rev-parse', '--short', 'HEAD',
      check: false
    )
    if rev.returncode() == 0
      package_version = '@0@ (@1@)'.format(package_version,
                                          rev.stdout().strip())
    endif
  endif
endif
conf = configuration_data()
conf.set('package_version', package_version)
conf.set('application_id', 'io.github.orontee.Argos')

about_ui = configure_file(
  input: 'about.ui.in',
  output: 'about.ui',
  configuration: conf
)
