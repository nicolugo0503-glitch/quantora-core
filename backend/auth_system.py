
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uuid, hashlib

app = FastAPI(title="QNT30410 Auth System")

USERS = {}
SESSIONS = {}

class Register(BaseModel):
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

@app.post("/auth/register")
def register(data: Register):
    if data.email in USERS:
        raise HTTPException(400, "user exists")
    USERS[data.email] = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "password": hash_pw(data.password)
    }
    return {"status":"ok","user":data.email}

@app.post("/auth/login")
def login(data: Login):
    user = USERS.get(data.email)
    if not user or user["password"] != hash_pw(data.password):
        raise HTTPException(401, "invalid credentials")
    token = str(uuid.uuid4())
    SESSIONS[token] = user["email"]
    return {"status":"ok","token":token}

@app.get("/auth/session")
def session(token:str):
    if token not in SESSIONS:
        raise HTTPException(401,"invalid session")
    return {"status":"ok","user":SESSIONS[token]}
