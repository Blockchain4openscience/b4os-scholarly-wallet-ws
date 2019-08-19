from scholarly_wallet import mongo_access as mongo, config
import urllib.request
import urllib.parse
import json


def authenticate(auth_code, orcid_id):
    user_data = mongo.get_user(orcid_id)
    if 'github_token' not in user_data:
        params = {'client_id': config.get('DEFAULT', 'GITHUB_CLIENT_ID'),
                  'client_secret': config.get('DEFAULT', 'GITHUB_SECRET'),
                  'code': auth_code
                  }
        data = urllib.parse.urlencode(params)
        data = data.encode('ascii')
        req = urllib.request.Request('https://github.com/login/oauth/access_token', data,
                                     headers={'Accept': 'application/json'})
        response = urllib.request.urlopen(req).read()
        github_token = json.loads(response)
        user_data['github_token'] = github_token
        mongo.update_user(orcid_id, user_data)
    else:
        github_token = user_data['github_token']
    return github_token['access_token']


def get_repositories(access_token, orcid):
    req = urllib.request.Request('https://api.github.com/user?access_token=' + access_token,
                                 headers={'Accept': 'application/json'})
    response = urllib.request.urlopen(req)
    user_data = json.loads(response.read())

    req = urllib.request.Request(user_data['repos_url'],
                                 headers={'Accept': 'application/json'})
    response = urllib.request.urlopen(req)
    repos_data = json.loads(response.read())
    for repo in repos_data:
        repo['claimed'] = mongo.repo_exists(repo['html_url'], orcid)
    return [repo for repo in repos_data if not repo['claimed']]