
from fastapi import FastAPI
from db import get_conn

app = FastAPI(title="QNT30414 Accounts")

@app.get("/account/{user_id}")
def account(user_id:str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT capital,pnl FROM accounts WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        return {"status":"not_found"}
    return {"capital":row[0],"pnl":row[1]}

@app.post("/account/update")
def update(user_id:str, pnl:float):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE accounts SET pnl=pnl+?, capital=capital+? WHERE user_id=?", (pnl,pnl,user_id))
    conn.commit()
    return {"status":"ok"}
