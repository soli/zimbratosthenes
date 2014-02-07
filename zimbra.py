# python 2.7

import getpass

from pythonzimbra.tools import auth
from pythonzimbra.request_xml import RequestXml
from pythonzimbra.response_xml import ResponseXml
from pythonzimbra.communication import Communication


def display_rule(rule):
    print '# ' + rule['name']
    if rule['active'] == '0':
        print '# inactive'
    print 'if',
    display_test(rule['filterTests'])
    print '{'
    display_actions(rule['filterActions'])
    print '}'


def display_test(test):
    print test['condition'] + ' ('
    print ',\n'.join(transform_tests(test))
    print ')',


def transform_tests(tests):
    new_tests = []
    for key in ['headerTest', 'sizeTest']:
        if key in tests:
            t = tests[key]
            # single element is not in a list...
            if not isinstance(t, list):
                t = [t]
            for tt in t:
                tt['test'] = key[:-4]
            new_tests.extend(t)
    new_tests.sort(key=lambda x: x.get('index'))
    return map(show_test, new_tests)


def show_test(test):
    show = '   '
    if test.get('negative') == '1':
        show += 'not '
    if test['test'] == 'size':
        show += 'size :' + test['numberComparison'] + ' ' + test['s']
        return show
    if test['test'] == 'header':
        show += 'header :' + test['stringComparison']
    if test['test'] == 'address':
        show += 'address :' + test['stringComparison'] + ' :' + test['part']
    if test['test'] not in ['header', 'address']:
        return '/* unknown test: ' + test + ' */ true'
    if test.get('caseSensitive') == '1':
        show += ' :comparator "i;ascii-casemap"'
    show += ' ["' + '", "'.join(test['header'].split(',')) + \
        '"] ["' + test['value'] + '"]'
    return show


def display_actions(actions):
    a = actions.items()
    a.sort(key=lambda (_, x): x.get('index'))
    for action in a:
        print '  ',
        display_action(action)


def display_action(action):
    if action[0] == 'actionFileInto':
        print 'fileinto "' + action[1]['folderPath'] + '";'
        return
    if action[0] == 'actionStop':
        print 'stop;'
        return
    if action[0] == 'actionRedirect':
        print 'redirect "' + action[1]['a'] + '";'
        return
    if action[0] == 'actionKeep':
        print 'keep;'
        return
    if action[0] == 'actionDiscard':
        print 'discard;'
        return
    # Zimbra specific
    if action[0] == 'actionFlag':
        print 'flag "' + action[1]['flagName'] + '";'
        return
    if action[0] == 'actionTag':
        print 'tag "' + action[1]['tagName'] + '";'
        return
    # reply and notify not taken into account
    print '/* unknown action: ' + action + ' */ keep;'


def main():
    login = 'Sylvain.Soliman@inria.fr'
    passwd = getpass.getpass()
    url = 'https://zimbra.inria.fr/service/soap/'

    token = auth.authenticate(
        url,
        login,
        passwd,
        use_password=True)

    request = RequestXml()
    request.set_auth_token(token)
    request.add_request('GetFilterRulesRequest', {}, 'urn:zimbraMail')

    response = ResponseXml()
    comm = Communication(url)
    comm.send_request(request, response)

    if not response.is_fault():
        rules = response.get_response()['GetFilterRulesResponse']
        print 'require ["fileinto"];\n'
        for rule in rules['filterRules']['filterRule']:
            display_rule(rule)
            print

if __name__ == '__main__':
    main()
