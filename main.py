import os
from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# PostgreSQL connection
def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg2.connect(
        database_url,
        connect_timeout=10,
        sslmode="require"
    )

# Create table when backend starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS student_submissions (
                        id SERIAL PRIMARY KEY,
                        name_or_rollnumber VARCHAR(150) NOT NULL,
                        course_category VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

        print("PostgreSQL connected. Table is ready.")

    except Exception as error:
        print("Database connection error:", error)
        raise RuntimeError("Database connection failed.") from error

    yield
    print("Backend stopped.")


app = FastAPI(
    title="My Project API",
    lifespan=lifespan
)


# Allow local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)


# Frontend data format
class StudentData(BaseModel):
    name_or_rollnumber: str = Field(
        min_length=1, max_length=150
    )
    course_category: str = Field(
        min_length=1, max_length=100
    )


# Test backend
@app.get("/")
def home():
    return {
        "message": "My Project backend is running"
    }


# Save frontend data
@app.post("/submit")
def submit_data(data: StudentData):
    name = data.name_or_rollnumber.strip()
    course = data.course_category.strip()

    if not name or not course:
        raise HTTPException(
            status_code=400,
            detail="Please fill in both fields."
        )

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO student_submissions
                        (name_or_rollnumber, course_category)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (name, course)
                )

                record_id = cursor.fetchone()[0]

        return {
            "message": "Data saved successfully!",
            "id": record_id
        }

    except psycopg2.Error as error:
        print("Database insert error:", error)

        raise HTTPException(
            status_code=500,
            detail="Database insert failed. Check backend terminal."
        ) from error


