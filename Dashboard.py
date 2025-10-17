import streamlit as st # UI framework for dashboard
import psycopg2
import pandas as pd
#from geopy.geocoders import Nominatim #Nominatim is the part of OpenStreetMap (OSM), free open mapping API.
from geopy.distance import geodesic # distance between two coordination
import folium # biolding interactive map
from streamlit_folium import st_folium # embeds the map into Streamlit
from dotenv import load_dotenv
import os
import requests


load_dotenv()  #.env
db_password = os.getenv("DB_PASSWORD")
db_user = os.getenv("DB_USER", "postgres") 
db_name = os.getenv("DB_NAME", "postgres")
DB_HOST = os.getenv("DB_HOST")

# connecting to the database
def get_connection():
    return psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=DB_HOST,
        port="5432"
    )


# obtening data on gas stations and prices from the database
def get_gas_stations():
    conn = get_connection()
    query = """
        SELECT g.id_station, g.municipio, g.direccion, g.station_name,
               p.fuel_type, p.price, p.fecha_informe,
               ST_Y(g.location_point::geometry) AS lat,
               ST_X(g.location_point::geometry) AS lon
        FROM gasolineras.gas_stations g
        JOIN gasolineras.prices p ON g.id_station = p.id_gas_station
        WHERE p.fecha_informe = CURRENT_DATE;
    """
    df = pd.read_sql(query, conn) # dataframe with the columns: id_station, municipio, direccion, station_name, fuel_type, price, fecha_informe, lat, lon.
                                  # if price does not yet contain data for today - will be returned empty
    conn.close()
    return df

"""
# find the nearest gas station 
def find_nearest(address, fuel_type, df):
    geolocator = Nominatim(user_agent="gasolineras_app", timeout=10) 
    time.sleep(1)  # добавить задержку
    location = geolocator.geocode(address)
    location = geolocator.geocode(address) #Sends a request to the Nominatim to find coordinates for a text address. If the address is found, a Location object is returned, containing the address, latitude, and longitude.
    if not location:
        st.error("Dirección no encontrada")
        return None, None, None

    user_coords = (location.latitude, location.longitude)
    df["fuel_type_norm"] = df["fuel_type"].astype(str).str.strip().str.lower() # filter the DataFrame by the selected fuel type (case insensitive)
    fuel_type_norm = fuel_type.strip().lower()
    df = df[df["fuel_type_norm"] == fuel_type_norm].copy()

    if df.empty:
        st.warning("No hay datos para este tipo de combustible")
        return user_coords, None, None

    # calculate the distance from the address to each gas station from the database and writes the result to a new column distancia_m (in meters).
    df["distancia_m"] = df.apply(lambda row: geodesic(user_coords, (row["lat"], row["lon"])).meters, axis=1)

    # 10 mas cercanas
    nearest = df.sort_values("distancia_m").head(10)
    # mas barata en la misma ciudad
    if "municipio" in nearest.columns and not nearest.empty:
        ciudad = nearest.iloc[0]["municipio"]
        cheapest = df[df["municipio"] == ciudad].sort_values("price").head(1)
    else:
        cheapest = pd.DataFrame()

    return user_coords, nearest, cheapest
"""


