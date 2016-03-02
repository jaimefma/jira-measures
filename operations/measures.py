# -*- coding: utf-8 -*-

import datetime
import tempfile
import webbrowser
from dateutil import rrule, parser
from jira import JIRA
from credentials import USER, PASS


SERVER = 'https://paradigma.atlassian.net'

jira = JIRA(basic_auth=(USER, PASS), options={'server': SERVER})


class Issue(object):
    def __init__(self, **kargs):
        [setattr(self, field, value)for field, value in kargs.items()]


########################################################################################################################
def get_date_issue_stared_in_sprint(issue_name):
    issue = jira.issue(issue_name, expand='changelog')
    started_in_sprint = issue.fields.created
    print issue_name
    for h in issue.changelog.histories:
        info = h.items[0]
        if getattr(info, 'field', '') == 'priority' and getattr(info, 'to', '') in ['1', '2']:
            started_in_sprint = h.created
    return parser.parse(started_in_sprint)


def sprint_issues(from_date=None):
    issues = jira.search_issues('project=PL AND (priority=Highest or priority=High) AND status != Closed ORDER BY created ASC')

    sp_issues = []
    for issue in issues:
        i = Issue(**{'into_sprint_date': get_date_issue_stared_in_sprint(issue.key),
                     'priority': issue.fields.priority,
                     'key': issue.key})
        if (from_date and i.into_sprint_date.date() >= from_date) or not from_date:
            sp_issues.append(i)

    return sorted(sp_issues, key=lambda x: x.into_sprint_date)


def creation_highest_issues(starting_date=None):
    his = sprint_issues(starting_date)

    start_at = his[0].into_sprint_date.date()
    finish_at = his[-1].into_sprint_date.date()
    print "Range {} ({}) - {} ({})".format(start_at, his[0].key, finish_at, his[-1].key)

    day_range = list(rrule.rrule(rrule.DAILY, dtstart=start_at, until=finish_at))

    # structure for chart
    # print day_range
    data = {d.date(): [] for d in day_range}
    print sorted(data.keys())
    [data[h.into_sprint_date.date()].append(h) for h in his]

    template = open('highest_issues.html', 'r')
    # tmp_file = tempfile.mktemp(suffix='.html')
    tmp_file = '/tmp/tmpfrnU21.html'
    destination = open(tmp_file, 'w')
    for row in template.readlines():
        if "DATA_TO_REPLACE" in row:
            # Header
            # destination.write(u'["Dia", "Numero de incidencias abiertas"],\n')
            for a_day in day_range:
                # destination.write('[{}, {}],\n'.format(d.day, len(data[d.date()])))
                issues = data[a_day.date()]
                high_priority = len([i for i in issues if i.priority.name == 'High'])  # High
                highest_priority = len([i for i in issues if i.priority.name == 'Highest'])  # Highest
                destination.write('[new Date({},{},{}), {}, {}],\n'.format(a_day.year, a_day.month - 1, a_day.day, high_priority, highest_priority))
        else:
            destination.write(row)
    print tmp_file


########################################################################################################################
def operational_issues():
    issues = jira.search_issues('project=AIL AND created > "-1w" ORDER BY created ASC', expand='changelog')

    issues = [Issue(**{'created': parser.parse(i.fields.created)}) for i in issues]

    tmp_file = '/tmp/ail_issues.html'

if __name__ == '__main__':
    start = datetime.date(2016, 2, 1)
    creation_highest_issues(start)