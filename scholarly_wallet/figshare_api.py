from scholarly_wallet import mongo_access as mongo, config, logger
import urllib.request
import urllib.parse
import json
import tempfile
import os
import zipfile


def authenticate(auth_code, orcid_id):
    user_data = mongo.get_user(orcid_id)
    if 'figshare_token' not in user_data and auth_code is not None:
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
    elif 'figshare_token' in user_data:
        figshare_token = user_data['figshare_token']
    else:
        figshare_token = None
    return figshare_token['access_token']


def get_articles(access_token, orcid):
    req = urllib.request.Request('https://api.figshare.com/v2/account/articles',
                                 headers={'Accept': 'application/json',
                                          'Authorization': 'token ' + access_token})
    response = urllib.request.urlopen(req)
    articles_data = json.loads(response.read())
    for article in articles_data:
        article['claimed'] = mongo.article_exists(article['url'], orcid)
    return [article for article in articles_data if not article['claimed']]


def download_files(figshare_ro, access_token, file_name):
    req = urllib.request.Request(figshare_ro['url'] + '/files',
                                 headers={'Accept': 'application/json',
                                          'Authorization': 'token ' + access_token})
    response = urllib.request.urlopen(req)
    figshare_files = json.loads(response.read())
    with tempfile.TemporaryDirectory() as tmpdirname:
        logger.info('Created temporary directory for Figshare files: ', tmpdirname)
        for figshare_file in figshare_files:
            logger.info('Trying to get: ', figshare_file)
            req = urllib.request.Request(figshare_file['download_url'],
                                         headers={'Authorization': 'token ' + access_token})
            response = urllib.request.urlopen(req)
            figshare_file_content = response.read()
            with open(tmpdirname + '/' + figshare_file['name'], 'wb') as f:
                f.write(figshare_file_content)
        logger.info('Trying to compress: ', file_name)
        zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)
        zip_dir(tmpdirname, zipf)
        zipf.close()


def zip_dir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), file)

