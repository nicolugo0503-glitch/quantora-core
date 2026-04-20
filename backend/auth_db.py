
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid, hashlib
from db import get_conn, init_db

app = FastAPI(title="QNT30414 Auth + DB")

init_db()

class Register(BaseModel):
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

@app.post("/auth/register")
def register(d: Register):
    conn = get_conn()
    c = conn.cursor()
    try:
        uid = str(uuid.uuid4())
        c.execute("INSERT INTO users VALUES (?,?,?)", (uid, d.email, hash_pw(d.password)))
        c.execute("INSERT INTO accounts VALUES (?,?,?)", (uid, 10000.0, 0.0))
        conn.commit()
        return {"status":"ok","user_id":uid}
    except:
        raise HTTPException(400,"user exists")

@app.post("/auth/login")
def login(d: Login):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id,password FROM users WHERE email=?", (d.email,))
    row = c.fetchone()
    if not row or row[1] != hash_pw(d.password):
        raise HTTPException(401,"invalid credentials")
    return {"status":"ok","user_id":row[0]}
