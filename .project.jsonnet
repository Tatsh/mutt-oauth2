local project_name = 'mutt-oauth2';
local date_released = '2024-11-30';
local version = '0.0.2';

local authors = ['Andrew Udvare <audvare@gmail.com>'];
local citation_authors = [
  {
    'family-names': 'Udvare',
    'given-names': 'Andrew',
  },
];
local description = 'Packaged, maintained version of contributed mutt_oauth2.py script.';
local directory_name = project_name;
local documentation_uri = 'https://%s.readthedocs.org' % project_name;
local github_username = 'Tatsh';
local github_funding = {
  custom: null,
  github: github_username,
  ko_fi: 'tatsh2',
  liberapay: 'tatsh2',
  patreon: 'tatsh2',
};
local github_theme = 'jekyll-theme-hacker';
local keywords = ['email', 'gmail', 'mutt', 'outlook'];
local license = 'MIT';
local module_name = std.strReplace(project_name, '-', '_');
local repository_name = project_name;
local repository_uri = 'https://github.com/%s/%s' % [github_username, project_name];

local min_python_minor_version = '10';
local supported_python_versions = [('3.%s' % i) for i in [min_python_minor_version, 11, 12, 13]];
local yarn_version = '4.5.0';

local shared_ignore = [
  '*~',
  '.*_cache/',
  '.coverage',
  '.directory',
  '.pnp.*',
  '/.yarn/install-state.gz',
  '/dist/',
  '__pycache__/',
  'htmlcov/',
  'node_modules/',
];

local manifestToml(value) =
  std.manifestTomlEx(value, '');

local manifestIgnore(value) =
  std.join('\n', std.uniq(std.sort(value + shared_ignore)));

local manifestLines(value) =
  std.join('\n', std.uniq(std.sort(value)));

local manifestYaml(value) =
  std.manifestYamlDoc(value, true, false);

