from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pandas as pd


API_FIELDS = (
    "nom",
    "code",
    "codeRegion",
    "region",
    "population",
    "surface",
    "centre",
)

IRL_SERIES_ID = "001515333"


def _get_env_var(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


def _require_env_var(name: str) -> str:
    value = _get_env_var(name)
    if not value:
        raise RuntimeError(
            f"{name} est manquant dans l'environnement. Ajoute-le dans .env ou .env.example."
        )
    return value.rstrip("/")


def _get_api_url() -> str:
    return _require_env_var("GEO_API_COMMUNES_URL")


def _call_api(url: str, params: dict[str, str], timeout: int, retries: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(params)
    request_url = f"{url}?{query}"
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request_url, timeout=timeout) as response:
                payload = json.load(response)
            if isinstance(payload, list):
                return payload
            return [payload]
        except Exception as exc:  # pragma: no cover - depend du reseau
            last_error = exc
            if attempt < retries:
                time.sleep(attempt)

    raise RuntimeError(f"Erreur API apres {retries} tentative(s): {last_error}")


def _format_commune(raw: dict[str, Any], ville_demandee: str) -> dict[str, Any]:
    centre = raw.get("centre") or {}
    coordinates = centre.get("coordinates") or [None, None]
    region = raw.get("region") or {}
    surface_hectares = raw.get("surface")

    return {
        "ville_demandee": ville_demandee,
        "ville_api": raw.get("nom"),
        "latitude": coordinates[1],
        "longitude": coordinates[0],
        "code_insee": raw.get("code"),
        "code_region": raw.get("codeRegion"),
        "nom_region": region.get("nom"),
        "population": int(raw["population"]) if raw.get("population") is not None else None,
        "superficie_m2": float(surface_hectares) * 10000 if surface_hectares is not None else None,
    }


def recuperer_infos_communes(
    villes: list[str],
    timeout: int = 20,
    retries: int = 3,
    verbose: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    
    api_url = _get_api_url()
    fields = ",".join(API_FIELDS)
    data: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if verbose:
        print("Plan API communes")
        print("  1. Lire l'URL depuis GEO_API_COMMUNES_URL")
        print("  2. Recevoir une liste de villes en entree")
        print("  3. Appeler l'API pour chaque ville")
        print("  4. Garder uniquement les champs du mapping PDF")
        print("  5. Retourner les donnees et le log d'erreurs")

    for ville in villes:
        ville_clean = str(ville).strip()
        if not ville_clean:
            errors.append({"ville": ville, "error": "Nom de ville vide"})
            continue

        try:
            payload = _call_api(
                api_url,
                {
                    "nom": ville_clean,
                    "fields": fields,
                    "format": "json",
                },
                timeout=timeout,
                retries=retries,
            )
        except Exception as exc:
            errors.append({"ville": ville_clean, "error": str(exc)})
            continue

        if not payload:
            errors.append({"ville": ville_clean, "error": "Aucune commune retournee par l'API"})
            continue

        exact_matches = [
            commune
            for commune in payload
            if str(commune.get("nom", "")).casefold() == ville_clean.casefold()
        ]
        selected = exact_matches[0] if exact_matches else payload[0]
        data.append(_format_commune(selected, ville_clean))

        if verbose:
            print(f"  OK - {ville_clean}: {selected.get('code')}")

    if verbose:
        print("\nLog erreurs API:")
        if not errors:
            print("  Aucune erreur.")
        for error in errors:
            print(f"  - {error['ville']}: {error['error']}")

    return {"data": data, "errors": errors}


def recuperer_toutes_communes(timeout: int = 30) -> pd.DataFrame:
    
    payload = _call_api(
        f"{_get_api_url()}",
        {"fields": ",".join(API_FIELDS), "format": "json"},
        timeout=timeout,
        retries=3,
    )
    return pd.DataFrame([_format_commune(commune, commune.get("nom", "")) for commune in payload])


def recuperer_irl(timeout: int = 60) -> pd.DataFrame:
    
    request = urllib.request.Request(f"{_require_env_var('INSEE_SDMX_URL')}/{IRL_SERIES_ID}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        xml_bytes = response.read()

    root = ET.fromstring(xml_bytes)
    records = [
        {"trimestre": obs.attrib["TIME_PERIOD"], "irl": float(obs.attrib["OBS_VALUE"])}
        for obs in root.iter("Obs")
    ]
    return pd.DataFrame(records).sort_values("trimestre").reset_index(drop=True)


if __name__ == "__main__":
    exemple = recuperer_infos_communes(["Lyon", "Paris"], verbose=True)
    print(json.dumps(exemple, ensure_ascii=False, indent=2))
