..
  SPDX-License-Identifier: GPL-3.0-or-later
  SPDX-FileCopyrightText: Linutronix GmbH

ELBE docs
==========

Welcome to the ELBE documentation.

This documentation covers how to use ELBE to build root-filesystem images for
embedded devices, define your build projects via XML, and includes a reference
to ELBEs commands and schema.

If you are new to ELBE, we recommend starting with the
:doc:`Quickstart <article-quickstart>` and afterwards
:doc:`Overview <article-elbeoverview-en>`.

.. toctree::
   :maxdepth: 1

   article-quickstart
   article-elbeoverview-en
   article-base-extended
   article-elbe-schema-reference
   elbevalidate
   news/index

.. toctree::
   :maxdepth: 1
   :caption: man-pages

   elbe
   elbe-add
   elbe-check_updates
   elbe-cyclonedx-sbom
   elbe-initvm
   elbe-parselicence
   elbe-pbuilder
   elbe-pkgdiff
   elbe-prjrepo
   elbe-show
   elbe-validate

.. toctree::
   :maxdepth: 1
   :caption: updated commands

   elbe-gen_update
   elbe-updated

.. toctree::
   :maxdepth: 1
   :caption: internal commands

   elbe-chg_archive
   elbe-chroot
   elbe-control
   elbe-daemon
   elbe-db
   elbe-debianize
   elbe-diff
   elbe-fetch_initvm_pkgs
   elbe-get_archive
   elbe-preprocess
   elbe-remove_sign
   elbe-repodir
   elbe-setsel
   elbe-sign