def geocode_google(address, api_key):
    """Devuelve latitud y longitud a partir de una dirección usando Google Geocoding API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "es"}
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    if data["status"] == "OK":
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    else:
        return None, None


def find_nearest(address, fuel_type, df):
    api_key = os.getenv("API_KEY")  # usamos el API Key desde .env o secrets.toml
    lat, lon = geocode_google(address, api_key)

    if not lat or not lon:
        st.error("No se pudo geolocalizar la dirección.")
        return None, None, None

    user_coords = (lat, lon)

    df["fuel_type_norm"] = df["fuel_type"].astype(str).str.strip().str.lower()
    fuel_type_norm = fuel_type.strip().lower()
    df = df[df["fuel_type_norm"] == fuel_type_norm].copy()

    if df.empty:
        st.warning("No hay datos para este tipo de combustible")
        return user_coords, None, None

    df["distancia_m"] = df.apply(lambda row: geodesic(user_coords, (row["lat"], row["lon"])).meters, axis=1)

    nearest = df.sort_values("distancia_m").head(10)
    if "municipio" in nearest.columns and not nearest.empty:
        ciudad = nearest.iloc[0]["municipio"]
        cheapest = df[df["municipio"] == ciudad].sort_values("price").head(1)
    else:
        cheapest = pd.DataFrame()

    return user_coords, nearest, cheapest

# Custom dashboard theme
st.markdown("""
    <style>
        /* Global background */
        html, body, [class*="stAppViewContainer"], [class*="stAppViewBlockContainer"] {
            background-color: #27363F !important; /* Pine */
            color: #DCE0E8 !important; /* Snowflake */
        }

        /* Buttons */
        .stButton>button {
            background-color: #6B212C; /* Berry */
            color: #FFFFFF;
            border-radius: 0px;
            padding: 10px 22px;
            font-weight: 600;
            border: none;
        }
        .stButton>button:hover {
            background-color: #8EA1AE; /* Mist */
            color: #27363F;
        }

        /* Labels */
        label, .stSelectbox label, .stTextInput label {
            color: #DCE0EB !important; 
            font-weight: 500 !important;
            font-size: 16px !important;
        }

        /* Input boxes and select */
        div[data-baseweb="input"]input{
            background-color: #DCE0EB !important;
            color: #27363F !important;
            border: 1px solid #6B5652 !important;
            border-radius: 0px !important;
            box-shadow: none !important;
        }

        /* selectbox */
        div[data-baseweb="select"] > div {
            background-color: #DCE0EB !important;
            color: #27363F !important;
            border: 1px solid #6B5652 !important;
            border-radius: 0px !important;
            box-shadow: none !important;
        }

        /* DataFrame tables */
        .stDataFrame {
            background-color: #DCE0E8; /* Snowflake */
            color: #27363F;
            border-radius: 0px;
        }

        /* Checkbox label text */
        div[data-testid="stCheckbox"] p {
            color: #DCE0EB !important;  
            font-weight: 500 !important;
            font-size: 16px !important;
            margin-left: 6px !important;
        }

        /* Headings */
        h1, h2, h3 {
            color: #DCE0E8;
        }

        /* Warnings and alerts */
        .stAlert {
            background-color: #685652;
            color: #DCE0E8;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# Interface en Streamlit
st.title("Buscador de gasolineras")

# Uploading data
df = get_gas_stations()
direccion = st.text_input("Introduce tu dirección:", "")

# selectbox of fuel types from unique values ​​in df
fuel_type = st.selectbox(
    "Selecciona un tipo de combustible",
    df["fuel_type"].unique()
)
# filter
df_filtered = df[df["fuel_type"].str.strip().str.lower() == fuel_type.strip().lower()]


# search button
if st.button("Buscar"):
    if direccion and fuel_type:
        combustible = fuel_type
        user_coords, nearest, cheapest = find_nearest(direccion, combustible, df)
        st.session_state["user_coords"] = user_coords
        st.session_state["nearest"] = nearest
        st.session_state["cheapest"] = cheapest
    else:
        st.warning("Introduce dirección y selecciona al menos un tipo de combustible.")

# display the results
if "nearest" in st.session_state and st.session_state["nearest"] is not None:
    ver_mapa = st.checkbox("Mostrar en mapa", value=False)

    if not ver_mapa:
        st.subheader("10 estaciones más cercanas")
        st.dataframe(st.session_state["nearest"][["station_name", "direccion", "price", "distancia_m"]])

        st.subheader("Combustible más barato en la ciudad")
        st.dataframe(st.session_state["cheapest"][["station_name", "direccion", "price"]])
    else:
        st.subheader("Mapa interactivo")
        user_lat, user_lon = st.session_state["user_coords"]
        # obtenemos coordenadas de la gasolinera más barata
        if not st.session_state["cheapest"].empty:
            cheapest_row = st.session_state["cheapest"].iloc[0]
            cheapest_lat = cheapest_row["lat"]
            cheapest_lon = cheapest_row["lon"]
        else:
            cheapest_lat, cheapest_lon = None, None
        m = folium.Map(location=[user_lat, user_lon], zoom_start=12)

        # Marcador del usuario
        folium.Marker(
            location=[user_lat, user_lon],
            popup="Tu ubicación",
            icon=folium.Icon(color="darkred", icon="car", prefix="fa", icon_color="lightgray")
        ).add_to(m)

        # Marcadores de gasolineras
        for _, row in st.session_state["nearest"].iterrows():
            ruta_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{row['lat']},{row['lon']}"
            popup_html = f"""
            <b>{row['station_name']}</b><br>
            {row['direccion']}<br>
            {row['price']} €<br>
            <a href="{ruta_url}" target="_blank">🚘 Ver ruta</a>
            """
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=popup_html,
                icon=folium.Icon(color="cadetblue", icon="tint", prefix="fa", icon_color="lightgray")
            ).add_to(m)
            
        # Marcador de cheapest
        if cheapest_lat and cheapest_lon:
            folium.Marker(
                location=[cheapest_lat, cheapest_lon],
                popup_html = f"""
                <b>{row['cheapest_name']}</b><br>
                {row['cheapest_adress']}<br>
                {row['cheapest_price']} €<br>
                <a href="{ruta_url}" target="_blank">🚘 Ver ruta</a>
                """,
                icon=folium.Icon(color="darkpurple", icon="star", prefix="fa", icon_color="beige")
                ).add_to(m)

        st_folium(m, width=700, height=500)