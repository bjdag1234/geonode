.. _getting_started:


***************
Getting started
***************

.. _installing-docdir:

Installing your doc directory
=============================

You may already have `sphinx <http://sphinx.pocoo.org/>`_
installed -- you can check by doing::

  > python -c 'import sphinx'

If that fails grab the latest version of and install it with::

  > sudo easy_install -U Sphinx

Now you are ready to check out the remote branch documentation, in your geonode folder::

  > git checkout -b documentation origin/documentation

The rst files in docs/source/ and the Makefile in docs/ are the things to watch out.
In the Makefile, BUILDDIR is where the documentation will be created::

  BUILDDIR      = ../../documentation

To prepare the repository for the publication online, we must have a branch named 'gh-pages', where it contains the html folder.
So we should clone the existing git repository for the html files, but first we must create documentation/::

  > cd ..
  > mkdir documentation
  > git clone https://github.com/PhilLidar-DAD/documentation.git html
  > cd html
  > git checkout -b gh-pages origin/gh-pages

Now going back to your geonode directory::

  > cd ../../geonode/

You can build build some html by::

  > cd docs
  > make html

Or::

  > make html -C docs

Then commit and push your gh-pages branch in the html repository::

  > cd ../documentation/html/
  > git commit -am "<message>"
  > git config --global push.default simple
  > git push

Visiting your documentation
-----------------

You may want to refresh `Phil-LiDAR's documentation page <https://phillidar-dad.github.io/documentation/>`_
