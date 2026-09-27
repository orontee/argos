python = import('python')

test('Python unit tests',
     python.find_installation('python3'),
     args: ['-m', 'unittest',
            'discover', meson.current_source_dir()],
     env: ['PYTHONPATH=' + meson.project_source_root()],
     verbose: true
)
