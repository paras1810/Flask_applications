from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId

app =Flask(__name__)
MONGO_URI = "mongodb://localhost:27017/"
client=MongoClient(MONGO_URI)
db=client["testdb"]
collection=db["users"]

@app.route('/add_user', methods=['POST'])
def add_user():
    data=request.json
    print(data)
    if not data.get('name') or not data.get('email'):
        return jsonify({'error':'Missing Fields'}), 400
    result = collection.insert_one({
        'name':data['name'],
        'email':data['email']
    })
    return jsonify({'message':'User added', 'id':str(result.inserted_id)}), 201


@app.route('/users', methods=['GET'])
def get_users():
    users=list(collection.find())
    for user in users:
        user['_id']=str(user['_id'])
    return jsonify(users)

@app.route('/user/<id>', methods=['GET'])
def get_user(id):
    user = collection.find_one({'_id': ObjectId(id)})
    if not user:
        return jsonify({'error':'User not found'}), 404
    user['_id']=str(user['_id'])
    return jsonify(user)

@app.route('/user/<id>', methods=['DELETE'])
def delete_user(id):
    result=collection.delete_one({'_id':ObjectId(id)})
    if result.deleted_count==0:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'message': 'User Deleted'})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)