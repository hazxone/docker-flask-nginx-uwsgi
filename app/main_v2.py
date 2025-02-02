from flask import Flask, jsonify, request, redirect, make_response, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
basic_auth = HTTPBasicAuth()
auth = HTTPTokenAuth('Bearer') 
from werkzeug import secure_filename
import face_recognition as fr
from L6SOsgE6HT import users, tokens
import uuid
import cv2
import os
from web_utils import *
# from flasgger import Swagger, swag_from
from companies_view import companies_api

swagger_template = {
    'securityDefinitions': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
}

# HTTP basic auth
# Two separate auth, one for username and password for generating token
# Second for token for API endpoint

app = Flask(__name__, static_url_path='/static')
# swagger = Swagger(app, template=swagger_template)
app.register_blueprint(companies_api)

# Security Authentication ---------------------------
# Basic Username / Password
# Token generator : use username / password
# Save/Persist token as .token in pickle folder
@basic_auth.get_password
def get_password(username):
    if username in users:
        return users.get(username)
    return None

@app.route('/')
def main_route():
    return 'The app working properly'

# Token dictionary is reverse {token:usename}, so its complicated to replace the value
# The loop is to find the key given the value(username)
# Then delete the key, reassign a new one
@app.route('/user/token', methods=['GET'])
@basic_auth.login_required
def generate_token():
    username = basic_auth.username()
    if username in users:
        for key, value in tokens.items():
            if value == username:
                new_token = gen_uuid()
                del tokens[key]
                tokens[new_token] = username
                save_pickle('session', 'token', tokens)
                result = {"Status" : "Changed", "New_Token" : new_token}
                return make_response(jsonify(result), 200)
    result = {"Status" : "Error", "Message" : "Wrong Credential"}
    return make_response(jsonify(result), 401)

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'Error':'Unauthorized Access'}), 401)

# Token Authentication for API endpoints
# All other endpoint except generate token use token auth

@auth.verify_token
def verify_token(token):
    g.user = None
    try:
        data = tokens
    except:
        return False
    if token in data:
        g.user = data[token]
        return True
    return False

@app.route('/predict', methods=['POST'])
@auth.login_required
def predict():
    username = g.user
    image = request.files['image']
    clinic_id = request.form['clinic']

    if allowed_file(secure_filename(image.filename)) is False:
        result = {"Status" : "Error", "Message" : "File type not allowed"}
        return make_response(jsonify(result), 422)

    # Process request
    img = load_image_dlib(image)
    face_bbox, im, shape, im_large = find_face_dlib(img)

    # Legacy : face_recognition
    # face_bbox, im = find_face(image)

    if len(face_bbox) != 1:
        result = {"Status" : "Error", "Message" : "No Face / More than one face detected"}
        return make_response(jsonify(result), 404)

    # Legacy : face_recognition
    # image = crop_face(im, face_bbox)
    # image = cv2.resize(image, (250, 250))

    # Save image
    save_path = os.path.join('raw')
    check_folder(save_path)
    save_image(im_large, os.path.join(save_path,'{}.jpg'.format(gen_uuid())))

    # Forward Pass Embedding
    emb = compute_emb(im, shape)

    # Legacy : face_recognition
    # emb = fr.face_encodings(im)[0]

    model, class_list = load_svm(username)

    best_class_prob, best_class_indices = predict_svm(model, emb)
    if best_class_prob > 0.4:
        result = {"Status" : "Success", "Identity" : class_list[best_class_indices], "Clinic_Id" : clinic_id}
        return make_response(jsonify(result), 200)
    else:
        result = {"Status" : "Failed", "Identity" : "Unknown"}
        return make_response(jsonify(result), 404)


# Endpoint to train the svm
# Separate from adding new identity to due cpu intensive process
# Only trigger once all the identity are added

@app.route('/train', methods=['GET'])
@auth.login_required
def training():
    import time
    new_class_list = []
    class_list = get_list_ic()
    for cla in class_list:
        x = os.path.split(cla)
        new_class_list.append(x[-1])
    print("new class list", new_class_list)
    start_time = time.time()
    train_svm(sorted(new_class_list))
    result = {"Status" : "Success", "Message" : "Successfully Update Face Database", "Training Time": time.time() - start_time}
    return make_response(jsonify(result), 200)

@app.route('/initialize', methods=['GET'])
@basic_auth.login_required
def create():
    username = basic_auth.username()
    if username == "alphaadmin":
        create_encodings()
        result = {"Status" : "Success", "Message" : "Embeddings Initialized"}
        return make_response(jsonify(result), 200)
    else:
        result = {"Status" : "Failed", "Message" : "Unauthorized users"}
        return make_response(jsonify(result), 401)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
