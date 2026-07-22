from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
import csv
import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.database import connection, init_db, row, rows
from app.face_engine import (
    decode_embedding,
    decode_image,
    embedding_from_image,
    encode_embedding,
    similarity,
)

BASE_DIR = Path(__file__).resolve().parent.parent
FACE_DIR = BASE_DIR / "data" / "faces"
FACE_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="AI Smart Attendance API",
    version="1.0.0",
    description="Python 3.14-compatible smart attendance monitoring system.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={}
    )

@app.get("/api/health")
def health():
    return {"status": "online", "service": "AI Smart Attendance"}

@app.get("/api/dashboard")
def dashboard_data():
    today = date.today().isoformat()
    total = row("SELECT COUNT(*) AS count FROM students")["count"]
    present = row(
        "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date=?",
        (today,),
    )["count"]
    recent = rows("""
        SELECT a.id, s.roll_no, s.name, s.course, a.attendance_date,
               a.check_in_time, ROUND(a.confidence * 100, 1) AS confidence,
               a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.id DESC
        LIMIT 20
    """)
    return {
        "total_students": total,
        "present_today": present,
        "absent_today": max(total - present, 0),
        "attendance_rate": round((present / total) * 100, 1) if total else 0,
        "recent": recent,
    }

@app.get("/api/students")
def list_students():
    return rows("""
        SELECT id, roll_no, name, course, email, face_path, created_at
        FROM students
        ORDER BY id DESC
    """)

@app.post("/api/students")
async def add_student(
    roll_no: str = Form(...),
    name: str = Form(...),
    course: str = Form(...),
    email: str = Form(""),
    photo: UploadFile = File(...),
):
    if not (photo.content_type or "").startswith("image/"):
        raise HTTPException(400, "Please upload an image file.")

    image_data = await photo.read()
    try:
        image = decode_image(image_data)
        vector = embedding_from_image(image)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    safe_roll = "".join(
        character for character in roll_no if character.isalnum() or character in "-_"
    )
    extension = Path(photo.filename or "photo.jpg").suffix.lower() or ".jpg"
    target = FACE_DIR / f"{safe_roll}{extension}"
    target.write_bytes(image_data)
    relative_path = str(target.relative_to(BASE_DIR)).replace("\\", "/")

    try:
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO students
                    (roll_no, name, course, email, face_path, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    roll_no.strip(),
                    name.strip(),
                    course.strip(),
                    email.strip(),
                    relative_path,
                    encode_embedding(vector),
                ),
            )
    except Exception as error:
        if "UNIQUE" in str(error).upper():
            raise HTTPException(
                409, "A student with this roll number is already registered."
            ) from error
        raise

    return {"message": "Student registered successfully."}

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    student = row("SELECT * FROM students WHERE id=?", (student_id,))
    if not student:
        raise HTTPException(404, "Student not found.")

    with connection() as conn:
        conn.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))

    face_path = BASE_DIR / student["face_path"]
    if face_path.exists():
        face_path.unlink()

    return {"message": "Student deleted successfully."}

@app.post("/api/recognize")
async def recognize(photo: UploadFile = File(...)):
    image_data = await photo.read()
    try:
        query_vector = embedding_from_image(decode_image(image_data))
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    students = rows(
        "SELECT id, roll_no, name, course, embedding FROM students"
    )
    if not students:
        raise HTTPException(404, "No students have been registered yet.")

    best_student = None
    best_score = -1.0
    for student in students:
        score = similarity(
            query_vector, decode_embedding(student["embedding"])
        )
        if score > best_score:
            best_student = student
            best_score = score

    threshold = 0.48
    if best_student is None or best_score < threshold:
        return {
            "matched": False,
            "confidence": round(max(best_score, 0) * 100, 1),
            "message": "Face not recognized.",
        }

    now = datetime.now()
    today = now.date().isoformat()
    existing = row(
        """
        SELECT id FROM attendance
        WHERE student_id=? AND attendance_date=?
        """,
        (best_student["id"], today),
    )

    if not existing:
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO attendance
                    (student_id, attendance_date, check_in_time, confidence)
                VALUES (?, ?, ?, ?)
                """,
                (
                    best_student["id"],
                    today,
                    now.strftime("%H:%M:%S"),
                    best_score,
                ),
            )

    return {
        "matched": True,
        "already_marked": bool(existing),
        "student": {
            "id": best_student["id"],
            "roll_no": best_student["roll_no"],
            "name": best_student["name"],
            "course": best_student["course"],
        },
        "confidence": round(best_score * 100, 1),
        "message": (
            "Attendance was already marked today."
            if existing
            else "Attendance marked successfully."
        ),
    }

@app.get("/api/attendance")
def attendance_records(attendance_date: str | None = None):
    query = """
        SELECT a.id, s.roll_no, s.name, s.course, a.attendance_date,
               a.check_in_time, ROUND(a.confidence * 100, 1) AS confidence,
               a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
    """
    parameters = ()
    if attendance_date:
        query += " WHERE a.attendance_date=?"
        parameters = (attendance_date,)
    query += " ORDER BY a.id DESC"
    return rows(query, parameters)

@app.delete("/api/attendance/{attendance_id}")
def delete_attendance(attendance_id: int):
    with connection() as conn:
        result = conn.execute(
            "DELETE FROM attendance WHERE id=?", (attendance_id,)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Attendance record not found.")
    return {"message": "Attendance record deleted."}

@app.get("/api/reports/attendance.csv")
def attendance_csv(attendance_date: str | None = None):
    records = attendance_records(attendance_date)
    output = io.StringIO()
    fields = [
        "id", "roll_no", "name", "course", "attendance_date",
        "check_in_time", "confidence", "status",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    filename = f"attendance_{attendance_date or 'all'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
