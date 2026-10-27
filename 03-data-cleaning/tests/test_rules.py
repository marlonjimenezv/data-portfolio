"""Unit tests for src/rules.py. Run: python tests/test_rules.py (also run by run.py)."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import rules as r  # noqa: E402


def test_nit():
    # Check digits confirmed against the RUES business registry
    assert r.nit_check_digit("820001277") == 2
    assert r.nit_check_digit("820001772") == 7
    assert r.nit_check_digit("900827539") == 2
    assert r.nit_check_digit("901415505") == 8
    assert r.parse_nit("900.827.539-2")["nit_status"] == "ok (check digit removed)"
    assert r.parse_nit("9008275392")["nit"] == "900827539"
    assert r.parse_nit("9008275391")["nit_status"] == "check digit does not match"
    assert r.parse_nit("900827539")["nit_status"] == "ok"
    assert r.parse_nit("1010119527")["nit_status"].startswith("personal ID")
    assert r.parse_nit("")["nit_status"] == "missing"
    assert r.parse_nit("10533266789")["nit_status"].startswith("personal ID")
    assert r.parse_nit("90001")["nit_status"] == "invalid length"
    assert r.parse_nit("11111111111111111111")["nit_status"] == "invalid length"


def test_phone():
    assert r.parse_phone("3102146698")["phone_type"] == "mobile"
    assert r.parse_phone("7444664")["phone_e164"] == "+576087444664"
    assert r.parse_phone("(608) 744 4664")["phone_e164"] == "+576087444664"
    assert r.parse_phone("+57 310 214 6698")["phone_e164"] == "+573102146698"
    assert r.parse_phone("0000000")["phone_status"].startswith("invalid")
    assert r.parse_phone("12345")["phone_status"].startswith("invalid")
    assert r.mask_mobile("+573102146698") == "+57 310 *** **98"
    assert r.parse_phone("0987447432")["phone_e164"] == "+576087447432"
    assert r.parse_phone("+57 (8) 7605427")["phone_e164"] == "+576087605427"
    assert r.parse_phone("7602595-7603303")["phone_e164"] == "+576087602595"
    assert r.parse_phone("+5716738250")["phone_e164"] == "+576016738250"
    assert r.parse_phone("31125273000")["phone_status"].startswith("invalid")


def test_email():
    assert r.parse_email(" Info@Empresa.COM ")["email"] == "info@empresa.com"
    assert r.parse_email("ventas@gmail.con")["email"] == "ventas@gmail.com"
    assert r.parse_email("no-es-un-correo")["email_status"] == "invalid format"
    assert r.parse_email("a@b.co")["email_domain_type"] == "own domain"
    assert r.is_organisational_email("construboysas@gmail.com", "CONSTRUBOY SAS")
    assert r.is_organisational_email("gerencia@limeq.com.co", "LIMEQ")
    assert not r.is_organisational_email("floralbagilsanchez@gmail.com", "JUNTA DE ACCION COMUNAL BARRIOS LAS BRISAS")
    assert r.mask_email("juanperez@gmail.com") == "j********@gmail.com"


def test_website_address_names_dates():
    assert r.parse_website("www.Empresa.com.co/")["website"] == "https://www.empresa.com.co"
    assert r.parse_website("info@empresa.com")["website_status"].startswith("invalid")
    assert r.parse_website("https://facebook.com/miempresa")["website_status"] == "social media page"
    assert r.parse_website("www.paluwala,com")["website"] == "https://www.paluwala.com"
    assert r.parse_website("http//www.gisisas.com")["website"] == "https://www.gisisas.com"
    assert r.parse_website("www.fundacionprisba2023")["website_status"] == "invalid domain"
    assert r.names_match("ORBIMUNDOSAS", "CONSTRUCTORA ORBIMUNDO SAS")
    assert r.names_match("ECORCITUR S.A.S.", "ECORECITUR S.A.S")
    assert not r.names_match("INDUSTRIAS GYA S.A.S.", "CMO BENDICION S.A.S.")
    assert r.legal_form_from_registry("SOCIEDADES POR ACCIONES SIMPLIFICADAS SAS") == "SAS"
    assert r.looks_like_person_name("Juan Daniel Vergara Fonseca")
    assert not r.looks_like_person_name("BOMBEROS VOLUNTARIOS DE OICATA")
    assert not r.looks_like_person_name("JDC CHIQUINQUIRA")
    assert not r.looks_like_person_name("CONSTRUCTORA MAGEDA SAS")
    assert r.standard_address("Carrera 7 No. 18 - 56") == "KR 7 # 18-56"
    assert r.standard_address("CALLE 23 3 21 APT 503") == "CL 23 3 21 AP 503"
    assert r.address_status("KR 7 # 18-56") == "ok"
    assert r.address_status(r.standard_address("Vereda Paunita")) == "ok (rural or non-standard)"
    assert r.address_status(r.standard_address("CERINZA")).startswith("incomplete")
    assert r.standard_name("constructora mageda s.a.s") == "CONSTRUCTORA MAGEDA S.A.S."
    assert r.standard_name("Carrazos SAS") == "CARRAZOS S.A.S."
    assert r.legal_form_from_name("GALEANOTI S.A.S") == "SAS"
    assert r.parse_date("2024-03-25T22:44:28.000") == date(2024, 3, 25)
    assert r.parse_date("19971015") == date(1997, 10, 15)
    assert r.parse_date("2026/06/18 11:31:29.553000000") == date(2026, 6, 18)
    assert r.date_status(date(2030, 1, 1), date(2026, 10, 26)) == "in the future"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("  rules tests: OK")
