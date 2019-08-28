import pickle
import os

users = {
        "medkad" : "mk101",
        "haibe" : "hb201",
        "maybank" : "may404",
        "alphaadmin" : "alpha303"
}

tokens = {
    "kjkjniuijoiuu879" : "medkad"
}

cred_pickle = os.path.join('pickle','users.cred')

if os.path.isfile(cred_pickle):
    with open(cred_pickle, "rb") as u:
        users = pickle.load(u)

token_pickle = os.path.join('pickle','session.token')

if os.path.isfile(token_pickle):
    with open(token_pickle, "rb") as t:
        tokens = pickle.load(t)
