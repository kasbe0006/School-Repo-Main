"""
/api/students
    GET   /api/students                    (admin)
    POST  /api/students                    (admin)
    GET   /api/students/{id}               (admin, or the student themself)
    PATCH /api/students/{id}               (admin)
    GET   /api/students/{id}/transcript    (admin, or self)
    GET   /api/students/{id}/dues          (admin, or self)
    GET   /api/students/{id}/attendance    (admin, or self)

A student asking for ANOTHER student's data gets 403 (ensure_self_student).
"""

import csv
import io
import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.database import get_db, transaction
from app.errors import found_or_404
from app.pagination import list_params
from app.repositories import students as repo
from app.repositories.departments import get_department
from app.repositories.users import insert_user, set_user_active
from app.schemas.student import StudentCreate, StudentUpdate
from app.security import ensure_self_student, get_current_user, hash_password, require_role
from app.services.grading_service import calculate_cgpa

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
def list_students(
    list_args: dict = Depends(list_params),
    department_id: int | None = Query(None),
    status: str | None = Query(None),
    grade_level: int | None = Query(None, ge=1, le=12),
    section: str | None = Query(None, min_length=1, max_length=10),
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Paged list of students with CGPA, filterable by department and status."""
    return repo.list_students(conn, list_args, department_id, status, grade_level, section)


@router.post("", status_code=201)
def create_student(body: StudentCreate, user: dict = Depends(require_role("admin")),
                   conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Create account + student + profile (three tables) in ONE transaction: all or nothing."""
    data = body.model_dump(mode="json")
    found_or_404(get_department(conn, data["department_id"]), "Department", data["department_id"])
    password_hash = hash_password(data.pop("password"))     # slow: do it before taking the lock
    profile = data.pop("profile")
    with transaction(conn, user["id"]):
        user_id = insert_user(conn, data["email"], password_hash, "student")
        student_id = repo.insert_student(conn, user_id, data)
        repo.insert_profile(conn, student_id, profile)
    return repo.get_student(conn, student_id)


@router.post("/import", status_code=201)
async def import_students(
    file: UploadFile = File(...),
    initial_password: str = Form(..., min_length=12, max_length=128),
    user: dict = Depends(require_role("admin")),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create many student accounts from a CSV using one initial password."""
    if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=415, detail="Upload a CSV file")
    raw = await file.read(5 * 1024 * 1024)
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from error
    required = {
        "email", "first_name", "last_name", "student_code", "grade_level", "section",
        "department_code", "admission_date", "date_of_birth", "gender",
        "guardian_name", "guardian_phone", "guardian_relation",
    }
    missing = sorted(required - set(reader.fieldnames or []))
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing CSV columns: {', '.join(missing)}")
    rows = list(reader)
    if not rows or len(rows) > 500:
        raise HTTPException(status_code=400, detail="CSV must contain between 1 and 500 students")
    departments = {
        row["code"].upper(): row["id"]
        for row in conn.execute("SELECT id, code FROM departments WHERE is_active = 1").fetchall()
    }
    password_hash = hash_password(initial_password)
    prepared = []
    errors = []
    for number, row in enumerate(rows, start=2):
        try:
            department_id = departments.get(row["department_code"].strip().upper())
            if department_id is None:
                raise ValueError(f"unknown department_code '{row['department_code']}'")
            body = StudentCreate(
                email=row["email"], password=initial_password, department_id=department_id,
                student_code=row["student_code"], first_name=row["first_name"], last_name=row["last_name"],
                admission_date=row["admission_date"], grade_level=row.get("grade_level") or 1,
                section=row.get("section") or "A", status=row.get("status") or "active",
                profile={
                    "date_of_birth": row["date_of_birth"], "gender": row["gender"],
                    "blood_group": row.get("blood_group") or None, "address_line": row.get("address_line") or None,
                    "city": row.get("city") or None, "postal_code": row.get("postal_code") or None,
                    "guardian_name": row["guardian_name"], "guardian_phone": row["guardian_phone"],
                    "guardian_email": row.get("guardian_email") or None,
                    "guardian_relation": row["guardian_relation"],
                },
            )
            prepared.append((body, department_id))
        except Exception as error:
            errors.append(f"row {number}: {error}")
    if errors:
        raise HTTPException(status_code=422, detail={"message": "CSV validation failed", "errors": errors[:20]})
    try:
        with transaction(conn, user["id"]):
            for body, department_id in prepared:
                data = body.model_dump(mode="json")
                profile = data.pop("profile")
                data.pop("password")
                user_id = insert_user(conn, data.pop("email"), password_hash, "student")
                student_id = repo.insert_student(conn, user_id, data)
                repo.insert_profile(conn, student_id, profile)
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail=f"Import failed; duplicate or invalid value: {error}") from error
    return {"created": len(prepared), "message": "Student accounts created with the supplied initial password"}


@router.get("/{student_id}")
def get_student(student_id: int, user: dict = Depends(get_current_user),
                conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """One student with profile and CGPA."""
    ensure_self_student(user, student_id)
    return found_or_404(repo.get_student(conn, student_id), "Student", student_id)


@router.patch("/{student_id}")
def update_student(student_id: int, body: StudentUpdate, user: dict = Depends(require_role("admin")),
                   conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Change student and/or profile fields; is_active enables/disables the login."""
    student = found_or_404(repo.get_student(conn, student_id), "Student", student_id)
    changes = body.model_dump(mode="json", exclude_unset=True)
    profile_changes = changes.pop("profile", None) or {}
    is_active = changes.pop("is_active", None)
    if "department_id" in changes:
        found_or_404(get_department(conn, changes["department_id"]), "Department", changes["department_id"])
    with transaction(conn, user["id"]):
        repo.update_student(conn, student_id, changes)
        repo.update_profile(conn, student_id, profile_changes)
        if is_active is not None:
            set_user_active(conn, student["user_id"], is_active)
    return repo.get_student(conn, student_id)


@router.get("/{student_id}/transcript")
def student_transcript(student_id: int, user: dict = Depends(get_current_user),
                       conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Completed courses grouped by semester, with semester GPA and overall CGPA."""
    ensure_self_student(user, student_id)
    student = found_or_404(repo.get_student(conn, student_id), "Student", student_id)
    rows = repo.get_transcript(conn, student_id)

    semesters: dict[str, dict] = {}
    for row in rows:
        group = semesters.setdefault(row["semester_code"], {"semester_code": row["semester_code"],
                                                            "courses": [], "points": 0.0, "credits": 0.0})
        group["courses"].append(row)
        group["points"] += row["grade_point"] * row["credits"]
        group["credits"] += row["credits"]
    for group in semesters.values():
        group["gpa"] = round(group.pop("points") / group["credits"], 2) if group["credits"] else None

    return {"student": student, "semesters": list(semesters.values()), **calculate_cgpa(conn, student_id)}


@router.get("/{student_id}/dues")
def student_dues(student_id: int, user: dict = Depends(get_current_user),
                 conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """All invoices of the student and the total still owed."""
    ensure_self_student(user, student_id)
    found_or_404(repo.get_student(conn, student_id), "Student", student_id)
    return repo.get_dues(conn, student_id)


@router.get("/{student_id}/attendance")
def student_attendance(student_id: int, user: dict = Depends(get_current_user),
                       conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Attendance percentage per course."""
    ensure_self_student(user, student_id)
    found_or_404(repo.get_student(conn, student_id), "Student", student_id)
    return {"items": repo.get_attendance(conn, student_id)}
