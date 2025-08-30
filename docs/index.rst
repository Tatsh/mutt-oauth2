mutt-oauth2
===========

.. only:: html

   .. image:: https://img.shields.io/pypi/pyversions/mutt-oauth2.svg?color=blue&logo=python&logoColor=white
      :target: https://www.python.org/
      :alt: Python versions

   .. image:: https://img.shields.io/pypi/v/mutt-oauth2
      :target: https://pypi.org/project/mutt-oauth2/
      :alt: PyPI Version

   .. image:: https://img.shields.io/github/v/tag/Tatsh/mutt-oauth2
      :target: https://github.com/Tatsh/mutt-oauth2/tags
      :alt: GitHub tag (with filter)

   .. image:: https://img.shields.io/github/license/Tatsh/mutt-oauth2
      :target: https://github.com/Tatsh/mutt-oauth2/blob/master/LICENSE.txt
      :alt: License

   .. image:: https://img.shields.io/github/commits-since/Tatsh/mutt-oauth2/v0.1.1/master
      :target: https://github.com/Tatsh/mutt-oauth2/compare/v0.1.1...master
      :alt: GitHub commits since latest release (by SemVer including pre-releases)

   .. image:: https://github.com/Tatsh/mutt-oauth2/actions/workflows/codeql.yml/badge.svg
      :target: https://github.com/Tatsh/mutt-oauth2/actions/workflows/codeql.yml
      :alt: CodeQL

   .. image:: https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml/badge.svg
      :target: https://github.com/Tatsh/mutt-oauth2/actions/workflows/qa.yml
      :alt: QA

   .. image:: https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml/badge.svg
      :target: https://github.com/Tatsh/mutt-oauth2/actions/workflows/tests.yml
      :alt: Tests

   .. image:: https://coveralls.io/repos/github/Tatsh/mutt-oauth2/badge.svg?branch=master
      :target: https://coveralls.io/github/Tatsh/mutt-oauth2?branch=master
      :alt: Coverage Status

   .. image:: https://readthedocs.org/projects/mutt-oauth2/badge/?version=latest
      :target: https://mutt-oauth2.readthedocs.org/?badge=latest
      :alt: Documentation Status

   .. image:: https://www.mypy-lang.org/static/mypy_badge.svg
      :target: http://mypy-lang.org/
      :alt: mypy

   .. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
      :target: https://github.com/pre-commit/pre-commit
      :alt: pre-commit

   .. image:: https://img.shields.io/badge/pydocstyle-enabled-AD4CD3
      :target: http://www.pydocstyle.org/en/stable/
      :alt: pydocstyle

   .. image:: https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black
      :target: https://docs.pytest.org/en/stable/
      :alt: pytest

   .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
      :target: https://github.com/astral-sh/ruff
      :alt: Ruff

   .. image:: https://static.pepy.tech/badge/mutt-oauth2/month
      :target: https://pepy.tech/project/mutt-oauth2
      :alt: Downloads

   .. image:: https://img.shields.io/github/stars/Tatsh/mutt-oauth2?logo=github&style=flat
      :target: https://github.com/Tatsh/mutt-oauth2/stargazers
      :alt: Stargazers

   .. image:: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor%3Ddid%3Aplc%3Auq42idtvuccnmtl57nsucz72%26query%3D%24.followersCount%26style%3Dsocial%26logo%3Dbluesky%26label%3DFollow%2520%40Tatsh&query=%24.followersCount&style=social&logo=bluesky&label=Follow%20%40Tatsh
      :target: https://bsky.app/profile/Tatsh.bsky.social
      :alt: Follow @Tatsh

   .. image:: https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social
      :target: https://hostux.social/@Tatsh
      :alt: Mastodon Follow

This is an update of `Alexander Perlis' script <https://github.com/muttmua/mutt/blob/master/contrib/mutt_oauth2.py>`_
and conversion to a package. Instead of using GPG for token storage, this package uses Keyring.

.. only:: html

   Installation
   ------------

   .. code-block::bash

      pip install mutt-oauth2

Commands
--------

.. click:: mutt_oauth2.main:main
   :prog: mutt-oauth2
   :nested: full

Usage
-----

Start by calling ``mutt-oauth2 -a``. Be sure to have your client ID and and client secret available.

Scopes required
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Provider
     - Scopes
   * - Gmail
     - Gmail API
   * - Microsoft
     - offline_access IMAP.AccessAsUser.All POP.AccessAsUser.All SMTP.Send

To support other accounts, use the ``--username`` argument with a unique string such as the account
email address.

Test the script with the ``--test`` argument.

mutt configuration
^^^^^^^^^^^^^^^^^^

Add the following to ``muttrc``:

.. code-block::

   set imap_authenticators="oauthbearer:xoauth2"
   set imap_oauth_refresh_command="/path/to/mutt-oauth2"
   set smtp_authenticators=${imap_authenticators}
   set smtp_oauth_refresh_command=${imap_oauth_refresh_command}

.. only:: html

   Library
   -------
   .. automodule:: mutt_oauth2.constants
      :members:

   .. automodule:: mutt_oauth2.registrations
      :members:

   .. automodule:: mutt_oauth2.utils
      :members:

   .. toctree::
      :maxdepth: 2
      :caption: Contents:

   Indices and tables
   ==================
   * :ref:`genindex`
   * :ref:`modindex`
