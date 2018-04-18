#!/usr/bin/env python
import csv
import json
import requests
import datetime
from datetime import datetime
import re

"""
Exports Issues from a list of repositories to individual CSV files
Uses basic authentication (Github API Token and Zenhub API Token)
to retrieve Issues from a repository that token has access to.
Supports Github API v3 and ZenHubs current working API.
Derived from https://gist.github.com/Kebiled/7b035d7518fdfd50d07e2a285aff3977
"""

def write_issues(r, csvout, repo_name, repo_ID):
    if not r.status_code == 200:
        raise Exception(r.status_code)

    r_json = r.json()
    # print r_json
    print(json.dumps(r_json, indent=2))

    for issue in r_json:
        print repo_name + ' issue Number: ' + str(issue['number'])
        zenhub_issue_url = 'https://api.zenhub.io/p1/repositories/' + \
            str(repo_ID) + '/issues/' + str(issue['number']) + ACCESS_TOKEN
        zen_r = requests.get(zenhub_issue_url).json()
        global Payload
        print(json.dumps(zen_r, indent=2))

        if 'pull_request' not in issue:
            global ISSUES
            ISSUES += 1
            sAssigneeList = ''
            labels = ''
            sCategory = ''
            sPriority = ''

            for i in issue['assignees'] if issue['assignees'] else []:
                sAssigneeList += i['login'] + ','

            for x in issue['labels'] if issue['labels'] else []:
                labels += x['name'] + ','

            # for x in issue['labels'] if issue['labels'] else []:
            #     if "Category" in x['name']:
            #         sCategory = x['name']
            #     if "Tag" in x['name']:
            #         Labels = x['name']
            #     if "Priority" in x['name']:
            #         sPriority = x['name']
            estimacion = zen_r.get('estimate', dict()).get('value', "")
            estado    = zen_r.get('pipeline', dict()).get('name', "" )


            # Horas trabajadas: <hours>5</hours>
            # Horas trabajadas: <hours>5</hours>
            # Horas trabajadas: <hours>5</hours>
            print issue['closed_at']
            csvout.writerow([getRepoName(repo_name),
                             issue['number'],
                             issue['title'].encode('utf-8'),
                             issue['milestone']['title'] if issue['milestone'] else "",
                             estado,
                             getDate(issue['closed_at']),
                             estimacion,
                             getWorkingHours(issue['body'])
                             # sCategory,
                             # labels[:-1],
                             # sPriority,
                             # issue['user']['login'],
                             # issue['created_at'],
                             # sAssigneeList[:-1],
                             # issue['body'].encode('utf-8'),
                             ])
        else:
            print 'You have skipped %s Pull Requests' % ISSUES


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

def get_issues(repo_data):
    repo_name = repo_data[0]
    repo_ID = repo_data[1]
    # all issues
    issues_for_repo_url = 'https://api.github.com/repos/%s/issues?state=all' % repo_name
    # open issues
    # issues_for_repo_url = 'https://api.github.com/repos/%s/issues' % repo_name
    r = requests.get(issues_for_repo_url, auth=AUTH_TOKEN_GITHUB)
    write_issues(r, FILEOUTPUT, repo_name, repo_ID)
    # more pages? examine the 'link' header returned
    if 'link' in r.headers:
        pages = dict(
            [(rel[6:-1], url[url.index('<') + 1:-1]) for url, rel in
             [link.split(';') for link in
              r.headers['link'].split(',')]])
        while 'last' in pages and 'next' in pages:
            pages = dict(
                [(rel[6:-1], url[url.index('<') + 1:-1]) for url, rel in
                 [link.split(';') for link in
                  r.headers['link'].split(',')]])
            r = requests.get(pages['next'], auth=AUTH_TOKEN_GITHUB)
            write_issues(r, FILEOUTPUT, repo_name, repo_ID)
            if pages['next'] == pages['last']:
                break

    FILEOUTPUT.writerow(['Total', ISSUES])




PAYLOAD = ""
# all repos
# ('username/reponame', zenhubID )  get the zenhub id from the url
REPO_LIST = [("Doskapi/Tdp2-Android", "125941072"), ("Doskapi/Tdp2-Node", "125941349"), ("guillerecalde/tdp2-angular", "127685368")]

# https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
AUTH_TOKEN_GITHUB = ('token', 'REPLACE WITH YOUR TOKEN')

# https://github.com/ZenHubIO/API#authentication
ACCESS_TOKEN_ZENHUB = '?access_token=<Zenhub TOKEN>'

ISSUES = 0

FILENAME = 'output.csv'
OPENFILE = open(FILENAME, 'wb')
FILEOUTPUT = csv.writer(OPENFILE)

# define header of the csv
FILEOUTPUT.writerow((
         'Categoria',
         'Issue',
         'Funcionalidad',
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


for repo_data in REPO_LIST:
    get_issues(repo_data)
OPENFILE.close()



