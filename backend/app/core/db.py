import json
import logging
from threading import Lock
from datetime import datetime, timezone
from typing import Any

from backend.app.core.config import get_settings
from backend.app.models.schemas import ClinicianBaseline

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Persistence adapter for DiagnoAI.
    Uses Supabase (PostgreSQL) when SUPABASE_DB_URL is configured,
    and falls back to an in-memory repository for local development and unit tests.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = Lock()
        self._in_memory_patients: dict[str, ClinicianBaseline] = {}
        self._in_memory_sessions: dict[str, dict[str, Any]] = {}
        self._db_initialized = False

        # Seed with initial mock patient for immediate local showcase
        default_patient = ClinicianBaseline(
            patient_id="default-patient",
            full_name="Jane Doe",
            age=45,
            biological_sex="Female",
            known_allergies=["Penicillin"],
            chronic_conditions=["Mild Asthma", "Hypertension"],
            current_medications=["Lisinopril 10mg daily", "Albuterol inhaler PRN"],
            sensitive_notes="Family history of early coronary artery disease. Non-smoker.",
        )
        self._in_memory_patients[default_patient.patient_id] = default_patient

    def _get_pg_connection(self):
        if not self.settings.supabase_db_url:
            return None
        try:
            import psycopg2
            conn = psycopg2.connect(self.settings.supabase_db_url)
            return conn
        except Exception as e:
            logger.warning("Could not connect to Supabase PostgreSQL: %s. Using in-memory store.", e)
            return None

    def init_db(self) -> None:
        """Create tables in Supabase Postgres if connected."""
        if not self.settings.supabase_db_url:
            return

        conn = self._get_pg_connection()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clinician_patients (
                        patient_id TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        biological_sex TEXT NOT NULL,
                        known_allergies JSONB NOT NULL DEFAULT '[]'::jsonb,
                        chronic_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
                        current_medications JSONB NOT NULL DEFAULT '[]'::jsonb,
                        sensitive_notes TEXT,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS patient_intake_sessions (
                        session_id TEXT PRIMARY KEY,
                        patient_id TEXT NOT NULL REFERENCES clinician_patients(patient_id) ON DELETE CASCADE,
                        intake_stage TEXT NOT NULL DEFAULT 'gathering',
                        extracted_symptoms JSONB NOT NULL DEFAULT '{}'::jsonb,
                        red_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
                        report_markdown TEXT,
                        messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                conn.commit()
                self._db_initialized = True
                logger.info("Supabase PostgreSQL tables verified successfully.")
        except Exception as e:
            logger.error("Failed initializing Supabase tables: %s", e)
        finally:
            conn.close()

    def get_patient(self, patient_id: str) -> ClinicianBaseline | None:
        conn = self._get_pg_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM clinician_patients WHERE patient_id = %s;",
                        (patient_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return ClinicianBaseline(
                            patient_id=row["patient_id"],
                            full_name=row["full_name"],
                            age=row["age"],
                            biological_sex=row["biological_sex"],
                            known_allergies=row["known_allergies"] or [],
                            chronic_conditions=row["chronic_conditions"] or [],
                            current_medications=row["current_medications"] or [],
                            sensitive_notes=row["sensitive_notes"],
                            updated_at=str(row["updated_at"]),
                        )
            except Exception as e:
                logger.error("Error querying patient from Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            return self._in_memory_patients.get(patient_id)

    def save_patient(self, patient: ClinicianBaseline) -> ClinicianBaseline:
        conn = self._get_pg_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO clinician_patients (
                            patient_id, full_name, age, biological_sex,
                            known_allergies, chronic_conditions, current_medications,
                            sensitive_notes, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (patient_id) DO UPDATE SET
                            full_name = EXCLUDED.full_name,
                            age = EXCLUDED.age,
                            biological_sex = EXCLUDED.biological_sex,
                            known_allergies = EXCLUDED.known_allergies,
                            chronic_conditions = EXCLUDED.chronic_conditions,
                            current_medications = EXCLUDED.current_medications,
                            sensitive_notes = EXCLUDED.sensitive_notes,
                            updated_at = NOW();
                        """,
                        (
                            patient.patient_id,
                            patient.full_name,
                            patient.age,
                            patient.biological_sex,
                            json.dumps(patient.known_allergies),
                            json.dumps(patient.chronic_conditions),
                            json.dumps(patient.current_medications),
                            patient.sensitive_notes,
                        ),
                    )
                    conn.commit()
            except Exception as e:
                logger.error("Error saving patient to Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            self._in_memory_patients[patient.patient_id] = patient
        return patient

    def list_patients(self) -> list[ClinicianBaseline]:
        conn = self._get_pg_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM clinician_patients ORDER BY updated_at DESC;")
                    rows = cur.fetchall()
                    if rows:
                        return [
                            ClinicianBaseline(
                                patient_id=row["patient_id"],
                                full_name=row["full_name"],
                                age=row["age"],
                                biological_sex=row["biological_sex"],
                                known_allergies=row["known_allergies"] or [],
                                chronic_conditions=row["chronic_conditions"] or [],
                                current_medications=row["current_medications"] or [],
                                sensitive_notes=row["sensitive_notes"],
                                updated_at=str(row["updated_at"]),
                            )
                            for row in rows
                        ]
            except Exception as e:
                logger.error("Error listing patients from Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            return list(self._in_memory_patients.values())

    def save_session_record(
        self,
        session_id: str,
        patient_id: str,
        intake_stage: str,
        extracted_symptoms: dict[str, Any],
        red_flags: list[str],
        report_markdown: str | None,
        messages: list[dict[str, str]],
    ) -> None:
        conn = self._get_pg_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO patient_intake_sessions (
                            session_id, patient_id, intake_stage,
                            extracted_symptoms, red_flags, report_markdown,
                            messages, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (session_id) DO UPDATE SET
                            intake_stage = EXCLUDED.intake_stage,
                            extracted_symptoms = EXCLUDED.extracted_symptoms,
                            red_flags = EXCLUDED.red_flags,
                            report_markdown = EXCLUDED.report_markdown,
                            messages = EXCLUDED.messages,
                            updated_at = NOW();
                        """,
                        (
                            session_id,
                            patient_id,
                            intake_stage,
                            json.dumps(extracted_symptoms),
                            json.dumps(red_flags),
                            report_markdown,
                            json.dumps(messages),
                        ),
                    )
                    conn.commit()
            except Exception as e:
                logger.error("Error saving session record to Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            existing = self._in_memory_sessions.get(session_id, {})
            created_at = existing.get("created_at", now)
            self._in_memory_sessions[session_id] = {
                "session_id": session_id,
                "patient_id": patient_id,
                "intake_stage": intake_stage,
                "extracted_symptoms": extracted_symptoms,
                "red_flags": red_flags,
                "report_markdown": report_markdown,
                "messages": messages,
                "created_at": created_at,
                "updated_at": now,
            }

    def get_session_record(self, session_id: str) -> dict[str, Any] | None:
        conn = self._get_pg_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM patient_intake_sessions WHERE session_id = %s;",
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return dict(row)
            except Exception as e:
                logger.error("Error getting session from Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            return self._in_memory_sessions.get(session_id)

    def list_sessions_for_patient(self, patient_id: str) -> list[dict[str, Any]]:
        conn = self._get_pg_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM patient_intake_sessions WHERE patient_id = %s ORDER BY updated_at DESC;",
                        (patient_id,),
                    )
                    rows = cur.fetchall()
                    if rows:
                        return [dict(r) for r in rows]
            except Exception as e:
                logger.error("Error listing sessions from Supabase: %s", e)
            finally:
                conn.close()

        with self._lock:
            return [
                s for s in self._in_memory_sessions.values()
                if s.get("patient_id") == patient_id
            ]


db = DatabaseClient()
