"""Validation and normalisation rules for Colombian organisation records.

Each function is small and testable (see tests/test_rules.py). They never guess: when a value
cannot be fixed with certainty it is flagged, not invented.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

PLACEHOLDERS = {"", "no provisto", "no definido", "n/a", "na", "sin dato", "sin informacion", "ninguno", "0",
                "null", "none", "-", "."}

# ---------------------------------------------------------------- text


def clean_text(s: str) -> str:
    """Trim, collapse inner spaces, fix NBSP. Placeholders become an empty string."""
    s = (s or "").replace(" ", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return "" if s.lower() in PLACEHOLDERS else s


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def name_key(s: str) -> str:
    """Comparison key for names: no accents, no punctuation, no legal-form suffix, upper case."""
    s = strip_accents(s).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(S A S|SAS|S A|SA|LTDA|E S P|ESP|S EN C|SCA|E U|EU|SAS BIC|BIC|ZOMAC)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


LEGAL_SUFFIX = [
    (r"\bS\.?\s?A\.?\s?S\.?(?=\s|$)", "S.A.S."),
    (r"\bLTDA\.?(?=\s|$)", "LTDA."),
    (r"\bE\.?\s?S\.?\s?P\.?(?=\s|$)", "E.S.P."),
    (r"\bS\.?\s?A\.?(?=\s|$)", "S.A."),
    (r"\bS\.?\s?EN\s?C\.?(?=\s|$)", "S. EN C."),
]


def standard_name(s: str) -> str:
    """Upper case, single spaces, one spelling for each legal-form suffix (SAS, S.A.S -> S.A.S.)."""
    s = clean_text(s).upper().strip(" ,;")
    for pat, rep in LEGAL_SUFFIX:
        s = re.sub(pat, rep, s)
    return re.sub(r"\s+", " ", s).strip()


def names_match(a: str, b: str) -> bool:
    """Same organisation name? Ignores spaces, punctuation, accents, legal form and small typos."""
    from difflib import SequenceMatcher
    def squash(x: str) -> str:
        x = name_key(x).replace(" ", "").replace("ENLIQUIDACION", "")
        return re.sub(r"(SAS|LTDA|ESP|SA)+$", "", x)  # suffix glued to the name: ORBIMUNDOSAS
    sa, sb = squash(a), squash(b)
    if not sa or not sb:
        return False
    return sa in sb or sb in sa or SequenceMatcher(None, sa, sb).ratio() >= 0.88


REGISTRY_FORMS = [("ACCIONES SIMPLIFICADA", "SAS"), ("LIMITADA", "LTDA"), ("COMANDITA", "S EN C"),
                  ("ANONIMA", "SA"), ("ANÓNIMA", "SA")]


def legal_form_from_registry(org_type: str) -> str:
    t = (org_type or "").upper()
    for key, form in REGISTRY_FORMS:
        if key in t:
            return form
    return ""


ORG_WORDS = re.compile(
    r"\b(SAS|S\.A\.S\.|LTDA\.?|LIMITADA|S\.A\.|E\.S\.P\.|ASOC\w*|FUNDA\w*|FUN|CORPORA\w*|COORPORA\w*|CONSORCIO|"
    r"UNION|UNIÓN|UT|JUNTA|JAC|COOPERATIV\w*|EMPRESA\w*|GRUPO|INGENIER\w*|CONSTRUC\w*|SERVICIO\w*|SOLUCION\w*|"
    r"PATRIMONIO|FIDEICOMISO|IGLESIA|PARROQUIA|INSTITU\w*|COLEGIO|CLUB|LIGA|COMERCIA\w*|INVERSION\w*|DISTRIBU\w*|"
    r"TRANSPORT\w*|SOCIEDAD|AGRO\w*|HOTEL|CENTRO|RED|COMITE|COMITÉ|FEDERA\w*|CAJA|BANCO|UNIVERSIDAD|ACUEDUCTO|"
    r"HOGAR|ALBERGUE|SEMINARIO|CONJUNTO|DEFENSA|CRUZ|ASOPADRES\w*|ONG|IPS|ESE|CDA|CAMARA|CÁMARA|ORGANIZACI\w*|"
    r"INDUSTRIA\w*|ESPECTACULOS|DOTACION\w*|PUBLICIDAD|CONSULTOR\w*|PROYECTO\w*|ASESOR\w*|SALUD|ENERGIA|"
    r"LABORATORIO\w*|BIBLIOTECA|CULTURA\w*|ARTE|VIDA|COLOMBIA\w*|BOYAC\w*|INTERNATIONAL|ESAL|CIENCIA|REDES|"
    r"MUNICIPIO|ALCALD\w*|GOBERNACI\w*|SECRETAR\w*|EDUCATIV\w*|AMBIENTAL\w*|DEPORT\w*|ESCUELA|ACADEMIA|"
    r"MINERA\w*|MINAS|CARBON\w*|TECNOLOG\w*|SISTEMAS|COMUNICACION\w*|MOTOR\w*|AUTO\w*|SUMINISTRO\w*|"
    r"FERRETER\w*|DROGUER\w*|CLINICA|CLÍNICA|HOSPITAL|MEDIC\w*|ODONTO\w*|VEREDA|SECTOR|BARRIO|PROVINCIA|ONG|"
    r"REALIDAD|VIVO|VERSO|AGUA|AGUAS|AMIGOS|ESTUDIANTES|PADRES|MUJERES|JOVENES|JÓVENES|NIÑOS|CAMPESIN\w*|"
    r"PRODUCTOR\w*|VIVIENDA|DESARROLLO|PROGRESO|FUTURO|PAZ|ESPERANZA|UNIDOS|CEMENTERIO|DIOCES\w*|CONCEJO|"
    r"BOMBEROS|ASOJUNTAS|INFRAESTRUCTURA|CABILDO|S\. EN C\.)\b")
CONNECTORS = {"DE", "LA", "DEL", "EL", "LOS", "LAS", "Y", "SAN"}


def looks_like_person_name(name: str) -> bool:
    """Heuristic privacy check: 2-4 plain words and none of the words organisations use.

    Used together with "no record in the business registry" so that real companies are not removed.
    """
    n = strip_accents(standard_name(name))
    words = n.split()
    if not 2 <= len(words) <= 4 or not all(w.isalpha() for w in words):
        return False
    if any(len(w) <= 3 and w not in CONNECTORS for w in words):  # acronyms (JDC, OAC, UC) -> organisation
        return False
    return not ORG_WORDS.search(n) and not ORG_WORDS.search(standard_name(name))


def legal_form_from_name(name: str) -> str:
    n = standard_name(name)
    for suffix, form in (("S.A.S.", "SAS"), ("LTDA.", "LTDA"), ("S. EN C.", "S EN C"), ("S.A.", "SA")):
        if n.endswith(" " + suffix) or f" {suffix} " in n:
            return form
    return ""


TYPE_TO_FORM = {
    "Sociedad por acciones simplificada": "SAS", "Sociedad de Responsabilidad Limitada colombiana": "LTDA",
    "Sociedad Anónima Abierta colombiana": "SA", "Sociedad Anónima Cerrada Colombiana": "SA",
    "Sociedad en Comandita Simple colombiana": "S EN C", "Sociedad en Comandita por Acciones colombiana": "S EN C",
}

# ---------------------------------------------------------------- NIT (Colombian tax ID)

NIT_WEIGHTS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def nit_check_digit(base: str) -> int:
    """DIAN check digit (modulo 11) for a NIT without its check digit."""
    total = sum(int(d) * w for d, w in zip(reversed(base), NIT_WEIGHTS))
    r = total % 11
    return r if r in (0, 1) else 11 - r


def parse_nit(raw: str) -> dict:
    """Split a raw NIT into base + check digit and classify it.

    Organisation NITs have 9 digits and start with 8 or 9 (800.000.000 - 999.999.999).
    The raw field sometimes includes the check digit (10 digits) and punctuation.
    """
    digits = re.sub(r"\D", "", raw or "")
    out = {"nit_digits": digits, "nit": "", "dv_given": "", "nit_status": ""}
    if len(digits) == 9 and digits[0] in "89":
        out.update(nit=digits, nit_status="ok")
    elif len(digits) == 10 and digits[0] in "89":
        base, dv = digits[:9], digits[9]
        if nit_check_digit(base) == int(dv):
            out.update(nit=base, dv_given=dv, nit_status="ok (check digit removed)")
        else:
            out.update(nit=base, dv_given=dv, nit_status="check digit does not match")
    elif not digits:
        out["nit_status"] = "missing"
    elif (len(digits) <= 10 and digits[0] not in "89") or len(digits) in (7, 8) or \
            (len(digits) == 11 and digits[0] == "1"):  # personal ID, sometimes with its check digit
        out["nit_status"] = "personal ID number (not an organisation NIT)"
    else:
        out["nit_status"] = "invalid length"
    return out


# ---------------------------------------------------------------- phone numbers (Colombia)

DEPT_LANDLINE_PREFIX = "608"  # Boyacá, Casanare, Meta... use the 2021 national numbering plan prefix 608


def parse_phone(raw: str, landline_prefix: str = DEPT_LANDLINE_PREFIX) -> dict:
    """Normalise to +57 format. Mobiles: 10 digits starting with 3. Landlines: 60X + 7 digits.

    Old 7-digit landlines get the department prefix (Colombia moved to 10-digit numbers in 2021).
    """
    raw = raw or ""
    parts = [p for p in re.split(r"[-/,;]| y | o ", raw) if len(re.sub(r"\D", "", p)) >= 7]
    if len(parts) > 1:  # "7602595-7603303": two numbers in one cell -> keep the first one
        raw = parts[0]
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("57") and len(digits) in (10, 12):  # country code typed in front
        digits = digits[2:]
    if len(digits) == 10 and digits[0] == "0" and digits[2] in "12345678":
        digits = digits[2:]  # old long-distance format 0 + carrier + area code + 7 digits (e.g. 098 7447432)
    res = {"phone_e164": "", "phone_type": "", "phone_status": ""}
    if not digits:
        res["phone_status"] = "missing"
    elif len(set(digits)) == 1 or digits in ("1234567", "1234567890", "0123456789"):
        res["phone_status"] = "invalid (dummy number)"
    elif len(digits) == 10 and digits[0] == "3":
        res.update(phone_e164="+57" + digits, phone_type="mobile", phone_status="ok")
    elif len(digits) == 10 and digits.startswith("60"):
        res.update(phone_e164="+57" + digits, phone_type="landline", phone_status="ok")
    elif len(digits) == 7 and digits[0] in "2345678":
        res.update(phone_e164="+57" + landline_prefix + digits, phone_type="landline",
                   phone_status="ok (area prefix added)")
    elif len(digits) == 8 and digits[0] in "12345678" and digits[1] in "2345678":
        # old format: 1-digit area code + 7 digits -> 60 + area code + 7 digits (2021 numbering plan)
        res.update(phone_e164="+5760" + digits, phone_type="landline", phone_status="ok (converted to 60X format)")
    else:
        res["phone_status"] = "invalid length or format"
    return res


def format_phone(e164: str) -> str:
    d = e164.replace("+57", "")
    return f"+57 {d[:3]} {d[3:6]} {d[6:]}" if len(d) == 10 else e164


def mask_mobile(e164: str) -> str:
    """Privacy: a mobile number may belong to a person, so only the operator prefix and last 2 digits stay."""
    d = e164.replace("+57", "")
    return f"+57 {d[:3]} *** **{d[-2:]}"


# ---------------------------------------------------------------- email

EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(\.[a-z0-9\-]+)*\.[a-z]{2,}$")
DOMAIN_TYPOS = {"gmail.con": "gmail.com", "gmail.co": "gmail.com", "gmial.com": "gmail.com", "gmai.com": "gmail.com",
                "gmail.comm": "gmail.com", "hotmail.con": "hotmail.com", "hotmal.com": "hotmail.com",
                "hotmail.co": "hotmail.com", "hotmail.es.": "hotmail.es", "yahoo.con": "yahoo.com",
                "outlook.con": "outlook.com", "outlok.com": "outlook.com"}
FREE_DOMAINS = {"gmail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es", "yahoo.com", "yahoo.es",
                "live.com", "msn.com", "icloud.com", "yahoo.com.co", "live.com.co", "hotmail.com.co", "aol.com",
                "protonmail.com"}
ROLE_WORDS = ("info", "contact", "gerencia", "gerente", "admin", "ventas", "comercial", "licitacion", "contratacion",
              "contabilidad", "factura", "notificacion", "proyecto", "servicio", "juridic", "tesorer", "presidencia",
              "secretar", "rector", "direccion", "coordinacion", "talentohumano", "compras", "soporte", "oficina",
              "recepcion", "general", "empresa", "asociacion", "fundacion", "corporacion", "cooperativa", "junta",
              "consorcio", "union", "sas", "ltda", "propuesta", "calidad", "operacion", "logistica", "nomina")
GENERIC_NAME_WORDS = {"SAS", "LTDA", "ASOCIACION", "FUNDACION", "CORPORACION", "JUNTA", "ACCION", "COMUNAL", "VEREDA",
                      "MUNICIPIO", "COLOMBIA", "SERVICIOS", "SOCIEDAD", "EMPRESA", "GRUPO", "COOPERATIVA", "BOYACA",
                      "CONSORCIO", "UNION", "TEMPORAL", "DEPARTAMENTO", "NACIONAL", "REGIONAL", "BARRIO", "PARA",
                      "DEL", "LOS", "LAS", "CON", "SAN", "SANTA"}


def parse_email(raw: str) -> dict:
    e = (raw or "").strip().lower().replace(" ", "").rstrip(".,;")
    res = {"email": "", "email_status": "", "email_domain": "", "email_domain_type": ""}
    if not e:
        res["email_status"] = "missing"
        return res
    if e.count("@") == 1:
        local, dom = e.split("@")
        if dom in DOMAIN_TYPOS:
            dom = DOMAIN_TYPOS[dom]
            res["email_status"] = "ok (domain typo fixed)"
        e = f"{local}@{dom}"
    if not EMAIL_RE.match(e):
        res["email_status"] = "invalid format"
        return res
    dom = e.split("@")[1]
    res.update(email=e, email_domain=dom, email_domain_type="free webmail" if dom in FREE_DOMAINS else "own domain")
    res["email_status"] = res["email_status"] or "ok"
    return res


def is_organisational_email(email: str, org_name: str) -> bool:
    """True when the mailbox clearly belongs to the organisation (role word or the organisation's name)."""
    local = re.sub(r"[^a-z]", "", email.split("@")[0])
    if any(w in local for w in ROLE_WORDS):
        return True
    words = [w for w in name_key(org_name).split() if len(w) >= 4 and w not in GENERIC_NAME_WORDS]
    if any(w.lower() in local for w in words):
        return True
    squashed = re.sub(r"[^a-z]", "", name_key(org_name).lower())
    return len(local) >= 5 and local in squashed


def mask_email(email: str) -> str:
    local, dom = email.split("@")
    return f"{local[0]}{'*' * max(3, len(local) - 1)}@{dom}"


# ---------------------------------------------------------------- website

SOCIAL = ("facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "tiktok.com",
          "wa.me", "whatsapp.com")
DOMAIN_RE = re.compile(r"^([a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def parse_website(raw: str) -> dict:
    w = (raw or "").strip().lower()
    res = {"website": "", "website_status": ""}
    if not w:
        res["website_status"] = "missing"
        return res
    w = w.replace(",", ".").replace(" ", "")
    w = re.sub(r"^(https?:?)?/*", "", w).replace("\\", "/").rstrip("/")
    host = w.split("/")[0].split(":")[0]
    if "@" in w:
        res["website_status"] = "invalid (looks like an email)"
    elif not DOMAIN_RE.match(host):
        res["website_status"] = "invalid domain"
    elif any(host.endswith(s) for s in SOCIAL):
        res.update(website="https://" + w, website_status="social media page")
    elif host in FREE_DOMAINS:
        res["website_status"] = "invalid (email provider)"
    else:
        res.update(website="https://" + w, website_status="ok")
    return res


# ---------------------------------------------------------------- address (Colombian abbreviations)

ADDRESS_ABBR = [
    (r"\b(AVENIDA CALLE|AV CALLE|AV\. CALLE)\b\.?", "AC"), (r"\b(AVENIDA CARRERA|AV CARRERA|AV\. CARRERA)\b\.?", "AK"),
    (r"\b(CALLE|CLL|CALL|CL)\b\.?", "CL"), (r"\b(CARRERA|CRA|CRR|KRA|KR|CR|CARERA)\b\.?", "KR"),
    (r"\b(AVENIDA|AVDA|AV)\b\.?", "AV"), (r"\b(DIAGONAL|DIAG|DG)\b\.?", "DG"),
    (r"\b(TRANSVERSAL|TRANSV|TRASV|TRANS|TV)\b\.?", "TV"), (r"\b(KILOMETRO|KILÓMETRO|KM)\b\.?", "KM"),
    (r"\b(BARRIO|BRR|BR)\b\.?", "BRR"), (r"\b(OFICINA|OFI|OF)\b\.?", "OF"), (r"\b(APARTAMENTO|APTO|APT|AP)\b\.?", "AP"),
    (r"\b(LOCAL|LC)\b\.?", "LC"), (r"\b(VEREDA|VRD|VDA)\b\.?", "VDA"), (r"\b(MANZANA|MANZ|MZA|MZ)\b\.?", "MZ"),
]


def standard_address(raw: str) -> str:
    a = clean_text(raw).upper()
    a = re.sub(r"\b(NO|NRO|NUM|NUMERO|NÚMERO)\b\.?|N°|Nº|#", " # ", a)
    for pat, rep in ADDRESS_ABBR:
        a = re.sub(pat, rep, a)
    a = re.sub(r"\s*-\s*", "-", a)
    a = re.sub(r"(# )+", "# ", a)
    return re.sub(r"\s+", " ", a).strip(" ,.")


def address_status(a: str) -> str:
    if not a:
        return "missing"
    if re.search(r"\b(CL|KR|AV|DG|TV|AC|AK)\b", a) and re.search(r"\d", a):
        return "ok"
    if re.search(r"\b(VDA|KM|SECTOR|SEC|FINCA|FCA|PREDIO|LOTE|MZ|PR|CORREGIMIENTO|INSPECCION)\b", a):
        return "ok (rural or non-standard)"
    return "incomplete (no street type or number)"


# ---------------------------------------------------------------- dates


def parse_date(raw: str) -> date | None:
    """Accepts the formats found in the two sources: ISO timestamps, YYYYMMDD and YYYY/MM/DD hh:mm:ss.fff."""
    s = (raw or "").strip()
    if not s or s in ("0", "00000000"):
        return None
    for fmt, n in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y%m%d", 8), ("%Y/%m/%d %H:%M:%S", 19), ("%Y-%m-%d", 10),
                   ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(s[:n], fmt).date()
        except ValueError:
            continue
    return None


def date_status(d: date | None, today: date) -> str:
    if d is None:
        return "missing or unreadable"
    if d > today:
        return "in the future"
    if d.year < 1900:
        return "before 1900"
    return "ok"
