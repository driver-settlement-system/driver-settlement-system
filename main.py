from fastapi import FastAPI, Form
import os
from supabase import create_client, Client

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None


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

    if supabase:
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

    return {
        "vat": vat,
        "do_wyplaty": do_wyplaty
    }


@app.get("/driver/{driver_id}")
def get_driver_settlements(driver_id: str):
    if not supabase:
        return {"error": "Database not connected"}

    response = (
        supabase
        .table("settlements")
        .select("*")
        .eq("driver_id", driver_id)
        .order("week_start", desc=True)
        .execute()
    )

    return response.data


@app.get("/drivers")
def get_all_drivers():
    if not supabase:
        return {"error": "Database not connected"}

    response = (
        supabase
        .table("settlements")
        .select("driver_id")
        .execute()
    )

    drivers = list({row["driver_id"] for row in response.data})

    return drivers


@app.get("/weeks")
def get_all_weeks():
    if not supabase:
        return {"error": "Database not connected"}

    response = (
        supabase
        .table("settlements")
        .select("week_start, week_end")
        .execute()
    )

    weeks = list({
        (row["week_start"], row["week_end"])
        for row in response.data
    })

    return [
        {"week_start": w[0], "week_end": w[1]}
        for w in weeks
    ]
