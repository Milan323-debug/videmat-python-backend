from fastapi import APIRouter, HTTPException, Query
from app.database import history_collection
from datetime import datetime
from bson import ObjectId
import math

router = APIRouter()

def serialize(doc):
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

@router.get("/")
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    skip = (page - 1) * limit
    total = await history_collection.count_documents({})
    docs = await history_collection.find({}) \
        .sort("created_at", -1) \
        .skip(skip).limit(limit) \
        .to_list(limit)

    return {
        "success": True,
        "data": [serialize(d) for d in docs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": math.ceil(total / limit),
        }
    }

@router.delete("/")
async def clear_history():
    await history_collection.delete_many({})
    return {"success": True, "message": "History cleared"}

@router.delete("/{item_id}")
async def delete_item(item_id: str):
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(400, "Invalid item ID")
    await history_collection.delete_one({"_id": oid})
    return {"success": True, "message": "Deleted"}

@router.get("/stats")
async def get_stats():
    total = await history_collection.count_documents({})
    pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}]
    by_type = await history_collection.aggregate(pipeline).to_list(10)
    return {"success": True, "data": {"total": total, "by_type": by_type}}
