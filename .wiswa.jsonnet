local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  description: 'Packaged, maintained version of contributed mutt_oauth2.py script.',
  keywords: ['email', 'gmail', 'mutt', 'outlook'],
  project_name: 'mutt-oauth2',
  version: '0.2.0',
  want_main: true,
  want_flatpak: true,
  publishing+: { flathub: 'sh.tat.mutt-oauth2' },
  security_policy_supported_versions: { '0.2.x': ':white_check_mark:' },
  pyproject+: {
    tool+: {
      pytest+: {
        ini_options+: {
          asyncio_mode: 'auto',
        },
      },
      ruff+: {
        lint+: {
          'per-file-ignores'+: {
            'tests/**'+: ['RUF029'],
          },
        },
      },
      poetry+: {
        dependencies+: {
          aioimaplib: utils.latestPypiPackageVersionCaret('aioimaplib'),
          aiosmtplib: utils.latestPypiPackageVersionCaret('aiosmtplib'),
          anyio: utils.latestPypiPackageVersionCaret('anyio'),
          click: utils.latestPypiPackageVersionCaret('click'),
          keyring: utils.latestPypiPackageVersionCaret('keyring'),
          niquests: utils.latestPypiPackageVersionCaret('niquests'),
        },
        group+: {
          tests+: {
            dependencies+: {
              'pytest-asyncio': utils.latestPypiPackageVersionCaret('pytest-asyncio'),
            },
          },
        },
      },
    },
  },
}
