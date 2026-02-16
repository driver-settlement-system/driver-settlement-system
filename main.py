from fastapi import FastAPI, Form, UploadFile, File
import os
from supabase import create_client
import io

app = FastAPI()

# ===== Supabase lazy init =====

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase env variables missing")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Supabase init error:", e)
        return None


# ===== Core calculation =====

def calculate_settlement(
    uber_netto,
    uber_gotowka,
    bolt_netto,
    bolt_gotowka,
    freenow_netto,
    freenow_gotowka,
    uber_brutto,
    bolt_brutto,
    freenow_brutto,
    oplata_za_uslugi,
    najem_auta,
    bonus,
    zus
):
    suma_brutto = uber_brutto + bolt_brutto + freenow_brutto
    vat = suma_brutto * 0.06

    do_wyplaty = (
        uber_netto
        + uber_gotowka
        + bolt_netto
        - bolt_gotowka
        + freenow_netto
        - freenow_gotowka
        - oplata_za_uslugi
        - vat
        - najem_auta
        + bonus
        - zus
    )

    return vat, do_wyplaty


@app.get("/")
def root():
    return {"status": "Server działa"}


# ===== Manual calculation =====

@app.post("/calculate")
async def calculate(
    driver_id: str = Form(...),
    week_start: str = Form(...),
    week_end: str = Form(...),
    uber_netto: float = Form(...),
    uber_gotowka: float = Form(...),
    uber_brutto: float = Form(...),
    bolt_netto: float = Form(...),
    bolt_gotowka: float = Form(...),
    bolt_brutto: float = Form(...),
    freenow_netto: float = Form(...),
    freenow_gotowka: float = Form(...),
    freenow_brutto: float = Form(...),
    oplata_za_uslugi: float = Form(...),
    najem_auta: float = Form(0),
    bonus: float = Form(0),
    zus: float = Form(0)
):
    vat, do_wyplaty = calculate_settlement(
        uber_netto,
        uber_gotowka,
        bolt_netto,
        bolt_gotowka,
        freenow_netto,
        freenow_gotowka,
        uber_brutto,
        bolt_brutto,
        freenow_brutto,
        oplata_za_uslugi,
        najem_auta,
        bonus,
        zus
    )

    supabase = get_supabase()

    if supabase:
        try:
            supabase.table("settlements").upsert(
                {
                    "driver_id": driver_id,
                    "week_start": week_start,
                    "week_end": week_end,
                    "uber_brutto": uber_brutto,
                    "bolt_brutto": bolt_brutto,
                    "freenow_brutto": freenow_brutto,
                    "uber_netto": uber_netto,
                    "bolt_netto": bolt_netto,
                    "freenow_netto": freenow_netto,
                    "uber_gotowka": uber_gotowka,
                    "bolt_gotowka": bolt_gotowka,
                    "freenow_gotowka": freenow_gotowka,
                    "vat": vat,
                    "oplata_za_uslugi": oplata_za_uslugi,
                    "najem_auta": najem_auta,
                    "bonus": bonus,
                    "zus": zus,
                    "do_wyplaty": do_wyplaty
                },
                on_conflict="driver_id,week_start,week_end"
            ).execute()
        except Exception as e:
            print("Supabase insert error:", e)

    return {
        "vat": vat,
        "do_wyplaty": do_wyplaty
    }


# ===== Get data =====

@app.get("/driver/{driver_id}")
def get_driver_settlements(driver_id: str):
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not connected"}

    try:
        response = (
            supabase
            .table("settlements")
            .select("*")
            .eq("driver_id", driver_id)
            .order("week_start", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        return {"error": str(e)}


@app.get("/drivers")
def get_all_drivers():
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not connected"}

    response = supabase.table("settlements").select("driver_id").execute()
    drivers = list({row["driver_id"] for row in response.data})
    return drivers


@app.get("/weeks")
def get_all_weeks():
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not connected"}

    response = supabase.table("settlements").select("week_start, week_end").execute()

    weeks = list({
        (row["week_start"], row["week_end"])
        for row in response.data
    })

    return [
        {"week_start": w[0], "week_end": w[1]}
        for w in weeks
    ]


# ===== Uber CSV upload =====

@app.post("/upload/uber")
async def upload_uber_csv(
    week_start: str = Form(...),
    week_end: str = Form(...),
    file: UploadFile = File(...)
):
    import pandas as pd

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    def normalize_name(first_name, last_name):
        full = f"{first_name} {last_name}".strip().lower()
        parts = full.split()
        return " ".join(parts[:2])

    drivers = []

    for _, row in df.iterrows():
        try:
            name = normalize_name(
                row["Imię kierowcy"],
                row["Nazwisko kierowcy"]
            )

            netto = float(row["Wypłacono Ci : Twój przychód"])
            brutto = float(row["Wypłacono Ci : Twój przychód : Opłata"])
            gotowka = float(row["Wypłacono Ci : Bilans przejazdu : Wypłaty : Odebrana gotówka"])

            drivers.append({
                "driver": name,
                "uber_brutto": brutto,
                "uber_netto": netto,
                "uber_gotowka": gotowka
            })
        except Exception:
            continue

    return {
        "drivers_preview": drivers[:10]
    }
