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
    IfCommand, HeaderCommand, add_commands


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
    known_tests = ['headerTest', 'sizeTest', 'dateTest', 'bodyTest']
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
    if test['test'] == 'size':
        show += 'size :' + test['numberComparison'] + ' ' + test['s']
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
        show += ' "' + test['string'] + '"'
        return show
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


def zimbrify_header(htest, index, negative=False):
    h = {
        u'index': index,
        u'stringComparison': htest['match-type'][1:],
        u'value': htest['key-list'][0][1:-1],
        u'header': ','.join(map(lambda h: h[1:-1], htest['header-names']))
    }
    if negative:
        h[u'negative'] = '1'
    if 'comparator' in htest.arguments:
        if htest['comparator']['extra_arg']['values'] == '"i;ascii-casemap"':
            h[u'caseSensitive'] = '0'
    return h


def zimbrify_test(test):
    tests = {
        u'condition': test.name
    }
    for (index, t) in enumerate(test['tests']):
        if isinstance(t, HeaderCommand):
            tt = zimbrify_header(t, index + 1)
            if 'headerTest' not in tests:
                tests['headerTest'] = []
            tests['headerTest'].append(tt)
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
    print('parsing ' + sys.argv[1])
    add_commands([AddflagCommand, SetCommand, TagCommand, DateCommand])
    p = Parser()
    if p.parse_file(sys.argv[1]) is False:
        print(p.error)
    else:
        print(zimbrify(p.result))


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
        parse()


if __name__ == '__main__':
    main()
