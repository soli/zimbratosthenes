# python 2.7
from __future__ import print_function

import getpass
import sys
from datetime import date

from pythonzimbra.tools import auth
from pythonzimbra.request_xml import RequestXml
from pythonzimbra.response_xml import ResponseXml
from pythonzimbra.communication import Communication

from sievelib.parser import Parser
from sievelib.commands import ActionCommand, TestCommand, RequireCommand, \
    IfCommand, HeaderCommand, AddressCommand, SizeCommand, NotCommand, \
    ExistsCommand, \
    add_commands, comparator, match_type


def display_rule(rule):
    print('set "name" "' + rule['name'] + '";')
    print('set "active" "' + rule['active'] + '";')
    print('if ', end='')
    display_test(rule['filterTests'])
    print('{')
    display_actions(rule['filterActions'])
    print('}')


def display_test(test):
    print(test['condition'] + ' (')
    print(',\n'.join(transform_tests(test)))
    print(') ', end='')


def transform_tests(tests):
    new_tests = []
    known_tests = ['headerTest', 'sizeTest', 'dateTest', 'bodyTest',
                   'headerExistsTest']
    for key in known_tests:
        if key in tests:
            t = tests[key]
            # single element is not in a list...
            if not isinstance(t, list):
                t = [t]
            for tt in t:
                tt['test'] = key[:-4]
            new_tests.extend(t)
    known_tests.append('condition')
    for key in tests.keys():
        if key not in known_tests:
            print('Warning: unknown test category ' + key + ' - ' +
                  str(tests[key]), file=sys.stderr)
            print('/* unknown test category ' + key + ' - ' +
                  str(tests[key]) + ' */ true')
    new_tests.sort(key=lambda x: x.get('index'))
    return map(show_test, new_tests)


def translate(category, key):
    dic = {
        'date': {'before': 'le', 'after': 'ge'},
        'flag': {'read': '\\\\Seen', 'flagged': '\\\\Flagged'}
    }
    return dic[category][key]


def show_test(test):
    show = '   '
    if test.get('negative') == '1':
        show += 'not '
    if test['test'] == 'headerExists':
        show += 'exists ["' + test['header'] + '"]'
        return show
    if test['test'] == 'size':
        s = test['s']
        unit = s[-1]
        s = int(s[:-1])
        if unit in ['K', 'M', 'G']:
            s = s * 1024
        if unit in ['M', 'G']:
            s = s * 1024
        if unit == 'G':
            s = s * 1024
        show += 'size :' + test['numberComparison'] + ' ' + str(s)
        return show
    if test['test'] == 'date':
        show += 'date :value "' + translate('date', test['dateComparison']) + \
            '" "date" "' + date.fromtimestamp(int(test['d'])).isoformat() + '"'
        return show
    if test['test'] == 'body':
        show += 'body :contains'
    if test['test'] == 'header':
        show += 'header :' + test['stringComparison']
    if test['test'] == 'address':
        show += 'address :' + test['stringComparison'] + ' :' + test['part']
    if test.get('caseSensitive') == '1':
        show += ' :comparator "i;ascii-casemap"'
    if test['test'] in ['header', 'address']:
        show += ' ["' + '", "'.join(test['header'].split(',')) + \
            '"] ["' + test['value'] + '"]'
        return show
    if test['test'] == 'body':
        show += ' "' + test['value'] + '"'
        return show
    print('Warning: unknown test: ' + str(test), file=sys.stderr)
    return '/* unknown test: ' + str(test) + ' */ true'


def display_actions(actions):
    a = actions.items()
    a.sort(key=lambda (_, x): x.get('index'))
    for action in a:
        print('   ', end='')
        display_action(action)


def display_action(action):
    if action[0] == 'actionFileInto':
        print('fileinto "' + action[1]['folderPath'] + '";')
        return
    if action[0] == 'actionStop':
        print('stop;')
        return
    if action[0] == 'actionRedirect':
        print('redirect "' + action[1]['a'] + '";')
        return
    if action[0] == 'actionKeep':
        print('keep;')
        return
    if action[0] == 'actionDiscard':
        print('discard;')
        return
    # Zimbra specific
    if action[0] == 'actionFlag':
        print('addflag "' + translate('flag', action[1]['flagName']) + '";')
        return
    if action[0] == 'actionTag':
        print('tag "' + action[1]['tagName'] + '";')
        return
    # reply and notify not taken into account
    print('Warning: unknown action: ' + str(action), file=sys.stderr)
    print('/* unknown action: ' + str(action) + ' */ keep;')


def get_token(url):
    login = 'Sylvain.Soliman@inria.fr'
    passwd = getpass.getpass()

    return auth.authenticate(
        url,
        login,
        passwd,
        use_password=True
    )


class AddflagCommand(ActionCommand):
    args_definition = [
        {
            "name": "flag",
            "type": "string",
            "required": True
        }
    ]


class SetCommand(ActionCommand):
    args_definition = [
        {
            "name": "name",
            "type": "string",
            "required": True
        },
        {
            "name": "value",
            "type": "string",
            "required": True
        }
    ]


class TagCommand(ActionCommand):
    args_definition = [
        {
            "name": "tag",
            "type": "string",
            "required": True
        }
    ]


