import pandas as pd 
import requests     # Solicitudes HTTP
import os   # Rutas de archivos
from dotenv import load_dotenv  # Cargar variables de entorno

"""
🎯 **Objetivo del Script**:

Este script tiene como objetivo procesar el conjunto de datos que tenemos activo, obteniendo géneros y tags desde la API de Last.fm. 
El objetivo principal es enriquecer los datos de las canciones con información adicional que pueda ser utilizada en el 
recomendador de música basado en frases del usuario y poder filtrar con géneros y tags. 🎶

📂 El script carga un archivo CSV con los datos de canciones, consulta la API de Last.fm para obtener información, y guarda los resultados en un nuevo archivo CSV. 📊
"""

# 📌 Cargar variables de entorno
load_dotenv()
API_KEY = os.getenv('LASTFM_API_KEY')  # Clave de API desde el archivo .env
BASE_URL = 'http://ws.audioscrobbler.com/2.0/'  # URL base de la API de Last.fm

# 📂 **Definir rutas de archivos**
input_folder = './data/procesando/'
files = [f for f in os.listdir(input_folder) if f.startswith('0_for_spoty') and f.endswith('.csv')]
if not files:
    raise FileNotFoundError("No se encontró ningún archivo que comience con '0_for_spoty' en la carpeta 'procesando'.")

# Obtener el archivo más reciente basado en fecha y renombrarlo con "last"
files.sort(reverse=True)
input_file = os.path.join(input_folder, files[0])
output_file = input_file.replace("spoty", "last")  # Cambia el nombre manteniendo la estructura

# 📌 Definir la ruta del archivo de errores
error_log_file = os.path.join(input_folder, "raw", f"{os.path.basename(output_file).replace('.csv', '_error.txt')}")
os.makedirs(os.path.dirname(error_log_file), exist_ok=True)  # Asegurar que la carpeta existe

# 📌 Cargar datos existentes si ya se ha procesado parcialmente
if os.path.exists(output_file):
    processed_df = pd.read_csv(output_file)

    # 📌 Verificar si el archivo tiene recording_id
    if 'recording_id' in processed_df.columns:
        processed_ids = set(processed_df['recording_id'])  # Conjunto de IDs ya procesados
    else:
        processed_ids = set()  # Si no existe la columna, inicializamos vacío
else:
    processed_df = pd.DataFrame()   # Crear un DataFrame vacío
    processed_ids = set()   # Conjunto vacío de IDs procesados

# 📌 Cargar el dataset original
df = pd.read_csv(input_file)

# 📌 Función para registrar errores en un archivo de logs
def log_error(message):
    """
    Guarda los mensajes de error en un archivo de texto para su revisión posterior.
    """
    with open(error_log_file, 'a') as f:
        f.write(message + '\n')

# 📌 Función para obtener géneros desde Last.fm
def get_genres(artist):
    """
    Obtiene los géneros de un artista desde la API de Last.fm.
    Devuelve una cadena con los géneros separados por comas, o 'Unknown' si no hay información.
    """
    params = {
        'method': 'artist.getinfo',     
        'artist': artist,   
        'api_key': API_KEY,     
        'format': 'json'        
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()     
        data = response.json()

        # 📌 Verificar si la API devuelve géneros válidos
        if 'artist' in data and 'tags' in data['artist']:
            genres = [tag['name'] for tag in data['artist']['tags'].get('tag', []) if 'name' in tag]
            return ', '.join(genres) if genres else 'Unknown'
    except Exception as e:
        log_error(f"Error al obtener géneros para '{artist}': {e}")
    return 'Unknown'   # Si no se pueden obtener los géneros, se devuelve 'Unknown'

# 📌 Función para obtener tags desde Last.fm
def get_track_tags(artist, track):
    """
    Obtiene los tags de una canción desde la API de Last.fm.
    Devuelve una cadena con los tags separados por comas, o 'Unknown' si no hay información.
    """
    params = {
        'method': 'track.getinfo',
        'artist': artist,
        'track': track,
        'api_key': API_KEY,
        'format': 'json'
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # 📌 Verificar si la API devuelve tags válidos
        if 'track' in data and 'toptags' in data['track']:
            tags = [tag['name'] for tag in data['track']['toptags'].get('tag', []) if 'name' in tag]
            return ', '.join(tags) if tags else 'Unknown'
    except Exception as e:
        log_error(f"Error al obtener tags para '{track}' de '{artist}': {e}")
    return 'Unknown'  # Si no se pueden obtener los tags, se devuelve 'Unknown'

# 📌 Función para procesar cada fila del dataset
def process_row(index, row):         
    """
    Procesa una fila del dataset, obteniendo los géneros y tags del artista y la canción.
    Devuelve una tupla con (géneros, tags).
    """
    artist = row['artist_name']
    track = row['song_name']
    genres = get_genres(artist)
    tags = get_track_tags(artist, track)    
    return genres, tags     

# 📌 Inicio del procesamiento
print("Procesando el dataset...")
processed_count = 0  # Contador de registros procesados

# 📌 Iterar sobre cada fila del DataFrame
for index, row in df.iterrows():
    # 📌 Verificar si ya se ha procesado el recording_id
    if 'recording_id' in row and row['recording_id'] in processed_ids:
        continue  # 🔄 Saltar canciones ya procesadas

    # 📌 Obtener géneros y tags
    genres, tags = process_row(index, row)
    row['genres'] = genres
    row['tags'] = tags

    # 📌 Agregar la fila procesada al DataFrame sin duplicados
    try:
        processed_df = pd.concat([processed_df, pd.DataFrame([row])], ignore_index=True)
    except Exception as e:
        log_error(f"Error al procesar fila {index}: {e}")
        continue

    processed_ids.add(row['recording_id'])  # ⬅ Se añade a la lista de procesados

    print(f"✅ Procesado: {row['artist_name']} - {row['song_name']} | Géneros: {genres} | Tags: {tags}")

# 📌 Guardar los datos finales
processed_df.to_csv(output_file, index=False)
print(f"✅ Procesamiento completo. Archivo guardado en {output_file}")
