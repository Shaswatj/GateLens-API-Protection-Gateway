import logging
from datetime import datetime
from fastapi import FastAPI

logging.basicConfig(
    filename="backend.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

app = FastAPI(title="Mock Backend APIs")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "backend"}

@app.get("/users")
async def get_users():
    users = [
        {"user_id": 1, "name": "John Doe", "email": "john@example.com"},
        {"user_id": 2, "name": "Jane Doe", "email": "jane@example.com"}
    ]
    logging.info(f"GET /users at {datetime.now()}")
    return users

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    logging.info(f"GET /users/{user_id} at {datetime.now()}")
    return {"user_id": user_id, "name": "John Doe", "email": "john@example.com"}

@app.get("/orders")
async def get_orders():
    logging.info(f"GET /orders at {datetime.now()}")
    return [
        {"id": 1, "item": "Laptop", "price": 999},
        {"id": 2, "item": "iPhone", "price": 1099}
    ]

@app.post("/test-waf")
async def test_waf(data: dict):
    return {"status": "received", "data": data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)