class DateCommand(TestCommand):
    is_extension = True
    args_definition = [
        {
            "name": "zone",
            "type": ["tag"],
            "write_tag": True,
            "values": [":zone"],
            "extra_arg": {"type": "string"},
            "required": False
        },
        {
            "name": "match-value",
            "type": ["tag"],
            "required": True
        },
        {
            "name": "comparison",
            "type": ["string"],
            "required": True
        },
        {
            "name": "match-against",
            "type": ["string"],
            "required": True
        },
        {
            "name": "match-against-field",
            "type": ["string"],
            "required": True
        }
    ]


class BodyCommand(TestCommand):
    args_definition = [
        comparator,
        match_type,
        {"name": "key-list",
         "type": ["string", "stringlist"],
         "required": True}
    ]


def zimbrify_header(htest):
    h = {
        u'stringComparison': unicode(htest['match-type'][1:]),
        u'value': unicode(htest['key-list'][0][1:-1]),
        u'header': ','.join(map(lambda h: h[1:-1], htest['header-names']))
    }
    if 'comparator' in htest.arguments:
        if htest['comparator']['extra_arg'] == '"i;ascii-casemap"':
            h[u'caseSensitive'] = u'0'
    return h


def zimbrify_address(htest):
    h = zimbrify_header(htest)
    if 'address_part' in htest.arguments:
        h[u'part'] = unicode(htest['address_part'][1:])
    return h


def zimbrify_size(htest):
    limit = int(htest['limit'])
    units = [u'B', u'K', u'M', u'G']
    idx = 0
    while idx < len(units) and limit % 1024 == 0:
        limit = limit / 1024
        idx += 1
    limit = unicode(limit) + units[idx]
    h = {
        u'numberComparison': unicode(htest['comparator'][1:]),
        u's': limit
    }
    return h


def zimbrify_exist(htest):
    return {u'header': unicode(htest['header-names'][0][1:-1])}


def zimbrify_body(htest):
    # deliberately ignoring the case where we get a list
    h = {u'value': unicode(htest['key-list'][1:-1])}
    if 'comparator' in htest.arguments:
        if htest['comparator']['extra_arg'] == '"i;ascii-casemap"':
            h[u'caseSensitive'] = u'0'
    return h


def zimbrify_test(test):
    tests = {
        u'condition': test.name
    }
    for (index, t) in enumerate(test['tests']):
        cat = None
        if isinstance(t, NotCommand):
            t = t['test']
            negative = True
        else:
            negative = False
        if isinstance(t, HeaderCommand):
            tt = zimbrify_header(t)
            cat = u'headerTest'
        if isinstance(t, AddressCommand):
            tt = zimbrify_address(t)
            cat = u'addressTest'
        if isinstance(t, SizeCommand):
            tt = zimbrify_size(t)
            cat = u'sizeTest'
        if isinstance(t, ExistsCommand):
            tt = zimbrify_exist(t)
            cat = u'headerExistsTest'
        if isinstance(t, BodyCommand):
            tt = zimbrify_body(t)
            cat = u'bodyTest'

        if cat is not None:
            if negative:
                tt[u'negative'] = u'1'
            tt[u'index'] = unicode(index)
            if cat not in tests:
                tests[cat] = []
            tests[cat].append(tt)
    actions = {}
    return(tests, actions)


def zimbrify(command_list):
    name = 'undefined'
    active = '1'
    commands = []
    for command in command_list:
        if isinstance(command, RequireCommand):
            pass
        elif isinstance(command, SetCommand):
            if command['name'] == '"name"':
                name = command['value'][1:-1]
            elif command['name'] == '"active"':
                active = command['value'][1:-1]
            else:
                print('unknown variable: ' + command['name'], file=sys.stderr)
        elif isinstance(command, IfCommand):
            (tests, actions) = zimbrify_test(command['test'])
            cmd = {
                u'name': name, u'active': active, u'filterTests': tests,
                u'filterActions': actions
            }
            commands.append(cmd)
        else:
            print('unknown command: ' + command, file=sys.stderr)
    commands.reverse()
    return commands


def parse():
    if sys.argv[1] == '-':
        inputfile = sys.stdin
    else:
        inputfile = sys.argv[1]
    print('parsing ' + inputfile, file=sys.stderr)
    add_commands([AddflagCommand, SetCommand, TagCommand, DateCommand,
                  BodyCommand])
    p = Parser()
    if p.parse_file(inputfile) is False:
        print(p.error)
    else:
        return zimbrify(p.result)


def main():
    url = 'https://zimbra.inria.fr/service/soap/'

    if len(sys.argv) < 2:
        token = get_token(url)
        request = RequestXml()
        request.set_auth_token(token)

        request.add_request('GetFilterRulesRequest', {}, 'urn:zimbraMail')

        response = ResponseXml()
        comm = Communication(url)
        comm.send_request(request, response)

        if not response.is_fault():
            rules = response.get_response()['GetFilterRulesResponse']
            print('require ["date", "relational", "fileinto",' +
                  ' "imap4flags", "body", "variables"];')
            print()
            for rule in rules['filterRules']['filterRule']:
                print(rule)
                display_rule(rule)
                print()
    else:
        print(parse())


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

    dummy_sieve = '''require ["date", "relational", "fileinto", "imap4flags",
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
    add_commands([AddflagCommand, SetCommand, TagCommand, DateCommand,
                  BodyCommand])
    p = Parser()
    if p.parse(dummy_sieve) is False:
        print(p.error)
    else:
        z = zimbrify(p.result)[0]['filterTests']
        dummy_rule = dummy_rule['filterTests']
        print(z == dummy_rule)
        print(dummy_sieve)
        print(z)
        print(dummy_rule)


if __name__ == '__main__':
    test_things()
    # main()
