mutt-oauth2
===========

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
