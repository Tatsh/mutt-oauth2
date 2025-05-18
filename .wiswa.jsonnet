local utils = import 'utils.libjsonnet';

local utils = import 'utils.libjsonnet';

(import 'defaults.libjsonnet') + {
  // Project-specific
  description: 'Packaged, maintained version of contributed mutt_oauth2.py script.',
  keywords: ['email', 'gmail', 'mutt', 'outlook'],
  project_name: 'mutt-oauth2',
  version: '0.0.3',
  want_main: true,
  citation+: {
    'date-released': '2025-04-09',
  },
  pyproject+: {
    tool+: {
      poetry+: {
        dependencies+: {
          click: '^8.1.8',
          keyring: '^25.5.0',
          requests: '^2.32.3',
        },
        group+: {
          dev+: {
            dependencies+: {
              'types-requests': '^2.32.0.20250328',
            },
          },
        },
      },
    },
  },
  // Common
  authors: [
    {
      'family-names': 'Udvare',
      'given-names': 'Andrew',
      email: 'audvare@gmail.com',
      name: '%s %s' % [self['given-names'], self['family-names']],
    },
  ],
  local funding_name = '%s2' % std.asciiLower(self.github_username),
  github_username: 'Tatsh',
  github+: {
    funding+: {
      ko_fi: funding_name,
      liberapay: funding_name,
      patreon: funding_name,
    },
  },
  mastodon_id: '109370961877277568',
}
