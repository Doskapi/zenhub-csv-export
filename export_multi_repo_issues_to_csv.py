#!/usr/bin/env python
import csv
import json
import requests
import datetime
from datetime import datetime
import re
import ConfigParser
from ast import literal_eval as make_tuple


"""
Exports Issues from a list of repositories to individual CSV files
Uses basic authentication (Github API Token and Zenhub API Token)
to retrieve Issues from a repository that token has access to.
Supports Github API v3 and ZenHubs current working API.
Derived from https://gist.github.com/Kebiled/7b035d7518fdfd50d07e2a285aff3977
"""

CONFIG = {
    'CONFIGFILE': 'config',
    'PAYLOAD': '',
    # ('username/reponame', zenhubID )  get the zenhub id from the url
    'REPO_LIST': '',
    # https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
    'AUTH_TOKEN_GITHUB': ('token', 'REPLACE WITH YOUR TOKEN'),
    # https://github.com/ZenHubIO/API#authentication
    'ACCESS_TOKEN_ZENHUB': '?access_token=<Zenhub TOKEN>',
    'ISSUES': 0,
    'FILENAME': 'output.csv'
}


def get_epic_ids(repo_ID, config):
    zenhub_issue_url = 'https://api.zenhub.io/p1/repositories/' + \
            str(repo_ID) + '/epics?access_token='  +  config['ACCESS_TOKEN_ZENHUB']
    zen_r = requests.get(zenhub_issue_url).json()
    epicsIds = []
    for epic in zen_r["epic_issues"]:
        epicsIds.append(epic["issue_number"])
    return epicsIds


def get_epic_related_ids(repo_ID, epic_ID, config):
    zenhub_issue_url = 'https://api.zenhub.io/p1/repositories/' + \
            str(repo_ID) + '/epics/' + str(epic_ID) + '?access_token='  +  config['ACCESS_TOKEN_ZENHUB']
    zen_r = requests.get(zenhub_issue_url).json()
    ids = []
    for related_issue in zen_r["issues"]:
        if (str(related_issue["repo_id"]) == str(repo_ID)):
            ids.append(related_issue["issue_number"])
    return ids


def write_issue(r_json, csvout, repo_name, repo_ID, config):
    print repo_name + ' issue Number: ' + str(r_json['number'])
    zenhub_issue_url = 'https://api.zenhub.io/p1/repositories/' + \
        str(repo_ID) + '/issues/' + str(r_json['number']) + '?access_token='  +  config['ACCESS_TOKEN_ZENHUB']
    zen_r = requests.get(zenhub_issue_url).json()
    if 'pull_request' not in r_json:
        config['ISSUES'] += 1
        sAssigneeList = ''
        labels = ''
        sCategory = ''
        sPriority = ''

        for i in r_json['assignees'] if r_json['assignees'] else []:
            sAssigneeList += i['login'] + ','

        for x in r_json['labels'] if r_json['labels'] else []:
            labels += x['name'] + ','


        # for x in r_json['labels'] if r_json['labels'] else []:
        #     if "Category" in x['name']:
        #         sCategory = x['name']
        #     if "Tag" in x['name']:
        #         Labels = x['name']
        #     if "Priority" in x['name']:
        #         sPriority = x['name']
        estimacion = zen_r.get('estimate', dict()).get('value', "")
        estado = zen_r.get('pipeline', dict()).get('name', "")

        csvout.writerow([getRepoName(repo_name),
                         r_json['number'],
                         r_json['title'].encode('utf-8'),
                         r_json['body'].encode('utf-8'),
                         labels[:-1],
                         r_json['milestone']['title'] if r_json['milestone'] else "",
                         estado,
                         getDate(r_json['closed_at']),
                         estimacion,
                         getWorkingHours(r_json['body'])
                         # sCategory,
                         # sPriority,
                         # r_json['user']['login'],
                         # r_json['created_at'],
                         # sAssigneeList[:-1],
                         ])
    else:
        print 'You have skipped %s Pull Requests' % config['ISSUES']


