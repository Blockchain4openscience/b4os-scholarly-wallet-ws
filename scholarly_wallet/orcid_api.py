import urllib
from typing import Dict
import json
from scholarly_wallet import config
from scholarly_wallet import mongo_access as mongo
import urllib.request
import urllib.parse
import orcid


def authenticate(auth_code):
    params = {'client_id': config.get('DEFAULT', 'ORCID_CLIENT_ID'),
              'client_secret': config.get('DEFAULT', 'ORCID_SECRET'),
              'grant_type': 'authorization_code',
              'code': auth_code,
              'redirect_uri': config.get('DEFAULT', 'CLIENT_URL')
              }
    data = urllib.parse.urlencode(params)
    data = data.encode('ascii')
    req = urllib.request.Request(config.get('DEFAULT', 'ORCID_AUTH_URL'), data,
                                 headers={'Accept': 'application/json'})
    try:
        response = urllib.request.urlopen(req).read()
        user_data: Dict = json.loads(response)

        orcid_token = {
            'access_token': user_data.pop('access_token'),
            'token_type': user_data.pop('token_type'),
            'refresh_token': user_data.pop('refresh_token'),
            'expires_in': user_data.pop('expires_in'),
            'scope': user_data.pop('scope'),
        }
        user_data['orcid_token'] = orcid_token

        if not mongo.user_exists(user_data['orcid']):
            mongo.create_user(user_data)
            user_data.pop('_id')
        else:
            mongo.update_user(user_data['orcid'], user_data)
        works = get_works(user_data['orcid_token']['access_token'], user_data['orcid'])
        for work in works:
            if not mongo.work_exists(work['id'], user_data['orcid']):
                mongo.save_ros([work], 'orcid')
        for field_name in user_data.keys():
            if field_name.endswith('_token'):
                user_data[field_name.replace('_token', '_access')] = True
                user_data.pop(field_name)
        return user_data

    except urllib.error.HTTPError as e:
        return None


def get_works(user_token, orcid_id):
    api = orcid.PublicAPI(config.get('DEFAULT', 'ORCID_CLIENT_ID'),
                          config.get('DEFAULT', 'ORCID_SECRET'))
    summary = api.read_record_public(orcid_id, 'works', user_token)
    metadata = []
    for work in summary['group']:
        work_summary = work['work-summary'][0]
        work_metadata = dict()
        work_metadata['id'] = work_summary['put-code']
        work_metadata['title'] = work_summary['title']['title']['value']
        work_metadata['last-modified-date'] = work_summary['last-modified-date']['value']
        work_metadata['type'] = work_summary['type']
        work_metadata['publication-year'] = work_summary['publication-date']['year']['value']
        work_metadata['owner'] = orcid_id

        for ext_id in work_summary['external-ids']['external-id']:
            if ext_id['external-id-type'] == 'doi':
                work_metadata['doi'] = ext_id['external-id-value']
            if ext_id['external-id-type'] == 'pmid':
                work_metadata['pmid'] = ext_id['external-id-value']
            if ext_id['external-id-type'] == 'pmc':
                work_metadata['pmcid'] = ext_id['external-id-value']

        metadata.append(work_metadata)
    return metadata
