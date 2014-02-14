# python 2.7
from __future__ import print_function

import getpass
import sys
import os
from datetime import date, datetime
from os.path import basename

from pythonzimbra.tools import auth
from pythonzimbra.request_xml import RequestXml
from pythonzimbra.response_xml import ResponseXml
from pythonzimbra.communication import Communication

from sievelib.parser import Parser
from sievelib.commands import ActionCommand, TestCommand, RequireCommand, \
    IfCommand, HeaderCommand, AddressCommand, SizeCommand, NotCommand, \
    ExistsCommand, KeepCommand, DiscardCommand, StopCommand, FileintoCommand, \
    RedirectCommand, \
    add_commands, comparator, match_type


def display_rule(rule):
    '''print out one single Zimbra filter

    use two varibles to store name and active flag, then one test with
    possibly many actions'''
    print(u'set "name" "' + rule[u'name'] + u'";')
    print(u'set "active" "' + rule[u'active'] + u'";')
    print(u'if ', end=u'')
    display_test(rule[u'filterTests'])
    print(u'{')
    display_actions(rule[u'filterActions'])
    print(u'}')


def display_test(test):
    '''any Zimbra filter is anyof/allof and then possibly many tests'''
    print(test[u'condition'] + u' (')
    print(u',\n'.join(transform_tests(test)))
    print(u') ', end=u'')


def transform_tests(tests):
    '''for each subtest category, convert the tests to a single list and print

    tests are grouped by category in Zimbra but not in Sieve. The index is
    used for ordering'''
    new_tests = []
    known_tests = [u'headerTest', u'sizeTest', u'dateTest', u'bodyTest',
                   u'headerExistsTest']
    for key in known_tests:
        if key in tests:
            t = tests[key]
            # single element is not in a list...
            if not isinstance(t, list):
                t = [t]
            for tt in t:
                tt[u'test'] = key[:-4]
            new_tests.extend(t)
    known_tests.append(u'condition')
    for key in tests.keys():
        if key not in known_tests:
            print(u'Warning: unknown test category ' + key + u' - ' +
                  unicode(tests[key]), file=sys.stderr)
            print(u'/* unknown test category ' + key + u' - ' +
                  unicode(tests[key]) + u' */ true')
    new_tests.sort(key=lambda x: int(x.get(u'index')))
    return map(show_test, new_tests)


def translate(category, key):
    '''Utility function for Zimbra to Sieve translation'''
    dic = {
        u'date': {u'before': u'le', u'after': u'ge'},
        u'flag': {u'read': u'\\\\Seen', u'flagged': u'\\\\Flagged'}
    }
    return dic[category][key]


def show_test(test):
    '''return a Sieve string for a single test'''
    show = u'   '
    if test.get(u'negative') == u'1':
        show += u'not '
    if test[u'test'] == u'headerExists':
        show += u'exists ["' + test[u'header'] + u'"]'
        return show
    if test[u'test'] == u'size':
        s = test[u's']
        unit = s[-1]
        s = int(s[:-1])
        if unit in [u'K', u'M', u'G']:
            s = s * 1024
        if unit in [u'M', u'G']:
            s = s * 1024
        if unit == u'G':
            s = s * 1024
        show += u'size :' + test[u'numberComparison'] + u' ' + unicode(s)
        return show
    if test[u'test'] == u'date':
        show += u'date :value "' + \
            translate(u'date', test[u'dateComparison']) + \
            u'" "date" "' + \
            date.fromtimestamp(int(test[u'd'])).isoformat() + u'"'
        return show
    if test[u'test'] == u'body':
        show += u'body :contains'
    if test[u'test'] == u'header':
        show += u'header :' + test[u'stringComparison']
    if test[u'test'] == u'address':
        show += u'address :' + test[u'stringComparison'] + u' :' + \
            test[u'part']
    if test.get(u'caseSensitive') == u'1':
        show += u' :comparator "i;ascii-casemap"'
    if test[u'test'] in [u'header', u'address']:
        show += u' ["' + u'", "'.join(test[u'header'].split(u',')) + \
            u'"] ["' + test[u'value'] + u'"]'
        return show
    if test[u'test'] == u'body':
        show += u' "' + test[u'value'] + u'"'
        return show
    print(u'Warning: unknown test: ' + unicode(test), file=sys.stderr)
    return u'/* unknown test: ' + unicode(test) + u' */ true'


