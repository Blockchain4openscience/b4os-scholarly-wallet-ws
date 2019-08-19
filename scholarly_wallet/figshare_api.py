from scholarly_wallet import mongo_access as mongo, config
import urllib.request
import urllib.parse
import json


def authenticate(auth_code, orcid_id):
    user_data = mongo.get_user(orcid_id)
    if 'figshare_token' not in user_data:
        params = {'client_id': config.get('DEFAULT', 'FIGSHARE_CLIENT_ID'),
                  'client_secret': config.get('DEFAULT', 'FIGSHARE_SECRET'),
                  'grant_type': 'authorization_code',
                  'code': auth_code
                  }
        data = urllib.parse.urlencode(params)
        data = data.encode('ascii')
        req = urllib.request.Request(config.get('DEFAULT', 'FIGSHARE_TOKEN_URL'), data=data,
                                     headers={'Accept': 'application/json'})
        req.get_method = lambda: "POST"
        response = urllib.request.urlopen(req).read()
        figshare_token = json.loads(response)
        user_data['figshare_token'] = figshare_token
        mongo.update_user(orcid_id, user_data)
    else:
        figshare_token = user_data['figshare_token']
    return figshare_token['access_token']


def get_articles(access_token, orcid):
    req = urllib.request.Request('https://api.figshare.com/v2/account/articles',
                                 headers={'Accept': 'application/json', 'Authorization': 'token ' + access_token})
    response = urllib.request.urlopen(req)
    articles_data = json.loads(response.read())
    for article in articles_data:
        article['claimed'] = mongo.article_exists(article['url'], orcid)
    return [article for article in articles_data if not article['claimed']]
