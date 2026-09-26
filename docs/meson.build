rst2man = find_program('rst2man', 'rst2man.py', required: false)
if rst2man.found()
  custom_target('manpage',
    input: 'argos.1.rst',
    output: 'argos.1',
    command: [rst2man, '@INPUT@', '@OUTPUT@'],
    install: true,
    install_dir: get_option('mandir') / 'man1',
  )
endif
