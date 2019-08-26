import requests
from scholarly_wallet import config, logger
from datetime import datetime
import json

SOURCE_TYPE_MAP = {"orcid": "DOCUMENT", "figshare": "DATASET", "github": "CODE"}
SOURCE_URL_FIELD_MAP = {"orcid": "doi", "figshare": "url", "github": "html_url"}


def create_researcher(user):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    researcher = {
        "$class": "org.bforos.Researcher",
        "researcherId": f"{user['orcid']}",
        "firstName": user["first_name"],
        "lastName": user["last_name"],
        "email": f"{user['orcid']}@b4os.com",
    }
    req = requests.post(f"{composer_url}/api/Researcher", researcher)
    return True


def create_reaserch_object(orcid_id, source, research_object):
    ro_type = SOURCE_TYPE_MAP[source] if source in SOURCE_TYPE_MAP else "OTHER"
    research_object_url = (
        research_object[SOURCE_URL_FIELD_MAP[source]]
        if SOURCE_URL_FIELD_MAP[source] in research_object
        else research_object["id"]
    )
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    create_op = {
        "$class": "org.bforos.CreateResearchOJ",
        "typeRO": ro_type,
        "uri": research_object_url,
        "creator": f"org.bforos.Researcher#{orcid_id}",
        "researchObjId": research_object_url,
    }
    req = requests.post(f"{composer_url}/api/CreateResearchOJ", create_op)
    return True


def claim_research_object(orcid_id, source, research_object):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    research_object_url = (
        research_object[SOURCE_URL_FIELD_MAP[source]]
        if SOURCE_URL_FIELD_MAP[source] in research_object
        else research_object["id"]
    )
    claim_op = {
        "$class": "org.bforos.ClaimRO",
        "researchObjId": f"resource:org.bforos.ResearchOJ#{research_object_url}",
        "claimer": f"resource:org.bforos.Researcher#{orcid_id}",
    }
    req = requests.post(f"{composer_url}/api/CreateResearchOJ", claim_op)
    return True


def create_disco_transaction(orcid_id, disco_id, disco_name, research_object_urls):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    bforos_ros = [
        f"resource:org.bforos.ResearchOJ#{url}" for url in research_object_urls
    ]
    timestamp = str(datetime.now())
    create_disco_op = {
        "$class": "org.bforos.CreateDisco",
        "discoId": disco_id,
        "title": disco_name,
        "researchObjs": bforos_ros,
        "creator": f"org.bforos.Researcher#{orcid_id}",
        "timestamp": timestamp,
    }
    logger.info(create_disco_op)
    headers = {"Content-Type": "application/json"}
    req = requests.post(f"{composer_url}/api/CreateDisco", json.dumps(create_disco_op), headers=headers)
    logger.info(req.text)
    return True


def create_disco(orcid_id, disco_id, disco_name, research_object_urls):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    bforos_ros = [
        f"resource:org.bforos.ResearchOJ#{url}" for url in research_object_urls
    ]
    create_disco_op = {
        "$class": "org.bforos.Disco",
        "discoId": disco_id,
        "title": disco_name,
        "researchObjs": bforos_ros,
        "owner": f"org.bforos.Researcher#{orcid_id}",
        "collectors": [f"org.bforos.Researcher#{orcid_id}"],
    }
    logger.info(create_disco_op)
    headers = {"Content-Type": "application/json"}
    req = requests.post(f"{composer_url}/api/Disco", json.dumps(create_disco_op), headers=headers)
    logger.info(req.text)
    return True


def update_disco(orcid_id, disco_id, disco_name, research_object_urls):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    bforos_ros = [
        f"resource:org.bforos.ResearchOJ#{url}" for url in research_object_urls
    ]
    create_disco_op = {
        "$class": "org.bforos.Disco",
        "discoId": disco_id,
        "title": disco_name,
        "researchObjs": bforos_ros,
        "owner": f"org.bforos.Researcher#{orcid_id}",
    }
    req = requests.put(f"{composer_url}/api/Disco", create_disco_op)
    return True


def research_object_exist(source, research_object):
    composer_url = config.get("DEFAULT", "HYPERLEDGER_COMPOSER_URL")
    research_object_url = (
        research_object[SOURCE_URL_FIELD_MAP[source]]
        if SOURCE_URL_FIELD_MAP[source] in research_object
        else research_object["id"]
    )
    req = requests.get(f"{composer_url}/ResearchOJ/{research_object_url}")
    if req.status_code == 404:
        return False
    return True


def claim_ros(orcid_id, source, repositories):
    for repository in repositories:
        id = repository.pop("_id") if '_id' in repository else None
        if not research_object_exist(source, repository):
            create_reaserch_object(orcid_id, source, repository)
        claim_research_object(orcid_id, source, repository)
