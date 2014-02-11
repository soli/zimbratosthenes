***************
Zimbratosthenes
***************

    *"Cat project" not "pet project"--you are going to put a lot into it but
    don't expect anything back* -- Kent Beck on Twitter

Zimbratosthenes aims at bridging the gap between `Zimbra
<http://zimbra.com>`_'s mail filters and the `Sieve language
<http://tools.ietf.org/html/rfc5228>`_ allowing to describe mail filters as
simple text files.

Usage
=====

::

    zbt

If no argument is given, `zbt` will download current mail filters from the
Zimbra server and convert them to sieve rules, displayed on standard output. ::

    zbt file.sieve

If an argument is given, `zbt` will parse the file as a list of sieve rules
and then upload them to the Zimbra server. '-' can be used to use standard
input.

Foundations
===========

`Zimbra SOAP API
<http://files.zimbra.com/docs/soap_api/8.0.4/soap-docs-804/api-reference/index.html>`_