def write_all_issues(r_json, csvout, repo_name, repo_ID, config):
    for issue in r_json:
        write_issue(issue, csvout, repo_name, repo_ID, config)


def write_issues(r_json, csvout, repo_name, repo_ID, config):
    if isinstance(r_json, list):
        write_all_issues(r_json, csvout, repo_name, repo_ID, config)
    else:
        write_issue(r_json, csvout, repo_name, repo_ID, config)


def getRepoName(repo):
    return {
        'Doskapi/Tdp2-Android': 'Android',
        'Doskapi/Tdp2-Node': 'NodeJs',
        'guillerecalde/tdp2-angular': 'Backoffice',
    }.get(repo, '')


def getDate(date):
    if date:
        # format: 2018-04-16T23:33:47Z
        d = datetime.strptime(date[:-1], '%Y-%m-%dT%H:%M:%S')
        return d.strftime('%Y-%m-%d')
    return ''


def getWorkingHours(issue_body):
    hours = re.search("<hours>(.+?)</hours>", issue_body)
    if hours:
        return hours.group(1)
    return ''


def get_issues(repo_name, repo_zenhub_id, epicsIds, config):
    for epic in epicsIds:
        epic_issue_url = 'https://api.github.com/repos/' + repo_name + '/issues/' + str(epic)
        r_epic = requests.get(epic_issue_url, auth=config['AUTH_TOKEN_GITHUB'])
        if not r_epic.status_code == 200:
            raise Exception(r_epic.status_code)
        # print(json.dumps(r_epic.json(), indent=2))
        write_issues(r_epic.json(), config['FILEWRITER'], repo_name, repo_zenhub_id, config)

        related_issues = get_epic_related_ids(repo_zenhub_id, epic, config)

        for issue in related_issues:
            issue_url = 'https://api.github.com/repos/' + repo_name + '/issues/' + str(issue)
            r_issue = requests.get(issue_url, auth=config['AUTH_TOKEN_GITHUB'])
            if not r_issue.status_code == 200:
                raise Exception(r_issue.status_code)
            write_issues(r_issue.json(), config['FILEWRITER'], repo_name, repo_zenhub_id, config)


def parseConfigs():
    configParser = ConfigParser.ConfigParser()
    configParser.readfp(open(CONFIG['CONFIGFILE']))
    CONFIG['AUTH_TOKEN_GITHUB'] = ('token', configParser.get('apiTokens', 'AUTH_TOKEN_GITHUB'))
    CONFIG['ACCESS_TOKEN_ZENHUB'] = configParser.get('apiTokens', 'ACCESS_TOKEN_ZENHUB')
    CONFIG['FILENAME'] = configParser.get('filename', 'FILENAME')
    repos = configParser.items('repos')
    CONFIG['REPO_LIST'] = []
    for x in repos:
        CONFIG['REPO_LIST'].append((x[1].split(',')[0],x[1].split(',')[1]))


if __name__ == '__main__':
    parseConfigs()
    CONFIG['OPENFILE'] = open(CONFIG['FILENAME'], 'wb')
    CONFIG['FILEWRITER'] = csv.writer(CONFIG['OPENFILE'])
    # define header of the csv
    CONFIG['FILEWRITER'].writerow((
        'Categoria',
        'Issue',
        'Funcionalidad',
        'Descriocion',
        'Labels',
        'Iteracion',
        'Estado',
        'Fecha de Finalizacion',
        'Estimacion',
        'Horas Tabajadas',
        'Tag',
        'Priority',
        'Pipeline',
        'Issue Author',
        'Created At',
        'Milestone',
        'Assigned To',
        'Issue Content',
        'Estimate Value'))

    for repo_data in CONFIG['REPO_LIST']:
        epicIds = get_epic_ids(repo_data[1], CONFIG)
        get_issues(repo_data[0], repo_data[1], epicIds, CONFIG)

    CONFIG['OPENFILE'].close()
