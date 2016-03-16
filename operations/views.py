# -*- coding: utf-8 -*-
from copy import deepcopy

import datetime
from collections import OrderedDict

from dateutil import parser, rrule, relativedelta

from jira import JIRA

from django.conf import settings
from django.shortcuts import render

from . import Issue
# Create your views here.

jira = JIRA(basic_auth=(settings.JIRA_USER, settings.JIRA_PASS), options={'server': settings.JIRA_SERVER})


def ail_measures(request):
    issues = jira.search_issues('project=AIL AND created > -2w ORDER BY created ASC', expand='changelog', maxResults=1000)

    assert issues.total <= 1000

    data = {}

    for i in issues:
        key = parser.parse(i.fields.created).date()
        val = data.setdefault(key, {'created': 0, 'resolved': 0, 'blocked': 0})
        val['created'] += 1

        # Inspect history
        for h in i.changelog.histories:
            if h.items[0].field == 'status':
                key = parser.parse(h.created).date()

                if h.items[0].to == '5':
                    val = data.setdefault(key, {'created': 0, 'resolved': 0, 'blocked': 0})
                    val['resolved'] += 1
                elif h.items[0].to == '4':
                    val = data.setdefault(key, {'created': 0, 'resolved': 0, 'blocked': 0})
                    val['blocked'] += 1

    data = OrderedDict(sorted(data.items()))
    print(data)
    return render(request, 'ail_charts.html', locals())


OPEN_ID = '1'
REOPENED_ID = '4'
BLOCKED_ID = '10000'
RESOLVED_ID = '5'
CLOSED_ID = '6'

STATUS_MAP = {
    OPEN_ID: 'open',
    REOPENED_ID: 'reopened',
    BLOCKED_ID: 'blocked',
    RESOLVED_ID: 'resolved',
    CLOSED_ID: 'closed',
}

default = {'open': [], 'reopened': [], 'resolved': [], 'blocked': [], 'created': [], 'closed': []}


def insert_issue_status(data, date, status_id, issue_info):
    val = data.setdefault(date, deepcopy(default))
    val[STATUS_MAP[status_id]].append(issue_info)


def print_issue_trace(data, issue_key):
    """
    Tool for debug
    """
    def issue_evolution(data, id):
        for date, val in data.items():
            for status, ids in val.items():
                if id in ids:
                    yield (date, status)
    return sorted([i for i in issue_evolution(data, issue_key)])


def process_issues(issues):
    data = {}

    for i in issues:
        i_creation_date = parser.parse(i.fields.created).date()
        print("Processing", i.key, i_creation_date, i.fields.created)
        val = data.setdefault(i_creation_date, deepcopy(default))
        val['created'].append(i.key)

        last_status = OPEN_ID
        last_status_date = i_creation_date
        # Inspect history
        for h in i.changelog.histories:
            if h.items[0].field == 'status':

                if h.items[0].to in STATUS_MAP.keys():
                    hist_date = parser.parse(h.created).date()

                    # Add resolution information
                    if h.items[0].to == CLOSED_ID:
                        insert_issue_status(data, hist_date, h.items[0].to, (i.key, i_creation_date))
                        # val[STATUS_MAP[h.items[0].to]].append((i.key, i_creation_date))
                    else:
                        insert_issue_status(data, hist_date, h.items[0].to, i.key)
                        # val[STATUS_MAP[h.items[0].to]].append(i.key)
                    print(i.key, STATUS_MAP[h.items[0].to], hist_date)

                    # fill intermediate dates
                    if last_status in [OPEN_ID, REOPENED_ID]:
                        i_day = last_status_date + relativedelta.relativedelta(days=1)
                        while i_day <= hist_date:
                            insert_issue_status(data, i_day, OPEN_ID, i.key)
                            i_day += relativedelta.relativedelta(days=1)
                    last_status_date = hist_date
                    last_status = h.items[0].to

        print(i.key, i_creation_date, hist_date)
    return data


def ail_measures2(request):
    end_date = datetime.date.today()
    start_date = end_date - relativedelta.relativedelta(weeks=2)

    issues = jira.search_issues('project = AIL AND updated > {} AND updated <= {} ORDER BY created ASC'.format(start_date.strftime('%Y-%m-%d'),
                                                                                                              end_date.strftime('%Y-%m-%d')),
                                expand='changelog', maxResults=1000)
    assert issues.total <= 1000

    data = process_issues(issues)
    print(data)
    date_range = [d.date() for d in rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date + relativedelta.relativedelta(days=1))]

    opened = []
    created = []
    reopened = []
    blocked = []
    resolved = []
    closed = OrderedDict()
    kpis = OrderedDict()

    for date in date_range:

        if date in data:
            v = data[date]

            created_count = len(v['created'])
            open_count = len(v[STATUS_MAP[OPEN_ID]])
            reopened_count = len(v[STATUS_MAP[REOPENED_ID]])
            resolved_count = len(v[STATUS_MAP[RESOLVED_ID]])
            blocked_count = len(v[STATUS_MAP[BLOCKED_ID]])
            closed_count = len(v[STATUS_MAP[CLOSED_ID]])
            close_time = [(date - i[1]).days for i in v[STATUS_MAP[CLOSED_ID]]]

            # print(v[STATUS_MAP[CLOSED_ID]])
            kpis[date] = {
                'solved': 1.0 * closed_count / created_count if created_count else ' - ',
                'time': sum(close_time) / len(close_time) if close_time else ' - ',
                'processed': 1.0 * (blocked_count + resolved_count) / (created_count + open_count + reopened_count) if resolved_count > 0 else 0.0
            }

            created.append(created_count)
            opened.append(open_count)
            reopened.append(reopened_count)
            blocked.append(blocked_count)
            resolved.append(resolved_count)
            closed[date] = (v[STATUS_MAP[CLOSED_ID]])
        else:
            print('Did not happened anything', date)

    return render(request, 'ail_charts2.html', locals())
