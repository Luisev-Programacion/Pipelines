import requests
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Conexion API
#https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net
#endpoints
#https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net/rest/cinema/fetch
#envio de datos
#https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net/rest/cinema/sync
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

BASE_URL = os.getenv("BASE_URL", "https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
POSID = os.getenv("POSID", "000015")
CIRCUIT = os.getenv("CIRCUIT", "Cinemex")
CINEMA = os.getenv("CINEMA", "San Antonio")
COUNTRY = os.getenv("COUNTRY", "MX")
SYSTEM = os.getenv("SYSTEM", "VC")
TIMEOUT = int(os.getenv("TIMEOUT", "15"))  # segundos


# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if not ACCESS_TOKEN:
    raise ValueError(
        f"ACCESS_TOKEN no está definido. Configúralo en: {ENV_PATH}"
    )


# =========================
# HEADERS
# =========================
def get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


def make_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{endpoint}"

    try:
        logging.info("Enviando request a %s", url)
        logging.debug("Payload: %s", json.dumps(payload, ensure_ascii=False))
        response = requests.post(
            url,
            headers=get_headers(),
            json=payload,
            timeout=TIMEOUT
        )

        logging.info("Status Code: %s", response.status_code)
        logging.debug("Response headers: %s", dict(response.headers))
        logging.debug("Response text: %s", response.text)

        # Si status es 4xx/5xx, levanta HTTPError para inspección detallada
        response.raise_for_status()

        # Intentar parsear JSON
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Respuesta no es JSON válido. Body recibido: {response.text[:500]}"
            ) from exc

        return data

    except requests.exceptions.Timeout as exc:
        raise TimeoutError(f"Timeout: el servidor no respondió en {TIMEOUT}s") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError("Error de conexión: revisa red, DNS o URL base") from exc
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "N/A"
        response_text = exc.response.text[:1000] if exc.response is not None else ""
        if status_code == 401:
            detail = "Unauthorized (401): token inválido o expirado"
        elif status_code == 403:
            detail = "Forbidden (403): sin permisos para este recurso"
        elif status_code == 404:
            detail = "Not Found (404): endpoint incorrecto o no disponible"
        else:
            detail = f"HTTP {status_code}"
        raise RuntimeError(f"{detail}. Respuesta: {response_text}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Error inesperado de requests: {str(exc)}") from exc


def fetch_validation() -> Dict[str, Any]:
    payload = {
        "posid": POSID,
        "circuit": CIRCUIT,
        "cinema": CINEMA,
        "country": COUNTRY,
        "system": SYSTEM
    }

    logging.info("Ejecutando validación (fetch)...")
    result = make_request("/rest/cinema/fetch", payload)

    logging.info("Respuesta fetch recibida")
    return result


def sync_data(shows: list) -> Dict[str, Any]:
    payload = {
        "posid": POSID,
        "circuit": CIRCUIT,
        "cinema": CINEMA,
        "country": COUNTRY,
        "system": SYSTEM,
        "shows": shows
    }

    logging.info("Enviando datos (sync)...")
    result = make_request("/rest/cinema/sync", payload)

    logging.info("Datos enviados correctamente")
    return result

if __name__ == "__main__":
    try:
        # Cambia a DEBUG para ver payload y respuesta completa.
        logging.getLogger().setLevel(logging.INFO)

        # 1. Validar conexión
        fetch_response = fetch_validation()
        print("FETCH RESPONSE:")
        print(json.dumps(fetch_response, indent=2))

        # 2. Ejemplo de datos (ajusta según lo que te pida Comscore)
        sample_shows = [
            {
                "movie_id": "TEST123",
                "showtime": "2026-04-22T20:00:00",
                "tickets_sold": 100,
                "revenue": 12000
            }
        ]

        # 3. Enviar datos
        sync_response = sync_data(sample_shows)
        print("\nSYNC RESPONSE:")
        print(json.dumps(sync_response, indent=2))

    except Exception as e:
        logging.exception("Fallo en pipelineComscore: %s", str(e))

