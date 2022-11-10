.. _contributing:

Contributor's Guide
===================

This document lays out guidelines and advice for contributing to this project.


Code Contributions
------------------


Submission checklist
~~~~~~~~~~~~~~~~~~~~

When contributing code, you'll want to follow this checklist:

    1. Fork the repository on GitHub.

    2. Create a new branch, naming it appropriately.

    3. Run the tests to confirm they all pass on your system. If they don't, you'll
       need to investigate why they fail. If you're unable to diagnose this
       yourself, raise it as a bug report by following the guidelines in this
       document: :ref:`bug-reports`.

    4. Write tests that demonstrate your bug or feature. Ensure that they fail.

    5. Make your change.

    6. Run the entire test suite again, confirming that all tests pass *including
       the ones you just added*.

    7. Ensure the formatting and lint checks pass.

    8. Open a Pull Request (PR) to the main repository's ``main`` branch.
       Make sure to check the box "Allow edits from maintainers".


Create a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First create a virtual env and install all the dev dependencies (``requirements.txt``).
The following steps all assume you are working out of a virtual env with all
dependencies installed.


Running the Tests
~~~~~~~~~~~~~~~~~

Unit tests::

    $ pytest

End-to-end tests::

    $ python -m test.ci


Lint your code
~~~~~~~~~~~~~~

The repo follows standard Python style guidelines such as PEP8.  Consistent formatting
is enforced by running ``black`` and more problematic code smells are detected via
``flake8`` and ``pylint``.  For convenience, you can run all these using ``make`` 
(they should have been installed as part of your virtual env)::

    $ make black
    $ make lint

The first command will format all python files in the repo.  Ensure you commit these
changes since continuous integration (CI) will fail if it detects non-compliance with
``black``.  

The second command will run ``flake8`` and ``pylint`` using the repo's configurations for
those linters.  Note that we have made very few changes to the default settings.
Again, ensure this check passes because CI will fail otherwise.


Code Review
~~~~~~~~~~~

Every contribution will be reviewed by one of the maintainers.  Feedback may require
you to make changes before the contribution is merged into the repo.


Documentation Contributions
---------------------------

Documentation improvements are always welcome! The documentation files live in
the ``docs/`` directory of the codebase. They're written in
`reStructuredText`_, and use `Sphinx`_ to generate the full suite of
documentation.

Please follow similar practices as in existing documentation.  It is still young
and so we have not established editorial standards, but you should endeavour to
keep consistent syntax and formatting.  We like to explain things more informally
as a start and then re-iterate more formally later.

Much of the API documentation is generated from python docstrings.  They should
have a clear description preceding precise details on parameters.  Notes should
be used plentifully to point out useful "things" that don't easily fit in
elsewhere.


.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/index.html



.. _bug-reports:

Bug Reports
-----------

One of the most useful ways you can contribute is by reporting a bug (issue).
This ensures that code contributors can address the underlying problem so others
are not impacted in the future.

Before doing so, please check existing `GitHub issues`_, **both open and closed**,
to confirm this is not a duplicate issue.  Next, be sure to properly describe the
issue, providing the requested details and any appropriate code snippet, as
requested in the "bug report" template.

.. _GitHub issues: https://github.com/psf/requests/issues


Feature Requests
----------------

Requests for new features are welcome!  Curvesim is new and rapidly evolving.
The maintainers' hope is that it will prove useful to those in the Curve
community.  This can only happen if community members offer suggestions on
how the package can better serve their needs

Perhaps confusingly, in GitHub, feature requests and bug reports get submitted
through the same channel, "issues".  When proposing a feature request, open
an issue on the repo and select the "feature request" template.
