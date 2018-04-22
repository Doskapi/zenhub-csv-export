#!/usr/bin/env python
# coding: utf-8

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
        if str(related_issue["repo_id"]) == str(repo_ID):
            ids.append(related_issue["issue_number"])
    return ids


def write_issue(r_json, csvout, repo_name, repo_ID, config):

    labels = ''
    is_epic = ''
    for x in r_json['labels'] if r_json['labels'] else []:
        labels += x['name'] + ','
        if 'Epic' == x['name']:
            is_epic = x['name']

    if is_epic != '':
        print repo_name + ' issue Number: ' + str(r_json['number']) + " - Epic"
    else:
        print repo_name + ' issue Number: ' + str(r_json['number'])

    zenhub_issue_url = 'https://api.zenhub.io/p1/repositories/' + \
        str(repo_ID) + '/issues/' + str(r_json['number']) + '?access_token='  +  config['ACCESS_TOKEN_ZENHUB']
    zen_r = requests.get(zenhub_issue_url).json()

    if 'pull_request' not in r_json:
        config['ISSUES'] += 1
        estimacion = zen_r.get('estimate', dict()).get('value', "")
        estado = zen_r.get('pipeline', dict()).get('name', "")

        assignee_hours = getAssignieHours(r_json)
        total_hours = getTotalWorkingHours(assignee_hours)

        csvout.writerow([
                         getId(repo_name, r_json['number']),
                         getRepoName(repo_name),
                         r_json['title'].encode('utf-8'),
                         getBody(r_json['body'].encode('utf-8')),
                         is_epic,
                         labels[:-1],
                         r_json['milestone']['title'] if r_json['milestone'] else "",
                         getPriority(r_json['body']),
                         estado,
                         getDate(r_json['closed_at']),
                         estimacion,
                         assignee_hours['juanmafc'] if 'juanmafc' in assignee_hours else "",
                         assignee_hours['Doskapi'] if 'Doskapi' in assignee_hours else "",
                         assignee_hours['guillerecalde'] if 'guillerecalde' in assignee_hours else "",
                         assignee_hours['florrup'] if 'florrup' in assignee_hours else "",
                         total_hours if total_hours != 0 else "",
                         getPrototype(r_json['body']),
                         getUseCase(r_json['body']),
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

def get_assignees_concatenated(assignees):
    sAssigneeList = ''
    for i in assignees if assignees else []:
        sAssigneeList += i['login'] + ','
    return sAssigneeList

def getId(repo, issue_id):
    return {
        'Doskapi/Tdp2-Android': 'A',
        'Doskapi/Tdp2-Node': 'N',
        'guillerecalde/tdp2-angular': 'B',
    }.get(repo, '') + str(issue_id)


def getDate(date):
    if date:
        # format: 2018-04-16T23:33:47Z
        d = datetime.strptime(date[:-1], '%Y-%m-%dT%H:%M:%S')
        return d.strftime('%Y-%m-%d')
    return ''

def getAssignieHours(r_json):
    assigneeList = {}
    for i in r_json['assignees'] if r_json['assignees'] else []:
        assigneeList[i['login']] = getWorkingHoursUsername(r_json['body'], i['login'])
    userHours = getWorkingHours(r_json['body'])
    if userHours != '' and len(r_json['assignees']) == 1:
        assigneeList[r_json['assignee']['login']] = userHours
    return assigneeList


def getTotalWorkingHours(total_hours_per_assignee):
    sum = 0
    for v in total_hours_per_assignee.values():
        if v != '':
            sum = sum + int(v)
    return sum

#
# <metadata>
# Horas trabajadas: <hours>NUMERO</hours>
# Horas USERNAME: <hoursUSERNAME>NUMERO</hoursUSERNAME>
# Prioridad: <priority>NUMERO</priority>
# Prototipo: <prototype>LINK</prototype>
# Casos de Uso: <usecases>NUMERO CASOS DE USO busca el texto podemos poner los ids 1,2,5,6</usecases>
# </metadata>
# 

def getBody(issue_body):
    return issue_body.partition('<metadata>')[0]

def getWorkingHours(issue_body):
    data = re.search("<hours>(.*?)</hours>", issue_body)
    if data:
        return data.group(1)
    return ''

def getWorkingHoursUsername(issue_body, username):
    data = re.search("<hours" + username + ">(.*?)</hours" + username + ">", issue_body)
    if data:
        return data.group(1)
    return ''


def getPriority(issue_body):
    data = re.search("<priority>(.*?)</priority>", issue_body)
    if data:
        return data.group(1)
    return ''


def getPrototype(issue_body):
    data = re.search("<prototype>(.*?)</prototype>", issue_body)
    if data:
        return data.group(1)
    return ''


def getUseCase(issue_body):
    data = re.search("<usecases>(.*?)</usecases>", issue_body)
    if data:
        return data.group(1)
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
        # print(json.dumps(r_epic.json(), indent=2))

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


def createFile():
    CONFIG['FILENAME'] = CONFIG['FILENAME'] + "-" + datetime.now().strftime("%Y%m%d%H%M%S") + ".csv"
    CONFIG['OPENFILE'] = open(CONFIG['FILENAME'], 'wb')
    print "Saving data to: " + CONFIG['FILENAME']

    CONFIG['FILEWRITER'] = csv.writer(CONFIG['OPENFILE'])
    # define header of the csv
    CONFIG['FILEWRITER'].writerow((
        'Id',
        'Categoria',
        'Funcionalidad',
        'Descripcion',
        'Epic?',
        'Labels',
        'Iteracion',
        'Prioridad',
        'Estado',
        'Fecha de Finalizacion',
        'Estimacion',
        'JM',
        'SC',
        'GR',
        'FR',
        'Horas Tabajadas',
        'Prototipo',
        'User Stories',
        ))


def closeFile():
    CONFIG['OPENFILE'].close()


if __name__ == '__main__':
    parseConfigs()
    createFile()
    for repo_data in CONFIG['REPO_LIST']:
        epicIds = get_epic_ids(repo_data[1], CONFIG)
        get_issues(repo_data[0], repo_data[1], epicIds, CONFIG)
    closeFile()