def display_actions(actions):
    '''display a list of actions in the order specified by their index'''
    a = actions.items()
    a.sort(key=lambda (_, x): int(x.get(u'index')))
    for action in a:
        print(u'   ', end=u'')
        display_action(action)


def display_action(action):
    '''print the Sieve string for a single action'''
    if action[0] == u'actionFileInto':
        print(u'fileinto "' + action[1][u'folderPath'] + u'";')
        return
    if action[0] == u'actionStop':
        print(u'stop;')
        return
    if action[0] == u'actionRedirect':
        print(u'redirect "' + action[1][u'a'] + u'";')
        return
    if action[0] == u'actionKeep':
        print(u'keep;')
        return
    if action[0] == u'actionDiscard':
        print(u'discard;')
        return
    # Zimbra specific
    if action[0] == u'actionFlag':
        print(u'addflag "' + translate(u'flag', action[1][u'flagName']) +
              u'";')
        return
    if action[0] == u'actionTag':
        print(u'tag "' + action[1][u'tagName'] + u'";')
        return
    # reply and notify not taken into account
    print(u'Warning: unknown action: ' + unicode(action), file=sys.stderr)
    print(u'/* unknown action: ' + unicode(action) + u' */ keep;')


def get_token(url):
    '''Get authentication token from Zimbra SOAP API'''
    login = os.getenv('LOGNAME') or os.getenv('USER') or os.getlogin()
    login = unicode(login)
    passwd = getpass.getpass()

    return auth.authenticate(
        url,
        login,
        passwd,
        use_password=True
    )


class AddflagCommand(ActionCommand):
    '''Sieve command to handle Zimbra flags'''
    # extension_map is hardcoded in sievelib, so we cannot use this
    # is_extension = True
    args_definition = [
        {
            "name": "flag",
            "type": "string",
            "required": True
        }
    ]


class SetCommand(ActionCommand):
    '''Sieve command to handle variables used to store Zimbra rule name'''
    is_extension = True
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
    '''Sieve command to handle Zimbra tags'''
    # extension_map is hardcoded in sievelib, so we cannot use this
    # is_extension = True
    args_definition = [
        {
            "name": "tag",
            "type": "string",
            "required": True
        }
    ]


class DateCommand(TestCommand):
    '''Sieve test for Zimbra date comparisons'''
    # extension_map is hardcoded in sievelib, so we cannot use this
    # is_extension = True
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
    '''Sieve test for Zimbra body matches'''
    is_extension = True
    args_definition = [
        comparator,
        match_type,
        {"name": "key-list",
         "type": ["string", "stringlist"],
         "required": True}
    ]


def zimbrify_header(htest):
    '''Return a Zimbra headerTest for the corresponding Sieve test'''
    h = {
        u'stringComparison': unicode(htest[u'match-type'][1:]),
        u'value': unicode(htest[u'key-list'][0][1:-1]),
        u'header': unicode(
            u','.join(map(lambda h: h[1:-1], htest[u'header-names'])))
    }
    if u'comparator' in htest.arguments:
        if htest[u'comparator'][u'extra_arg'] == u'"i;ascii-casemap"':
            h[u'caseSensitive'] = u'0'
    return h


def zimbrify_address(htest):
    '''Return a Zimbra addressTest for the corresponding Sieve test'''
    h = zimbrify_header(htest)
    if u'address_part' in htest.arguments:
        h[u'part'] = unicode(htest[u'address_part'][1:])
    return h


