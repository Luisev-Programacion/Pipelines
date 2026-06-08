import requests
import json
#https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net/rest/cinema/sync
#https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net/rest/cinema/fetch
url = "https://realtimesync-test-cnfveggsfwesb3f3.z01.azurefd.net/rest/cinema/fetch"

headers = {
    "Authorization": "Bearer SwLxrEFKP45KGhqXlgDh2IA6oun2IZjn",
    "Content-Type": "application/json"
}

payload = {
    "posid": "000015",
    "circuit": "Cinemex",
    "cinema": "San Antonio",
    "country": "MX",
    "system": "VC"
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=15)

    print("STATUS:", response.status_code)
    print("HEADERS:", response.headers)
    print("RAW RESPONSE:")
    print(response.text)

    # Intentar parsear JSON
    try:
        data = response.json()
        print("\nJSON:")
        print(json.dumps(data, indent=2))
    except:
        print("\n⚠️ No es JSON válido")

    # Manejo básico de errores
    if response.status_code == 401:
        print("❌ Token inválido")
    elif response.status_code == 403:
        print("❌ Sin permisos")
    elif response.status_code == 404:
        print("❌ Endpoint no encontrado")
    elif response.status_code >= 500:
        print("❌ Error del servidor")

except requests.exceptions.Timeout:
    print("⏱️ Timeout")
except requests.exceptions.ConnectionError:
    print("🌐 Error de conexión")
except Exception as e:
    print("⚠️ Error:", str(e))