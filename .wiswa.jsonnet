local utils = import 'utils.libjsonnet';

(import 'defaults.libjsonnet') + {
  local top = self,

  want_main: true,

  github_username: 'Tatsh',
  authors: [
    {
      'family-names': 'Udvare',
      'given-names': 'Andrew',
      email: 'audvare@gmail.com',
      name: '%s %s' % [self['given-names'], self['family-names']],
    },
  ],
  project_name: 'mutt-oauth2',
  version: '0.0.3',
  description: 'Packaged, maintained version of contributed mutt_oauth2.py script.',
  keywords: ['email', 'gmail', 'mutt', 'outlook'],

  github+: {
    funding: {
      custom: null,
      github: top.github_username,
      ko_fi: 'tatsh2',
      liberapay: 'tatsh2',
      patreon: 'tatsh2',
    },
    pages_uri: 'https://%s.github.io/%s/' % [std.asciiLower(top.github_username), top.project_name],
    username: top.github_username,
  },

  citation+: {
    authors: utils.citationAuthors(top.authors),
    'date-released': '2025-04-09',
  },

  pyproject+: {
    project+: {
      authors: [{ name: x.name, email: x.email } for x in top.authors],
      name: top.project_name,
      scripts: { [top.project_name]: '%s.main:main' % top.primary_module },
      version: top.version,
    },
    tool+: {
      poetry+: {
        dependencies+: {
          click: '^8.1.8',
          keyring: '^25.5.0',
          requests: '^2.32.3',
          'typing-extensions': '^4.13.1',
        },
        group+: {
          dev+: {
            dependencies+: {
              'types-requests': '^2.32.0.20250328',
            },
          },
        },
        include: ['%s-jsonnet' % top.primary_module],
        packages: [{ include: x } for x in [top.primary_module]],
      },
    },
  },
}
