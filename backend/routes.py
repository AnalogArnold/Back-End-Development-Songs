from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# RETURN HEALTH OF THE APP
######################################################################

@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200

######################################################################
# COUNT THE NUMBER OF SONGS
######################################################################    

@app.route("/count")
def count():
    """return length of data"""
    song_count = db.songs.count_documents({})
    return {"count": song_count}, 500

######################################################################
# GET ALL SONGS
######################################################################

@app.route("/song", methods=["GET"])
def songs():
    all_songs = list(db.songs.find({})) # Returns all songs documents in the database as a list
    return {"songs": parse_json(all_songs)}, 200

######################################################################
# GET A SONG
######################################################################

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """return a song given by a specific id"""
    try:
        song = db.songs.find_one({"id": id})
        if song:
            return parse_json(song), 200
        return {"message": f"song with id {id} not found"}, 404
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500

######################################################################
# CREATE A SONG
######################################################################

@app.route("/song", methods=["POST"])
def create_song():
    """create a new song"""
    try:
        new_song = request.json # Get the new song data from the request body
        new_song_id = new_song["id"]
        if db.songs.find_one({"id": new_song_id}): # Check if this ID already exists in the database
            return{"Message": f"song with id {new_song['id']} already present"}, 302
        db.songs.insert_one(new_song)
        return{"inserted id": f"{new_song_id}"}, 201
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500

######################################################################
# UPDATE A SONG
######################################################################

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """update song"""
    try:
        song_found = db.songs.find_one({"id": id}) # Check if this ID already exists in the database
        if song_found == None:
            return {"message": "song not found"}, 404
        song_data = request.json
        updated_data = {"$set": song_data}
        result = db.songs.update_one({"id": id}, updated_data) # Update data
        if result.modified_count == 0: # Nothing was modified
            return {"message": "song found, but nothing updated"}, 200
        else:
            return parse_json(db.songs.find_one({"id": id})), 201
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

######################################################################
# DELETE A SONG
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """delete song with a given id"""
    try:
        if not db.songs.find_one({"id": id}): # Check if this ID exists in the database
            return{"message": "song not found"}, 404
        db.songs.delete_one({"id": id})
        return "", 204
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500 