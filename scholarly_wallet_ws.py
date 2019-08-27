from flask import Flask, request, jsonify
from scholarly_wallet import orcid_api as orcid
from scholarly_wallet import config
from scholarly_wallet import mongo_access as mongo, github_api as github
from scholarly_wallet import figshare_api as figshare
from scholarly_wallet import zenodo_api as zenodo
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)
from scholarly_wallet import hyperledger_api as hyperledger
from threading import Thread

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = config.get("DEFAULT", "JWT_SECRET")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(config.get("DEFAULT", "JWT_EXPIRES"))
jwt = JWTManager(app)

DEFAULT_SORT = {"orcid": "title", "github": "full_name", "figshare": "title"}


@app.route("/api/auth/orcid", methods=["GET", "OPTIONS"])
def signin():
    auth_code = request.args.get("orcid_auth_code")
    user_data = orcid.authenticate(auth_code)
    if user_data is None:
        return jsonify({"msg": "Failed authetication with Orcid"}), 403
    access_token = create_access_token(identity=user_data)
    return jsonify(access_token=access_token), 200


@app.route("/api/profile", methods=["GET", "OPTIONS"])
@jwt_required
def profile():
    current_user = get_jwt_identity()
    return jsonify(current_user), 200


@app.route("/api/auth/github", methods=["GET", "OPTIONS"])
@jwt_required
def github_auth():
    auth_code = request.args.get("code")
    orcid_id = request.args.get("orcid")
    github_token = github.authenticate(auth_code, orcid_id)
    repositories = github.get_repositories(github_token, orcid_id)
    return jsonify(repositories)


@app.route("/api/auth/figshare", methods=["GET", "OPTIONS"])
@jwt_required
def figshare_auth():
    auth_code = request.args.get("code")
    orcid_id = request.args.get("orcid")
    figshare_token = figshare.authenticate(auth_code, orcid_id)
    if figshare_token is not None:
        articles = figshare.get_articles(figshare_token, orcid_id)
        return jsonify(articles)
    else:
        return jsonify({"Msg": "Not auth for figshare"}), 403


@app.route("/api/<string:source>/claim", methods=["POST", "OPTIONS"])
@jwt_required
def claim_ro(source):
    repositories = request.get_json()
    orcid_id = request.args.get("orcid")
    for repository in repositories:
        repository["claimed"] = True
        repository["owner"] = orcid_id
    mongo.save_ros(repositories, source)
    for repository in repositories:
        repository.pop("_id")
    thread = Thread(target=hyperledger.claim_ros, args=(orcid_id, source, repositories))
    thread.start()
    return jsonify(repositories)


@app.route("/api/<string:orcid_id>/<string:source>/list", methods=["GET", "OPTIONS"])
@jwt_required
def list_github(orcid_id, source):
    start = int(request.args.get("start"))
    size = int(request.args.get("size"))
    start = start * size
    return jsonify(
        {
            "count": mongo.count_claimed(orcid_id, source),
            "results": mongo.get_claimed(
                orcid_id, source, DEFAULT_SORT[source], start, size
            ),
        }
    )


@app.route("/api/<string:orcid_id>/<string:source>/all", methods=["GET", "OPTIONS"])
@jwt_required
def list_all_ros_by_source(orcid_id, source):
    return jsonify(
        {
            "count": mongo.count_claimed(orcid_id, source),
            "results": mongo.get_claimed(orcid_id, source, DEFAULT_SORT[source]),
        }
    )


@app.route("/api/<string:orcid_id>/all", methods=["GET", "OPTIONS"])
@jwt_required
def list_all_ros(orcid_id,):
    all_ros = {"github": [], "orcid": [], "figshare": []}
    for source in all_ros.keys():
        all_ros[source] = mongo.get_claimed(orcid_id, source, DEFAULT_SORT[source])
    return jsonify(all_ros)


@app.route("/api/<string:orcid_id>/discos/create", methods=["POST", "OPTIONS"])
@jwt_required
def create_disco(orcid_id):
    disco = request.get_json()
    disco_id = str(mongo.save_disco(orcid_id, disco))
    disco_name = disco["name"]
    research_objects_urls = [
        node["data"]["id"] for node in disco["diagram"]["elements"]["nodes"]
    ]
    thread = Thread(
        target=hyperledger.create_disco_transaction,
        args=(orcid_id, disco_id, disco_name, research_objects_urls),
    )
    thread.start()
    return jsonify(disco_id)


@app.route(
    "/api/<string:orcid_id>/discos/<string:disco_id>/update",
    methods=["POST", "OPTIONS"],
)
@jwt_required
def update_disco(orcid_id, disco_id):
    disco = request.get_json()
    disco_name = disco["name"]
    research_objects_urls = [
        node["data"]["id"] for node in disco["diagram"]["elements"]["nodes"]
    ]
    thread = Thread(
        target=hyperledger.update_disco,
        args=(orcid_id, disco_id, disco_name, research_objects_urls),
    )
    thread.start()
    return jsonify(str(mongo.update_disco(orcid_id, disco_id, disco)))


@app.route(
    "/api/<string:orcid_id>/discos/<string:disco_id>/publish",
    methods=["POST", "OPTIONS"],
)
@jwt_required
def publish_disco(orcid_id, disco_id):
    user = mongo.get_user(orcid_id)
    disco = mongo.get_disco(orcid_id, disco_id)
    mongo.update_disco(orcid_id, disco_id, {"status": "in progress"})
    thread = Thread(target=zenodo.publish_to_zenodo, args=(user, disco))
    thread.start()
    return "in progress"


@app.route(
    "/api/<string:orcid_id>/discos/<string:disco_id>/status", methods=["GET", "OPTIONS"]
)
@jwt_required
def get_disco_status(orcid_id, disco_id):
    disco = mongo.get_disco(orcid_id, disco_id)
    return disco["status"] if "status" in disco else "unpublished"


@app.route(
    "/api/<string:orcid_id>/discos/<string:disco_id>", methods=["GET", "OPTIONS"]
)
@jwt_required
def get_disco(orcid_id, disco_id):
    disco = mongo.get_disco(orcid_id, disco_id)
    disco["id"] = str(disco.pop("_id"))
    return jsonify(disco)


@app.route("/api/<string:orcid_id>/discos", methods=["GET", "OPTIONS"])
@jwt_required
def get_all_discos(orcid_id):
    start = int(request.args.get("start"))
    size = int(request.args.get("size"))
    start = start * size
    return jsonify(
        {
            "count": mongo.count_discos(orcid_id),
            "results": mongo.get_discos(orcid_id, start, size),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=8000, host="0.0.0.0", threaded=True)
