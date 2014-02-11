import zimbra


def test_things():
    # Obtained from a dummy and inactive rule on Zimbra
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

    dummy_sieve = r'''require ["date", "relational", "fileinto", "imap4flags",
"body", "variables"];

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
'''
    p = zimbra.init_parser()
    if p.parse(dummy_sieve) is False:
        raise Exception(p.error)
    else:
        assert dummy_rule == zimbra.zimbrify(p.result)[0]
