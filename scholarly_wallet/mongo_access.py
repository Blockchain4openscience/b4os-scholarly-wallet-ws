from bson import ObjectId
from pymongo import MongoClient


def user_exists(orcid):
    client = MongoClient()
    db = client.sw
    collection = db.users
    user = collection.find_one({'orcid': orcid})
    return user is not None


def get_user(orcid):
    client = MongoClient()
    db = client.sw
    collection = db.users
    user = collection.find_one({'orcid': orcid})
    return user


def create_user(user):
    client = MongoClient()
    db = client.sw
    collection = db.users
    return collection.insert_one(user)


def update_user(orcid, changes):
    client = MongoClient()
    db = client.sw
    collection = db.users
    return collection.update_one({'orcid': orcid}, {'$set': changes})


def repo_exists(html_url, orcid_id=None):
    client = MongoClient()
    db = client.sw
    collection = db.github
    if orcid_id is None:
        ro = collection.find_one({'html_url': html_url})
    else:
        ro = collection.find_one({'html_url': html_url, 'owner': orcid_id})
    return ro is not None


def article_exists(article_url, orcid_id=None):
    client = MongoClient()
    db = client.sw
    collection = db.figshare
    if orcid_id is None:
        ro = collection.find_one({'url': article_url})
    else:
        ro = collection.find_one({'url': article_url, 'owner': orcid_id})
    return ro is not None


def work_exists(work_id, orcid_id=None):
    client = MongoClient()
    db = client.sw
    collection = db.orcid
    if orcid_id is None:
        ro = collection.find_one({'id': work_id})
    else:
        ro = collection.find_one({'id': work_id, 'owner': orcid_id})
    return ro is not None


def get_claimed(orcid, source, sort_field, start=None, size=None):
    client = MongoClient()
    db = client.sw
    collection = db[source]
    if start is None or size is None:
        ros = collection.find({'owner': orcid}).sort(sort_field)
    else:
        ros = collection.find({'owner': orcid}).sort(sort_field).skip(start).limit(size)
    claimed = []
    for ro in ros:
        ro.pop('_id', None)
        claimed.append(ro)
    return claimed


def count_claimed(orcid, source):
    client = MongoClient()
    db = client.sw
    collection = db[source]
    return collection.count_documents({'owner': orcid})


def save_ros(ros, source):
    client = MongoClient()
    db = client.sw
    collection = db[source]
    return collection.insert_many(ros)


def save_disco(orcid_id, disco):
    client = MongoClient()
    db = client.sw
    collection = db.discos
    return collection.insert_one({'owner': orcid_id, **disco}).inserted_id


def update_disco(orcid_id, disco_id, disco):
    client = MongoClient()
    db = client.sw
    collection = db.discos
    disco = {'owner': orcid_id, **disco}
    return collection.update_one({'owner': orcid_id, '_id': ObjectId(disco_id)}, {'$set': disco})


def get_disco(orcid_id, disco_id):
    client = MongoClient()
    db = client.sw
    collection = db.discos
    disco = collection.find_one({'owner': orcid_id, '_id': ObjectId(disco_id)})
    return disco


def get_discos(orcid_id, start=None, size=None):
    client = MongoClient()
    db = client.sw
    collection = db.discos
    if start is None or size is None:
        discos = collection.find({'owner': orcid_id}).sort('name')
    else:
        discos = collection.find({'owner': orcid_id}).sort('name').skip(start).limit(size)
    all_discos = []
    for disco in discos:
        disco['id'] = str(disco.pop('_id', None))
        all_discos.append(disco)
    return all_discos


def count_discos(orcid_id):
    client = MongoClient()
    db = client.sw
    collection = db.discos
    return collection.count_documents({'owner': orcid_id})