def zimbrify_size(htest):
    '''Return a Zimbra sizeTest for the corresponding Sieve test'''
    limit = int(htest[u'limit'])
    units = [u'B', u'K', u'M', u'G']
    idx = 0
    while idx < len(units) and limit % 1024 == 0:
        limit = limit / 1024
        idx += 1
    limit = unicode(limit) + units[idx]
    h = {
        u'numberComparison': unicode(htest[u'comparator'][1:]),
        u's': limit
    }
    return h


def zimbrify_exist(htest):
    '''Return a Zimbra headerExistsTest for the corresponding Sieve test'''
    return {u'header': unicode(htest[u'header-names'][0][1:-1])}


def zimbrify_body(htest):
    '''Return a Zimbra bodyTest for the corresponding Sieve test'''
    # FIXME deliberately ignoring the case where we get a list
    h = {u'value': unicode(htest[u'key-list'][1:-1])}
    if u'comparator' in htest.arguments:
        if htest[u'comparator'][u'extra_arg'] == u'"i;ascii-casemap"':
            h[u'caseSensitive'] = u'0'
    return h


def zimbrify_date(htest):
    '''Return a Zimbra dateTest for the corresponding Sieve test'''
    if htest[u'comparison'] == u'"le"':
        comp = u'before'
    else:
        comp = u'after'
    dt = htest[u'match-against-field']
    since_epoch = int(
        round((datetime(int(dt[1:5]), int(dt[6:8]), int(dt[9:11])) -
               datetime(1970, 1, 1)).total_seconds()))
    return {
        u'd': unicode(since_epoch),
        u'dateComparison': comp
    }


def zimbrify_actions(actions):
    '''Return a dict of Zimbra actions for the corresponding Sieve actions'''
    acts = {}
    for (index, a) in enumerate(actions):
        cat = None
        if isinstance(a, KeepCommand):
            aa = {}
            cat = u'actionKeep'
        if isinstance(a, DiscardCommand):
            aa = {}
            cat = u'actionDiscard'
        if isinstance(a, StopCommand):
            aa = {}
            cat = u'actionStop'
        if isinstance(a, AddflagCommand):
            if a[u'flag'] == u'"\\\\Seen"':
                flag = u'read'
            else:
                flag = u'flagged'
            aa = {u'flagName': flag}
            cat = u'actionFlag'
        if isinstance(a, TagCommand):
            aa = {u'tagName': unicode(a[u'tag'][1:-1])}
            cat = u'actionTag'
        if isinstance(a, FileintoCommand):
            aa = {u'folderPath': unicode(a[u'mailbox'][1:-1])}
            cat = u'actionFileInto'
        if isinstance(a, RedirectCommand):
            aa = {u'a': unicode(a[u'address'][1:-1])}
            cat = u'actionRedirect'

        if cat is not None:
            aa[u'index'] = unicode(index)
            # use a single value, then a list
            if cat not in acts:
                acts[cat] = aa
            elif not isinstance(acts[cat], list):
                acts[cat] = [acts[cat], aa]
            else:
                acts[cat].append(aa)
    return acts


def zimbrify_test(test):
    '''Return a dict of Zimbra tests for the corresponding Sieve tests'''
    tests = {
        u'condition': unicode(test.name)
    }
    for (index, t) in enumerate(test[u'tests']):
        cat = None
        if isinstance(t, NotCommand):
            t = t[u'test']
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
        if isinstance(t, DateCommand):
            tt = zimbrify_date(t)
            cat = u'dateTest'

        if cat is not None:
            if negative:
                tt[u'negative'] = u'1'
            tt[u'index'] = unicode(index)
            # use a single value, then a list
            if cat not in tests:
                tests[cat] = tt
            elif not isinstance(tests[cat], list):
                tests[cat] = [tests[cat], tt]
            else:
                tests[cat].append(tt)
    return tests


