"""FastAPI backend for Linktree Clone."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="Linktree Clone",
    description="Create a Linktree clone. It should have a main page that displays a list of links. There should be an admin page where a user can add, edit, and delete links. The links should be stored in a database.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Models ============

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ In-Memory Storage ============

items_db: List[dict] = []
item_counter = 0

# ============ Endpoints ============

@app.get("/")
def root():
    return {"message": "Welcome to Linktree Clone", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/items", response_model=List[Item])
def list_items():
    return items_db

@app.post("/items", response_model=Item)
def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    new_item = {
        "id": item_counter,
        "title": item.title,
        "description": item.description,
        "created_at": datetime.utcnow()
    }
    items_db.append(new_item)
    return new_item

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {"message": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")
