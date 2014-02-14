***************
Zimbratosthenes
***************

.. image:: https://travis-ci.org/soli/zimbratosthenes.png?branch=master
   :target: https://travis-ci.org/soli/zimbratosthenes

[Warning: experimental]

    *"Cat project" not "pet project"--you are going to put a lot into it but
    don't expect anything back* -- Kent Beck `on Twitter
    <https://twitter.com/KentBeck/status/432920221066596353>`_

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

Motivation
==========

Zimbra admins can actually more or less import Sieve filters for a given user
as explained in https://wiki.zimbra.com/index.php?title=Email_Rules_Migration.

However, it is a shame that an end-user has no other way to manage her filters
than to access the Web server. I personally read my mail through IMAP, access
my calendar through CalDAV, and thus filters are the only thing that kept me
opening the web server from time to time.

However, that also meant that I wasn't able to automatically update filters in
any case (e.g., frequent sender in my Junk box), or to trigger a modification
to a filter from my mail client… 

Nevertheless, I discovered that Zimbra's mail filters can be accessed and
modified through `Zimbra SOAP API
<http://files.zimbra.com/docs/soap_api/8.0.4/soap-docs-804/api-reference/index.html>`_
hence was born Zimbratosthenes.

Foundations
===========

Unfortunately Zimbra does not support precisely Sieve, nor any of its
`extensions <https://en.wikipedia.org/wiki/Sieve_(mail_filtering_language)>`_,
the mapping is thus quite fragile, but if you build a few rules in the web
interface, they should be easy to edit later on.

All filters available except reply/notify/addressbook are translated to Sieve
with some extensions. For instance the ``variables`` extension is used to
store the name and activity status of a filter rule.

Let us look at an example::

    require ["date", "relational", "fileinto", "imap4flags", "body", "variables"];

    set "name" "dummy";
    set "active" "0";
    if allof (
       header :contains ["subject"] ["fizz"],
       not header :contains ["from"] ["buzz"],
       header :is ["to", "cc"] ["foo"],
       not header :matches ["X-bar"] ["*none?"],
       size :over 10485760,
       not date :value "ge" "date" "2014-01-01",
       body :contains "baz",
       not exists ["X-dummy"]
    ) {
       keep;
       tag "Old";
       addflag "\\Seen";
       fileinto ".pipe";
       redirect "example@example.com";
       discard;
       stop;
    }

Zimbra defіnes always an ``allof`` or ``anyof`` condition, Zimbratosthenes
therefore expects such structure, even if there is a single condition.

Similarly, ``header`` tests can only target a single header or the couple
``To, Cc``. Size has to be indicated in bytes and gets converted back when
sent to Zimbra. The ``imap4flags`` extension is supported but only for
``\\Seen`` and ``\\Flagged``. The rest mostly works line in Sieve. If there is
an error parsing a Sieve file or converting to a Zimbra-compatible filter, a
message will be displayed on stderr.

Good luck, this software is still in a very experimental state!

Credits
=======

We make a heavy use of `python-zimbra
<https://github.com/Zimbra-Community/python-zimbra>`_ and of `sievelib
<https://bitbucket.org/tonioo/sievelib>`_.