def zimbrify(command_list):
    '''Translate a parsed sieve file to a Zimbra filter list'''
    name = u'undefined'
    active = u'1'
    commands = []
    for command in command_list:
        if isinstance(command, RequireCommand):
            pass
        elif isinstance(command, SetCommand):
            if command[u'name'] == u'"name"':
                name = command[u'value'][1:-1]
            elif command[u'name'] == u'"active"':
                active = command[u'value'][1:-1]
            else:
                print(u'unknown variable: ' + command[u'name'],
                      file=sys.stderr)
        elif isinstance(command, IfCommand):
            tests = zimbrify_test(command[u'test'])
            actions = zimbrify_actions(command.children)
            cmd = {
                u'name': unicode(name), u'active': unicode(active),
                u'filterTests': tests, u'filterActions': actions
            }
            commands.append(cmd)
        else:
            print(u'unknown command: ' + command, file=sys.stderr)
    return commands


def init_parser():
    '''initialize a Sieve parser with our supplementary commands'''
    add_commands([AddflagCommand, SetCommand, TagCommand, DateCommand,
                  BodyCommand])
    return Parser()


def parse():
    '''parse either a file or stdin and convert the result to Zimbra format'''
    if sys.argv[1] == u'-':
        inputfile = sys.stdin
    else:
        inputfile = sys.argv[1]
    print(u'parsing ' + inputfile, file=sys.stderr)
    p = init_parser()
    if p.parse_file(inputfile) is False:
        print(p.error)
    else:
        return zimbrify(p.result)


def display_rules(rules):
    '''print out a Sieve file corresponding to Zimbra filter rules'''
    print(u'require ["date", "relational", "fileinto",' +
          u' "imap4flags", "body", "variables"];')
    print(u'')
    for rule in rules:
        display_rule(rule)
        print(u'')


def update_rules(comm, token, rules):
    '''If confirmed try to upload rules corresponding to a parse

    if there is an issue, try to re-upload original rules'''
    new_rules = {u'filterRules': {u'filterRule': parse()}}
    confirm = raw_input(u'Do you wish to proceed [y/N]? ')
    if not confirm[0] in [u'y', u'Y']:
        exit(0)
        print(u'Uploading new filters', file=sys.stderr)
        response = communicate(comm, token,
                               u'ModifyFilterRulesRequest', new_rules)

        if response.is_fault():
            response = communicate(comm, token,
                                   u'ModifyFilterRulesRequest', rules)
            if response.is_fault():
                print(u'Uh oh! Updating your filters generated an error',
                      file=sys.stderr)
            else:
                print(u'We could not change your filters, sorry.',
                      file=sys.stderr)
        else:
            print(u'Seems ok', file=sys.stderr)


def communicate(comm, token, request_type, request_args):
    '''Send a request to Zimbra SOAP API and return response'''
    request = RequestXml()
    request.set_auth_token(token)
    request.add_request(request_type, request_args, u'urn:zimbraMail')

    response = ResponseXml()
    comm.send_request(request, response)
    return response


def usage():
    '''Command usage'''
    print(u'''Usage:
  {0} [file.sieve]

  If an argument is given, {0} will parse the file as a list of sieve rules
and then upload them to the Zimbra server. '-' can be used to use standard
input.

  If no argument is given, {0} will download current mail filters from the
Zimbra server and convert them to sieve rules, displayed on standard output.
'''.format(basename(sys.argv[0])))
    exit(1)


def main():
    '''Test arguments and either convert Zimbra to Sieve or the opposite'''
    if len(sys.argv) > 2 or u'-h' in sys.argv or u'--help' in sys.argv:
        usage()

    url = u'https://zimbra.inria.fr/service/soap/'
    token = get_token(url)
    comm = Communication(url)

    response = communicate(comm, token, u'GetFilterRulesRequest', {})

    if not response.is_fault():
        rules = response.get_response()[u'GetFilterRulesResponse']
        if len(sys.argv) < 2:
            display_rules(rules[u'filterRules'][u'filterRule'])
        else:
            update_rules(comm, token, rules)


if __name__ == '__main__':
    main()
