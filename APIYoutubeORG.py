from googleapiclient.discovery import build
from dotenv import load_dotenv
import pandas as pd
import os
import re

# ==============================
# CONFIG
# ==============================
from datetime import datetime

# today = datetime.now().strftime("%Y-%m-%d")


# conn_str = (
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=localhost;"
#     "DATABASE=YouTubeAnalytics;"
#     "UID=tu_usuario;"
#     "PWD=tu_password;"
# )
load_dotenv()
API_KEY = os.getenv("APIKey") or os.getenv("API_KEY")

youtube = build("youtube", "v3", developerKey=API_KEY)

CHANNEL_MAP = {
    "UCK7DXWnJJarFsyu3-kADUsg": "Cinemex",
    "UCVpzea-E12H-S0O2KtrCBtw": "Cinepolis",
    "UCuON8B3q1FMIOSE-0sbC_rQ": "Universal",
    "UCwTKziMccZoy631_wbxk8wg": "Paramount",
    "UC_2POp0ILf48h6T5JqsiMBw": "Sony Pictures",
    "UCSd7rXnSqDLwyBmn9OryywQ": "Warner Bros",
    "UC8huWhDjI8UJK4bqo8BJ9WQ": "Disney",
    "UCaFEAxeTC-Y_0AFthe0Xmwg": "Diamond Films"
}

START_DATE = "2025-01-01"#/*today*/
END_DATE = "2025-12-31"#/*today*/

TRAILER_REGEX = re.compile(r"\btr[aá]iler\b", re.IGNORECASE)

def get_videos_batch(channel_id):
    request = youtube.search().list(
        part="id,snippet",
        channelId=channel_id,
        publishedAfter=START_DATE + "T00:00:00Z",
        publishedBefore=END_DATE + "T23:59:59Z",
        maxResults=50,
        type="video"
    )

    response = request.execute()

    videos = []
    for item in response["items"]:
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"]
        })

    return videos

# 2. Obtener métricas + etiqueta trailer
def detect_language(snippet, content_details):
    lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")

    has_captions = content_details.get("caption") == "true"

    if lang:
        lang = lang.lower()
        if "es" in lang:
            return "Español"
        elif "en" in lang:
            # Si tiene subtítulos, lo marcamos como subtitulado
            return "Subtitulado" if has_captions else "Inglés"

    # fallback si no hay metadata clara
    return "Subtitulado" if has_captions else "Otro"

def get_video_details(video_ids, videos_info, channel_id, channel_name):
    request = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    )

    response = request.execute()

    rows = []

    for item in response["items"]:
        stats = item["statistics"]
        snippet = item["snippet"]
        content = item["contentDetails"]

        video_id = item["id"]
        title = snippet.get("title", "")
        url = f"https://www.youtube.com/watch?v={video_id}"

        # 🔍 Trailer
        is_trailer = bool(TRAILER_REGEX.search(title))

        # 🌍 Idioma
        language = detect_language(snippet, content)

        rows.append({
            "canal_id": channel_id,
            "NombreCanal": channel_name,
            "video_id": video_id,
            "Titulo": title,
            "url": url,
            "FechaDePublicacion": snippet.get("publishedAt"),
            "vistas": int(stats.get("viewCount", 0)),
            "MeGustas": int(stats.get("likeCount", 0)),
            "Comentarios": int(stats.get("commentCount", 0)),
            #"shares": int(stats.get("favoriteCount", 0)),
            "EsTrailer": is_trailer,
            "lenguaje": language  
        })

    return rows


# ==============================
# 3. Proceso por canal
# ==============================
def process_channel(channel_id, channel_name):
    videos = get_videos_batch(channel_id)

    if not videos:
        return []

    video_ids = [v["video_id"] for v in videos]

    rows = get_video_details(video_ids, videos, channel_id, channel_name)

    return rows

# import pyodbc

# def save_to_sql_server(df):
#     conn = pyodbc.connect(conn_str)
#     cursor = conn.cursor()

#     # Convertir tipos
#     df["is_trailer"] = df["is_trailer"].astype(int)

#     for _, row in df.iterrows():
#         try:
#             cursor.execute("""
#                 INSERT INTO youtube_videos (
#                     video_id, channel_id, channel_name, title, url,
#                     published_at, views, likes, comments, shares,
#                     is_trailer, language
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#                 row.video_id,
#                 row.channel_id,
#                 row.channel_name,
#                 row.title,
#                 row.url,
#                 row.published_at,
#                 row.views,
#                 row.likes,
#                 row.comments,
#                 row.shares,
#                 row.is_trailer,
#                 row.language
#             )
#         except Exception as e:
#             # Evita duplicados por PK
#             if "PRIMARY KEY" in str(e):
#                 continue
#             else:
#                 raise e

#     conn.commit()
#     conn.close()
# ==============================
# 4. Ejecutar todo
# ==============================
def main():
    all_rows = []

    for channel_id, name in CHANNEL_MAP.items():
        print(f"Procesando {name}...")

        rows = process_channel(channel_id, name)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)

    print("\nResultado final:")
    #print(df.to_string())
    print("archivo guardado")
    return df


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    df = main()
    #save_to_sql_server(df)