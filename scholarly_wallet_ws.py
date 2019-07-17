from flask import Flask, request, jsonify, json
import urllib
from pymongo import MongoClient
from typing import Dict

app = Flask(__name__)


@app.route("/auth/orcid", methods=['GET', 'OPTIONS'])
def signin():
    auth_code = request.args.get('orcid_auth_code')
    params = {'client_id': '',
              'client_secret': '',
              'grant_type': 'authorization_code',
              'code': auth_code,
              'redirect_uri': 'http://localhost:4200/main/login'
              }
    data = urllib.parse.urlencode(params)
    data = data.encode('ascii')
    req = urllib.request.Request('https://orcid.org/oauth/token', data,
                                 headers={'Accept': 'application/json'})
    response = urllib.request.urlopen(req).read()
    user_data: Dict = json.loads(response)
    user_data.pop('access_token')
    user_data.pop('token_type')
    user_data.pop('refresh_token')
    user_data.pop('expires_in')
    user_data.pop('scope')
    if not user_exists(user_data['orcid']):
        create_user(user_data)
        user_data.pop('_id')
    return jsonify(user_data)


def user_exists(orcid):
    client = MongoClient()
    db = client.sw
    collection = db.users
    user = collection.find_one({'orcid': orcid})
    return user is not None


def create_user(user):
    print(user)
    client = MongoClient()
    db = client.sw
    collection = db.users
    collection.insert_one(user)
    print(user)


@app.route('/auth/github', methods=['GET', 'OPTIONS'])
def github_auth():
    auth_code = request.args.get('code')
    orcid = request.args.get('orcid')
    params = {'client_id': '',
              'client_secret': '',
              'code': auth_code
              }
    data = urllib.parse.urlencode(params)
    data = data.encode('ascii')
    req = urllib.request.Request('https://github.com/login/oauth/access_token', data,
                                 headers={'Accept': 'application/json'})
    response = urllib.request.urlopen(req).read()
    user_data = json.loads(response)
    repositories = get_repositories(user_data['access_token'], orcid)
    return jsonify(repositories)


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
        repo['claimed'] = repo_exists(repo['html_url'])
    return [repo for repo in repos_data if not repo['claimed']]


@app.route('/ro/claim', methods=['POST', 'OPTIONS'])
def claim_ro():
    repositories = request.get_json()
    orcid = request.args.get('orcid')
    for repository in repositories:
        repository['claimed'] = True
        repository['orcid'] = orcid
    save_ros(repositories)
    for repository in repositories:
        repository.pop('_id')
    return jsonify(repositories)


@app.route('/ro/list', methods=['GET', 'OPTIONS'])
def list_ros():
    orcid = request.args.get('orcid')
    ros = get_claimed(orcid)
    return jsonify(ros)


def repo_exists(html_url):
    client = MongoClient()
    db = client.sw
    collection = db.ros
    ro = collection.find_one({'html_url': html_url})
    return ro is not None


def get_claimed(orcid):
    client = MongoClient()
    db = client.sw
    collection = db.ros
    ros = collection.find({'orcid': orcid})
    claimed = []
    for ro in ros:
        ro.pop('_id', None)
        claimed.append(ro)
    return claimed


def save_ros(ros):
    client = MongoClient()
    db = client.sw
    collection = db.ros
    collection.insert_many(ros)

# def repo_exists(repo_url, orcid):
#     sparql = SPARQLWrapper(conf.SPARQL_QUERY_ENDPOINT)
#     orcid = 'http://orcid.org/' + orcid
#     query = sparqlt.RO_EXIST.format(orcid=orcid, share_url=repo_url)
#     sparql.setQuery(query)
#     sparql.setReturnFormat(JSON)
#     return bool(sparql.query().convert()['boolean'])


if __name__ == '__main__':
    app.run(debug=True, port=8000, host='0.0.0.0')
