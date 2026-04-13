local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  description: 'Packaged, maintained version of contributed mutt_oauth2.py script.',
  keywords: ['email', 'gmail', 'mutt', 'outlook'],
  project_name: 'mutt-oauth2',
  version: '0.1.2',
  want_main: true,
  want_flatpak: true,
  publishing+: { flathub: 'sh.tat.mutt-oauth2' },
  security_policy_supported_versions: { '0.1.x': ':white_check_mark:' },
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
