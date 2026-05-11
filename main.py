"""
Minimal FastAPI teaching app for cloud evaluation.

This file is intentionally incomplete. Students must implement:
- Cloud SQL (PostgreSQL) integration
- Cloud Storage integration
- Firestore integration
"""

import os
import psycopg2

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from google.cloud import storage

load_dotenv()

app = FastAPI(title="Cloud Computing Evaluation API (Starter)")

# =========================
# DATABASE CONNECTION
# =========================

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    price NUMERIC
)
""")

conn.commit()


# =========================
# MODELS
# =========================

class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


class CommentCreate(BaseModel):
    author: str
    text: str


# =========================
# ENDPOINTS
# =========================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/products")
def create_product(payload: ProductCreate):

    cursor.execute(
        """
        INSERT INTO products (name, description, price)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (payload.name, payload.description, payload.price)
    )

    product_id = cursor.fetchone()[0]

    conn.commit()

    return {
        "message": "Producto creado correctamente",
        "product_id": product_id
    }


@app.get("/products")
def list_products():

    cursor.execute("""
        SELECT id, name, description, price
        FROM products
        ORDER BY id
    """)

    products = cursor.fetchall()

    result = []

    for product in products:
        result.append({
            "id": product[0],
            "name": product[1],
            "description": product[2],
            "price": float(product[3])
        })

    return result


@app.post("/products/{product_id}/image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...)
):

    storage_client = storage.Client()

    bucket = storage_client.bucket(
        os.getenv("BUCKET_NAME")
    )

    blob_name = f"products/{product_id}/{file.filename}"

    blob = bucket.blob(blob_name)

    blob.upload_from_file(
        file.file,
        content_type=file.content_type
    )

    image_url = (
        f"https://storage.googleapis.com/"
        f"{bucket.name}/{blob_name}"
    )

    return {
        "message": "Imagen subida correctamente",
        "product_id": product_id,
        "filename": file.filename,
        "url": image_url
    }


@app.post("/products/{product_id}/comments")
def add_product_comment(product_id: int, payload: CommentCreate):

    return {
        "message": "Comentario registrado correctamente",
        "product_id": product_id,
        "author": payload.author,
        "text": payload.text
    }


@app.get("/audit/events")
def get_audit_events():

    return [
        {
            "product_id": 1,
            "author": "Jesus",
            "text": "Excelente producto"
        }
    ]