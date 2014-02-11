'''No unit tests for zimbratosthenes, only one big integration test

Basically, a big ugly compound filter was built on Zimbra, then obtained
through a request. We check that if translated to sieve and back we do not
lose anything'''

from io import StringIO
import sys

import zimbra


dummy_rule = {
    u'active': u'0',
    u'filterTests': {
        u'bodyTest': {u'index': u'6', u'value': u'baz'},
        u'dateTest': {u'index': u'5', u'negative': u'1',
                      u'dateComparison': u'after', u'd': u'1388530800'},
        u'headerTest': [
            {u'stringComparison': u'contains', u'index': u'0',
                u'value': u'fizz', u'header': u'subject'},
            {u'stringComparison': u'contains', u'index': u'1',
                u'negative': u'1', u'value': u'buzz', u'header': u'from'},
            {u'stringComparison': u'is', u'index': u'2', u'value': u'foo',
                u'header': u'to,cc'},
            {u'stringComparison': u'matches', u'index': u'3',
                u'negative': u'1', u'value': u'*none?', u'header': u'X-bar'}],
        u'sizeTest': {u'numberComparison': u'over', u'index': u'4',
                      u's': u'10M'},
        u'condition': u'allof',
        u'headerExistsTest': {u'index': u'7', u'negative': u'1',
                              u'header': u'X-dummy'}},
    u'name': u'dummy',
    u'filterActions': {
        u'actionRedirect': {u'a': u'example@example.com', u'index': u'4'},
        u'actionTag': {u'index': u'1', u'tagName': u'Old'},
        u'actionFileInto': {u'index': u'3', u'folderPath': u'.pipe'},
        u'actionFlag': {u'index': u'2', u'flagName': u'read'},
        u'actionDiscard': {u'index': u'5'},
        u'actionKeep': {u'index': u'0'}, u'actionStop': {u'index': u'6'}}}

dummy_sieve = u'''require ["date", "relational", "fileinto", \
"imap4flags", "body", "variables"];

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
   addflag "\\\\Seen";
   fileinto ".pipe";
   redirect "example@example.com";
   discard;
   stop;
}

'''


def test_sieve_and_zimbrify():
    '''Parse mock sieve file and convert to Zimbra rule'''
    p = zimbra.init_parser()
    if p.parse(dummy_sieve) is False:
        raise Exception(p.error)
    else:
        assert dummy_rule == zimbra.zimbrify(p.result)[0]


def test_zimbra_to_sieve_converter():
    '''Convert zimbra rule to sieve'''
    dummy_out = StringIO()
    sys.stdout = dummy_out
    zimbra.display_rules([dummy_rule])
    sys.stdout.seek(0)
    dummy_result = sys.stdout.read()
    sys.stdout.close()
    sys.stdout = sys.__stdout__
    assert len(dummy_result) == len(dummy_sieve)
    for i in xrange(0, len(dummy_sieve)):
        assert dummy_result[i] == dummy_sieve[i]
