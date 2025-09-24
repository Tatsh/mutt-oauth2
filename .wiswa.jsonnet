local utils = import 'utils.libjsonnet';

{
  description: 'Packaged, maintained version of contributed mutt_oauth2.py script.',
  keywords: ['email', 'gmail', 'mutt', 'outlook'],
  project_name: 'mutt-oauth2',
  version: '0.1.1',
  want_main: true,
  copilot+: {
    intro: 'mutt-oauth2 is a script that helps users authenticate their email accounts using OAuth2 in the Mutt email client.',
  },
  pyproject+: {
    tool+: {
      poetry+: {
        dependencies+: {
          click: utils.latestPypiPackageVersionCaret('click'),
          keyring: utils.latestPypiPackageVersionCaret('keyring'),
          requests: utils.latestPypiPackageVersionCaret('requests'),
        },
        group+: {
          dev+: {
            dependencies+: {
              'types-requests': utils.latestPypiPackageVersionCaret('types-requests'),
            },
          },
        },
      },
    },
  },
}
