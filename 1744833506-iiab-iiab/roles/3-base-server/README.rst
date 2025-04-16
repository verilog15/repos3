.. |ss| raw:: html

   <strike>

.. |se| raw:: html

   </strike>

.. |nbsp| unicode:: 0xA0
   :trim:

====================
3-base-server README
====================

This 3rd `stage <https://github.com/iiab/iiab/wiki/IIAB-Contributors-Guide#ansible>`_ installs base server infra that `Internet-in-a-Box (IIAB) <https://internet-in-a-box.org/>`_ requires, including:

- |ss| `MySQL <https://github.com/iiab/iiab/blob/master/roles/mysql>`_ (database underlying many/most user-facing apps). |se| |nbsp|  *As of 2023-11-05, MySQL / MariaDB is NO LONGER INSTALLED by 3-base-server — instead it's installed on-demand — as a dependency of Matomo, MediaWiki, Nextcloud, PBX (for FreePBX), WordPress &/or Admin Console.*  This IIAB role (roles/mysql) also installs apt package:
   - **php{{ php_version }}-mysql** — which forcibly installs **php{{ php_version }}-common**
- `NGINX <https://github.com/iiab/iiab/blob/master/roles/nginx>`_ web server (with Apache in some lingering cases).  This IIAB role also installs apt package:
   - **php{{ php_version }}-fpm** — which forcibly installs **php{{ php_version }}-cli**, **php{{ php_version }}-common** and **libsodium23**
- `www_base <https://github.com/iiab/iiab/blob/master/roles/www_base>`_ (similar to `www_options <https://github.com/iiab/iiab/blob/master/roles/www_options>`_ which runs later in 4-server-options)

Recap: As with 0-init, 1-prep, 2-common, 4-server-options and 5-xo-services — this 3rd stage installs core server infra (that is not user-facing).

The next stage (4-server-options) brings more diverse/optional server infra functionality.
