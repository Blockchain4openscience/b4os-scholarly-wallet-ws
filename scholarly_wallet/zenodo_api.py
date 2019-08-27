import base64
from scholarly_wallet import config, logger
import requests
from bson.json_util import dumps
import json
import scholarly_wallet.mongo_access as mongo
from scholarly_wallet.rmap_api import get_rmap_rdf
import scholarly_wallet.github_api as github
import scholarly_wallet.figshare_api as figshare


def publish_to_zenodo(author, disco):
    turtle = get_rmap_rdf(author, disco)

    zenodo_url = config.get("DEFAULT", "ZENODO_REPOSITIONS_URL")
    zenodo_token = config.get("DEFAULT", "ZENODO_ACCESS_TOKEN")

    headers = {"Content-Type": "application/json"}
    r = requests.post(
        zenodo_url, params={"access_token": zenodo_token}, json={}, headers=headers
    )
    r = r.json()
    deposition_id = r["id"]
    deposition_doi = r["metadata"]["prereserve_doi"]["doi"]
    file_name_base = deposition_doi.replace("/", "_")

    tmp_dir = config.get("DEFAULT", "TMP_DIR")

    with open(tmp_dir + file_name_base + ".rdf", "w+") as t_file:
        t_file.write(turtle.decode("utf-8"))

    turtle_file = open(tmp_dir + deposition_doi.replace("/", "_") + ".rdf", "rb")

    data = {"filename": deposition_doi + ".rdf"}
    files = {"file": turtle_file}
    r = requests.post(
        f"{zenodo_url}/{deposition_id}/files",
        params={"access_token": zenodo_token},
        data=data,
        files=files,
    )

    img_data = base64.b64decode(disco["thumb"].split(",")[1])
    png_file = f"{file_name_base}.png"
    with open(tmp_dir + png_file, "wb") as f:
        f.write(img_data)

    png_file = open(tmp_dir + png_file, "rb")
    data = {"filename": deposition_doi.replace("/", "_") + ".png"}
    files = {"file": png_file}
    r = requests.post(
        f"{zenodo_url}/{deposition_id}/files",
        params={"access_token": zenodo_token},
        data=data,
        files=files,
    )
    for research_object in disco["diagram"]["elements"]["nodes"]:
        research_object = research_object["data"]
        file_name = harvest_file(author, research_object)
        ro_file = open(tmp_dir + file_name, "rb")
        data = {"filename": file_name}
        files = {"file": ro_file}
        logger.info(f"Uploading ${file_name} to Zenodo")
        r = requests.post(
            f"{zenodo_url}/{deposition_id}/files",
            params={"access_token": zenodo_token},
            data=data,
            files=files,
        )
    notes = ""

    # TODO Design a implement a queue for publication2zenodo

    data = {
        "metadata": {
            "title": disco["name"],
            "upload_type": "dataset",
            "publication_type": "milestone",
            "description": disco["description"]
            if disco["description"]
            else disco["title"],
            "creators": [{"name": author["name"], "orcid": author["orcid"]}],
            "keywords": ["disco", "scholarly wallet", "bundle"],
            "notes": notes,
            "access_right": "open",
            "communities": [{"identifier": "b4ossw"}],
        }
    }
    r = requests.put(
        f"{zenodo_url}/{deposition_id}",
        params={"access_token": zenodo_token},
        data=json.dumps(data),
        headers=headers,
    )
    r = requests.post(
        f"{zenodo_url}/{deposition_id}/actions/publish",
        params={"access_token": zenodo_token},
    )
    mongo.update_disco(
        author["orcid"],
        disco["_id"],
        {"doi": deposition_doi, "zenodo_id": deposition_id, "status": "published"},
    )
    return dumps({"doi": deposition_doi, "zenodo_id": deposition_id})


def harvest_file(user, research_object):
    tmp_dir = config.get("DEFAULT", "TMP_DIR")
    file_name = research_object["source"] + "_" + research_object["name"]
    logger.info(f"Harvesting files for research object: ${file_name}")
    if research_object["source"] == "github":
        downloads_url = research_object["ro"]["archive_url"]
        downloads_url = downloads_url.replace("{archive_format}", "zipball")
        downloads_url = downloads_url.replace("{/ref}", "/master")
        logger.info(f"Downloading Github zip files for research object: ${file_name}")
        ro_content = github.download_zip_file(
            downloads_url, user["github_token"]["access_token"]
        )
        file_name += ".zip"
        with open(tmp_dir + file_name, "wb") as f:
            f.write(ro_content)
    elif research_object["source"] == "figshare":
        file_name += ".zip"
        logger.info(f"Downloading Figshare files for research object: ${file_name}")
        figshare.download_files(
            research_object["ro"],
            user["figshare_token"]["access_token"],
            tmp_dir + file_name,
        )
    else:
        logger.info(f"Generating Orcid JSON file for research object: ${file_name}")
        ro_content = str(research_object["ro"]).encode("utf-8")
        file_name += ".json"
        with open(tmp_dir + file_name, "wb") as f:
            f.write(ro_content)
    return file_name
