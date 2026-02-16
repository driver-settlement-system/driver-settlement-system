from fastapi import FastAPI, Form

app = FastAPI()


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

    return {
        "vat": vat,
        "do_wyplaty": do_wyplaty
    }