{
  '.gitattributes': manifestLines([
    '*.lock binary',
    '/.yarn/**/*.cjs',
  ]),
  '.github/FUNDING.yml': manifestYaml(github_funding),
  '.github/dependabot.yml': manifestYaml({
    updates: [
      {
        directory: '/',
        'package-ecosystem': 'npm',
        schedule: {
          interval: 'weekly',
        },
      },
      {
        directory: '/',
        'package-ecosystem': 'pip',
        schedule: {
          interval: 'weekly',
        },
      },
    ],
    version: 2,
  }),
  '.github/workflows/close-inactive.yml': manifestYaml({
    name: 'Close inactive issues',
    on: {
      schedule: [
        {
          cron: '30 1 * * *',
        },
      ],
    },
    jobs: {
      'close-issues': {
        'runs-on': 'ubuntu-latest',
        permissions: {
          issues: 'write',
          'pull-requests': 'write',
        },
        steps: [
          {
            uses: 'actions/stale@v5',
            with: {
              'days-before-issue-stale': 30,
              'days-before-issue-close': 14,
              'stale-issue-label': 'stale',
              'stale-issue-message': 'This issue is stale because it has been open for 30 days with no activity.',
              'close-issue-message': 'This issue was closed because it has been inactive for 14 days since being marked as stale.',
              'days-before-pr-stale': -1,
              'days-before-pr-close': -1,
              'repo-token': '${{ secrets.GITHUB_TOKEN }}',
            },
          },
        ],
      },
    },
  }),
  '.github/workflows/qa.yml': manifestYaml({
    jobs: {
      build: {
        'runs-on': 'ubuntu-latest',
        steps: [
          {
            uses: 'actions/checkout@v3',
          },
          {
            name: 'Install Poetry',
            run: 'pipx install poetry',
          },
          {
            name: 'Set up Python ${{ matrix.python-version }}',
            uses: 'actions/setup-python@v4',
            with: {
              cache: 'poetry',
              'python-version': '${{ matrix.python-version }}',
            },
          },
          {
            name: 'Install dependencies (Poetry)',
            run: 'poetry install --with=dev,tests',
          },
          {
            name: 'Install dependencies (Yarn)',
            run: 'yarn',
          },
          {
            name: 'Lint with mypy',
            run: 'yarn mypy .',
          },
          {
            name: 'Lint with Ruff',
            run: 'yarn ruff .',
          },
          {
            name: 'Check formatting',
            run: 'yarn check-formatting',
          },
          {
            name: 'Check spelling',
            run: 'yarn check-spelling',
          },
        ],
        strategy: {
          matrix: {
            'python-version': supported_python_versions,
          },
        },
      },
    },
    name: 'QA',
    on: {
      pull_request: {
        branches: [
          'master',
        ],
      },
      push: {
        branches: [
          'master',
        ],
      },
    },
  }),
  '.github/workflows/tests.yml': manifestYaml({
    jobs: {
      test: {
        env: {
          GITHUB_TOKEN: '${{ secrets.GITHUB_TOKEN }}',
        },
        'runs-on': 'ubuntu-latest',
        steps: [
          {
            uses: 'actions/checkout@v3',
          },
          {
            name: 'Install Poetry',
            run: 'pipx install poetry',
          },
          {
            name: 'Set up Python ${{ matrix.python-version }}',
            uses: 'actions/setup-python@v4',
            with: {
              cache: 'poetry',
              'python-version': '${{ matrix.python-version }}',
            },
          },
          {
            name: 'Install dependencies (Poetry)',
            run: 'poetry install --with=tests --all-extras',
          },
          {
            name: 'Install dependencies (Yarn)',
            run: 'yarn',
          },
          {
            name: 'Run tests',
            run: 'yarn test --cov=. --cov-branch',
          },
          {
            'if': 'matrix.python-version == 3.12',
            name: 'Coveralls',
            run: 'poetry run coveralls --service=github',
          },
        ],
        strategy: {
          matrix: {
            'python-version': [
              '3.12',
              '3.13',
            ],
          },
        },
      },
    },
    name: 'Tests',
    on: {
      pull_request: {
        branches: [
          'master',
        ],
      },
      push: {
        branches: [
          'master',
        ],
      },
    },
  }),
  '.gitignore': manifestIgnore([]),
  '.pre-commit-config.yaml': manifestYaml({
    default_install_hook_types: [
      'pre-commit',
      'pre-push',
      'post-checkout',
      'post-merge',
    ],
    repos: [
      {
        hooks: [
          {
            exclude: 'yarn-\\d+.*\\.cjs$',
            id: 'check-added-large-files',
          },
          {
            id: 'check-ast',
          },
          {
            id: 'check-builtin-literals',
          },
          {
            id: 'check-case-conflict',
          },
          {
            id: 'check-executables-have-shebangs',
          },
          {
            id: 'check-merge-conflict',
          },
          {
            id: 'check-shebang-scripts-are-executable',
          },
          {
            id: 'check-symlinks',
          },
          {
            id: 'check-toml',
          },
          {
            id: 'debug-statements',
          },
          {
            id: 'destroyed-symlinks',
          },
          {
            id: 'detect-aws-credentials',
          },
          {
            id: 'detect-private-key',
          },
          {
            id: 'end-of-file-fixer',
          },
          {
            files: '^(\\.(docker|eslint|prettier)ignore|CODEOWNERS|\\.gitattributes)$',
            id: 'file-contents-sorter',
          },
          {
            id: 'fix-byte-order-marker',
          },
          {
            id: 'mixed-line-ending',
          },
        ],
        repo: 'https://github.com/pre-commit/pre-commit-hooks',
        rev: 'v4.6.0',
      },
      {
        hooks: [
          {
            id: 'poetry-check',
            stages: [
              'pre-push',
            ],
          },
          {
            args: [
              '--no-update',
            ],
            id: 'poetry-lock',
            stages: [
              'pre-push',
            ],
          },
          {
            args: [
              '--all-extras',
              '--sync',
              '--with=dev,docs,tests',
            ],
            id: 'poetry-install',
          },
        ],
        repo: 'https://github.com/python-poetry/poetry',
        rev: '1.8.0',
      },
      {
        hooks: [
          {
            id: 'yapf',
            name: 'check Python files are formatted',
          },
        ],
        repo: 'https://github.com/google/yapf',
        rev: 'v0.40.2',
      },
      {
        hooks: [
          {
            id: 'check-github-actions',
          },
          {
            id: 'check-github-workflows',
          },
          {
            args: [
              '--schemafile',
              'https://json.schemastore.org/package.json',
            ],
            files: '^package\\.json$',
            id: 'check-jsonschema',
            name: 'validate package.json',
          },
        ],
        repo: 'https://github.com/python-jsonschema/check-jsonschema',
        rev: '0.28.2',
      },
      {
        hooks: [
          {
            entry: 'yarn install --check-cache --immutable',
            files: '^package\\.json$',
            id: 'yarn-check-lock',
            language: 'system',
            name: 'check yarn.lock is up-to-date',
            pass_filenames: false,
          },
          {
            always_run: true,
            entry: 'yarn install',
            id: 'yarn-install',
            language: 'system',
            name: 'ensure Node packages are installed for this branch',
            pass_filenames: false,
            stages: [
              'post-checkout',
              'post-merge',
            ],
          },
          {
            entry: 'yarn prettier -w',
            exclude: '((requirements|robots).txt|Dockerfile.*|..*ignore|.(coveragerc|gitattributes)|.*.(csv|lock|resource|robot)|CODEOWNERS|py.typed)$',
            exclude_types: [
              'binary',
              'dockerfile',
              'pyi',
              'python',
              'rst',
              'plain-text',
              'shell',
            ],
            id: 'fix-formatting-prettier',
            language: 'system',
            name: 'check files are formatted with Prettier',
          },
          {
            entry: 'poetry run ruff check --fix --exit-non-zero-on-fix',
            id: 'fix-ruff',
            language: 'system',
            name: 'check Python files have Ruff fixes applied',
            require_serial: true,
            types_or: [
              'python',
              'pyi',
            ],
          },
          {
            entry: "yarn markdownlint-cli2 --fix '#node_modules'",
            id: 'fix-formatting-markdown',
            language: 'system',
            name: 'check Markdown files are formatted',
            types_or: [
              'markdown',
            ],
          },
        ],
        repo: 'local',
      },
    ],
  }),
  '.prettierignore': manifestIgnore(['*.jsonnet', '/.yarn/**/*.cjs']),
  '.vscode/extensions.json': std.manifestJson({
    recommendations: [
      'aaron-bond.better-comments',
      'davidanson.vscode-markdownlint',
      'eeyore.yapf',
      'pascalreitermann93.vscode-yaml-sort',
      'redhat.vscode-xml',
      'redhat.vscode-yaml',
    ],
  }),
  '.vscode/launch.json': std.manifestJson({
    configurations: [
      {
        args: ['-x'],
        autoReload: {
          enable: true,
        },
        console: 'integratedTerminal',
        env: {
          _PYTEST_RAISE: '1',
        },
        justMyCode: false,
        module: 'pytest',
        name: 'Run tests',
        request: 'launch',
        type: 'debugpy',
      },
    ],
    inputs: [],
    version: '0.2.0',
  }),
  '.vscode/settings.json': std.manifestJson({
    '[python]': {
      'editor.defaultFormatter': 'eeyore.yapf',
      'editor.formatOnSaveMode': 'file',
      'editor.tabSize': 4,
    },
    'cSpell.enabled': true,
    'editor.formatOnPaste': true,
    'editor.formatOnSave': true,
    'editor.formatOnType': true,
    'editor.insertSpaces': true,
    'editor.tabSize': 2,
    'files.eol': '\n',
    'python.analysis.autoImportCompletions': true,
    'python.analysis.completeFunctionParens': true,
    'python.analysis.importFormat': 'relative',
    'python.analysis.indexing': true,
    'python.analysis.inlayHints.callArgumentNames': 'all',
    'python.analysis.inlayHints.functionReturnTypes': true,
    'python.analysis.inlayHints.pytestParameters': true,
    'python.analysis.inlayHints.variableTypes': true,
    'python.analysis.packageIndexDepths': [
      {
        depth: 100,
        name: '',
      },
    ],
    'python.languageServer': 'Pylance',
    'python.testing.pytestArgs': [
      'tests',
    ],
    'python.testing.pytestEnabled': true,
  }),
  '.yarnrc.yml': manifestYaml({
    enableTelemetry: false,
    nodeLinker: 'node-modules',
    plugins: [
      {
        path: '.yarn/plugins/@yarnpkg/plugin-prettier-after-all-installed.cjs',
      },
    ],
    yarnPath: '.yarn/releases/yarn-%s.cjs' % yarn_version,
  }),
  'CITATION.cff': manifestYaml({
    'cff-version': '1.2.0',
    'date-released': date_released,
    authors: citation_authors,
    message: 'If you use this software, please cite it as below.',
    title: project_name,
    version: version,
  }),
  '_config.yml': manifestYaml({ theme: github_theme }),
  'package.json': std.manifestJson({
    contributors: authors,
    cspell: {
      dictionaryDefinitions: [
        {
          name: 'main',
          path: '.vscode/dictionary.txt',
        },
      ],
      enableGlobDot: true,
      enabledLanguageIds: [
        'git-commit',
        'ignore',
        'jinja',
        'json',
        'jsonc',
        'markdown',
        'plaintext',
        'python',
        'restructuredtext',
        'text',
        'toml',
        'yaml',
        'yml',
      ],
      ignorePaths: [
        '*.har',
        '*.log',
        '.coverage',
        '.directory',
        '.doctrees',
        '.git',
        '.vscode/extensions.json',
        '.yarn/**/*.cjs',
        '__pycache__',
        '_build/**',
        'build/**',
        'dist/**',
        'docs/_build/**',
        'htmlcov/**',
        'man/**',
        'node_modules/**',
      ],
      language: 'en-GB',
      languageSettings: [
        {
          dictionaries: [
            'main',
          ],
          languageId: '*',
        },
      ],
    },
    devDependencies: {
      '@prettier/plugin-xml': '^3.4.1',
      cspell: '^8.16.0',
      'markdownlint-cli2': '^0.15.0',
      prettier: '^3.4.1',
      'prettier-plugin-ini': '^1.3.0',
      'prettier-plugin-sort-json': '^4.0.0',
      'prettier-plugin-toml': '^2.0.1',
      pyright: '^1.1.389',
      'yarn-audit-fix': '^10.1.0',
    },
    homepage: repository_uri,
    keywords: keywords,
    'markdownlint-cli2': {
      config: {
        MD033: {
          allowed_elements: ['kbd'],
        },
        default: true,
        'line-length': {
          code_blocks: false,
          line_length: 100,
        },
      },
    },
    prettier: {
      endOfLine: 'lf',
      iniSpaceAroundEquals: true,
      jsonRecursiveSort: true,
      overrides: [
        {
          files: ['package.json'],
          options: {
            parser: 'json',
          },
        },
      ],
      plugins: [
        '@prettier/plugin-xml',
        'prettier-plugin-ini',
        'prettier-plugin-sort-json',
        'prettier-plugin-toml',
      ],
      reorderKeys: true,
      printWidth: 100,
      singleQuote: true,
    },
    license: license,
    name: project_name,
    packageManager: 'yarn@%s' % yarn_version,
    repository: {
      type: 'git',
      url: 'git@github.com:%s/%s.git' % [github_username, project_name],
    },
    scripts: {
      'check-formatting': "prettier -c './**/*.cff' './**/*.json' './**/*.md' './**/*.toml' './**/*.y*ml' && poetry run yapf -rd .",
      'check-spelling': "cspell --no-progress './**/*'  './**/.*'",
      format: "prettier -w './**/*.cff' './**/*.json' './**/*.md' './**/*.toml' './**/*.y*ml' && poetry run yapf -ri .",
      mypy: 'poetry run mypy',
      qa: 'yarn mypy . && yarn ruff . && yarn check-spelling && yarn check-formatting',
      ruff: 'poetry run ruff check --fix',
      'ruff:fix': 'poetry run ruff check --fix',
      test: 'poetry run pytest',
    },
    version: version,
  }),
  'pyproject.toml': manifestToml({
    tool: {
      poetry: {
        name: project_name,
        version: version,
        authors: authors,
        classifiers: std.sort([
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Typing :: Typed',
        ] + [('Programming Language :: Python :: %s' % i) for i in supported_python_versions]),
        description: description,
        documentation: documentation_uri,
        homepage: repository_uri,
        keywords: keywords,
        license: license,
        packages: [
          {
            include: module_name,
          },
        ],
        readme: 'README.md',
        repository: repository_uri,
        urls: {
          Issues: '%s/issues' % repository_uri,
        },
        dependencies: {
          python: '>=3.%s,<4' % min_python_minor_version,
          click: '^8.1.7',
          keyring: '^25.5.0',
          requests: '^2.32.3',
        },
        group: {
          dev: {
            optional: true,
            dependencies: {
              commitizen: '^4.0.0',
              mypy: '^1.13.0',
              ruff: '^0.8.0',
              'types-requests': '^2.32.0.20241016',
              yapf: '^0.43.0',
            },
          },
          docs: {
            optional: true,
            dependencies: {
              doc8: '^1.1.2',
              docutils: '^0.21.2',
              esbonio: '^0.16.5',
              'restructuredtext-lint': '^1.4.0',
              sphinx: '^8.1.3',
              'sphinx-click': '^6.0.0',
              tomlkit: '^0.13.2',
            },
          },
          tests: {
            optional: true,
            dependencies: {
              coveralls: '^3.3.1',
              mock: '^5.1.0',
              pytest: '^8.3.3',
              'pytest-cov': '^5.0.0',
              'pytest-mock': '^3.14.0',
              'requests-mock': '^1.12.1',
            },
          },
        },
        scripts: {
          'mutt-oauth2': '%s.main:main' % module_name,
        },
      },
      commitizen: {
        tag_format: 'v$version',
        version_files: [
          '.project.jsonnet',
          'CITATION.cff',
          'README.md',
          '%s/__init__.py' % module_name,
          'package.json',
        ],
        version_provider: 'poetry',
      },
      coverage: {
        report: {
          omit: [
            'tests/conftest.py',
            'tests/test_*.py',
          ],
          show_missing: true,
        },
        run: {
          branch: true,
          omit: [
            'tests/conftest.py',
            'tests/test_*.py',
          ],
        },
      },
      doc8: {
        'max-line-length': 100,
      },
      mypy: {
        cache_dir: '~/.cache/mypy',
        explicit_package_bases: true,
        platform: 'linux',
        python_version: '3.%s' % min_python_minor_version,
        show_column_numbers: true,
        strict: true,
        strict_optional: true,
        warn_unreachable: true,
      },
      pytest: {
        ini_options: {
          mock_use_standalone_module: true,
          norecursedirs: [
            'node_modules',
          ],
          python_files: [
            'test_*.py',
            '*_tests.py',
          ],
          testpaths: [
            'tests',
          ],
        },
      },
      pyright: {
        deprecateTypingAliases: true,
        enableExperimentalFeatures: true,
        include: [
          './%s' % module_name,
          './tests',
        ],
        pythonPlatform: 'Linux',
        pythonVersion: '3.%s' % min_python_minor_version,
        reportCallInDefaultInitializer: 'warning',
        reportImplicitOverride: 'warning',
        reportImportCycles: 'error',
        reportMissingModuleSource: 'error',
        reportPropertyTypeMismatch: 'error',
        reportShadowedImports: 'error',
        reportUnnecessaryTypeIgnoreComment: 'none',
        typeCheckingMode: 'off',
        useLibraryCodeForTypes: false,
      },
      ruff: {
        'cache-dir': '~/.cache/ruff',
        'extend-exclude': [],
        'force-exclude': true,
        'line-length': 100,
        'namespace-packages': [
          'docs',
          'tests',
        ],
        'target-version': 'py3%s' % min_python_minor_version,
        'unsafe-fixes': true,
        lint: {
          'extend-select': [
            'A',
            'AIR',
            'ANN',
            'ARG',
            'ASYNC',
            'B',
            'BLE',
            'C4',
            'C90',
            'COM',
            'CPY',
            'D',
            'DJ',
            'DTZ',
            'E',
            'EM',
            'ERA',
            'EXE',
            'F',
            'FA',
            'FBT',
            'FIX',
            'FLY',
            'FURB',
            'G',
            'I',
            'ICN',
            'INP',
            'INT',
            'ISC',
            'LOG',
            'N',
            'NPY',
            'PD',
            'PERF',
            'PGH',
            'PIE',
            'PL',
            'PT',
            'PTH',
            'PYI',
            'Q',
            'RET',
            'RSE',
            'RUF',
            'S',
            'SIM',
            'SLF',
            'SLOT',
            'T10',
            'T20',
            'TCH',
            'TD',
            'TID',
            'TRY',
            'UP',
            'YTT',
          ],
          ignore: [
            'A005',
            'ANN401',
            'ARG001',
            'ARG002',
            'ARG004',
            'C901',
            'COM812',
            'CPY001',
            'D100',
            'D101',
            'D102',
            'D103',
            'D104',
            'D105',
            'D106',
            'D107',
            'D203',
            'D204',
            'D212',
            'EM101',
            'N818',
            'PLR0912',
            'PLR0913',
            'PLR0914',
            'PLR0915',
            'PLR0917',
            'PLR1702',
            'PLR6301',
            'S101',
            'S404',
            'S603',
            'TD002',
            'TD003',
            'TD004',
          ],
          preview: true,
          'flake8-quotes': {
            'inline-quotes': 'single',
            'multiline-quotes': 'double',
          },
          isort: {
            'case-sensitive': true,
            'combine-as-imports': true,
            'from-first': true,
          },
          'pep8-naming': {
            'extend-ignore-names': [
              'test_*',
            ],
          },
          pydocstyle: {
            convention: 'numpy',
          },
        },
      },
      yapf: {
        align_closing_bracket_with_visual_indent: true,
        allow_multiline_dictionary_keys: false,
        allow_multiline_lambdas: false,
        allow_split_before_dict_value: true,
        blank_line_before_class_docstring: false,
        blank_line_before_module_docstring: false,
        blank_line_before_nested_class_or_def: false,
        blank_lines_around_top_level_definition: 2,
        coalesce_brackets: true,
        column_limit: 100,
        continuation_align_style: 'SPACE',
        continuation_indent_width: 4,
        dedent_closing_brackets: false,
        disable_ending_comma_heuristic: false,
        each_dict_entry_on_separate_line: true,
        indent_dictionary_value: true,
        indent_width: 4,
        join_multiple_lines: true,
        no_spaces_around_selected_binary_operators: false,
        space_between_ending_comma_and_closing_bracket: false,
        spaces_around_default_or_named_assign: false,
        spaces_around_power_operator: true,
        spaces_before_comment: 2,
        split_all_comma_separated_values: false,
        split_arguments_when_comma_terminated: false,
        split_before_bitwise_operator: true,
        split_before_closing_bracket: true,
        split_before_dict_set_generator: true,
        split_before_dot: false,
        split_before_expression_after_opening_paren: false,
        split_before_first_argument: false,
        split_before_logical_operator: true,
        split_before_named_assigns: true,
        split_complex_comprehension: false,
        split_penalty_after_opening_bracket: 30,
        split_penalty_after_unary_operator: 10000,
        split_penalty_before_if_expr: 0,
        split_penalty_bitwise_operator: 300,
        split_penalty_comprehension: 80,
        split_penalty_excess_character: 7000,
        split_penalty_for_added_line_split: 30,
        split_penalty_import_names: 0,
        split_penalty_logical_operator: 300,
        use_tabs: false,
      },
      yapfignore: {
        ignore_patterns: [
          'node_modules/**',
        ],
      },
    },
    'build-system': {
      requires: [
        'poetry-core',
      ],
      'build-backend': 'poetry.core.masonry.api',
    },
  }),
}
