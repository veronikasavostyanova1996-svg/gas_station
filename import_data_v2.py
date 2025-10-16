import ssl # TLS/SSL encription for HTTPS requests
import httpx # moden HTTP clients, used instead of requests (better TLS control)
import requests # for standart HTTP requests
import psycopg2 # PostgreSQL adapter for Python
from datetime import date # for proper date handling inside save_to_db(prices) 
from dotenv import load_dotenv
import os

load_dotenv()  #.env

api_key = os.getenv("API_KEY")
db_password = os.getenv("DB_PASSWORD")
db_user = os.getenv("DB_USER", "postgres") 
db_name = os.getenv("DB_NAME", "postgres")
DB_HOST = os.getenv("DB_HOST")

# Connetct to PostgreSQL
try:
    print("Connecting to Supabase with settings:")
    print("  host =", DB_HOST)
    print("  user =", db_user)
    print("  dbname =", db_name)
    print("  password present =", bool(db_password))
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=DB_HOST,
        port="5432"
    )
    cur = conn.cursor() # cursor () allows sending SQL queries from Python  
except Exception as e:
    print(f"Can’t establish connection to database: {e}")
    conn = None 
    cur = None


# API from the Spanish Ministry of Indusry (fuel prices)
def get_fuel_prices():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {"User-Agent": "Mozilla/5.0"} # fake browser header (User-Agent) to avoid being blokced (that the server does not reject the request as "scripted") 
    ssl_context = ssl.create_default_context() # create a default TSL context^ lower the OpenSSL "security level" to 1. This allows “older” cipher suites
    ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1") # компромисс безопасности. Без этого соединиться нельзя, т.к. у сервера устаревшая TLS-конфигурация.

    try:
        with httpx.Client(verify=ssl_context, timeout=10) as client: # Creates a synchronous HTTP client (httpx); verify=ssl_context - uses our custom TLS settings for certificate validation
            r = client.get(url, headers=headers)
            r.raise_for_status() # raise exception for HTTP 4xx/5xx codes (HTTPStatusError)
            return r.json()["ListaEESSPrecio"]
    except Exception as e:
        print(f"Error while loading data from Ministerio API: {e}")
        return []


# Google Maps API: find nearby gas stations
def find_gas_station_google(lat, lng):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 50,
        "type": "gas_station",
        "key": api_key,
        "language": "es"
    }
    try:
        response = requests.get(url, params=params, timeout=10) # sends an HTTP GET request
        data = response.json() # parses the JSON response into a Python dictionar
        results = data.get("results", []) # gets the list of results; if the key doesn't exist, return an empty list
        if results: 
            place = results[0] # takes the first (closest / most relevant) result
            return {
                "name": place.get("name"),
                "direccion_google": place.get("vicinity"),
                "rating": place.get("rating")
            }
    except Exception as e:
        print(f"Google API error: {e}")
    return None # Return None if no results 


# Save data into PostreSQL
def save_to_db(prices):
    today = date.today()
    target_prov = {"a coruña", "la coruña", "coruña (a)"} # different spellings in Minesterio API

    for station in prices:
        prov = station["Provincia"].strip().lower()
        if prov not in target_prov:
            continue  # ignor other provinces

        try:
            id_station = int(station["IDEESS"])
        except ValueError:
            continue

        cp = station["C.P."]
        municipio = station["Municipio"]
        direccion = station["Dirección"]

        try:
            lat = float(station["Latitud"].replace(",", "."))
            lng = float(station["Longitud (WGS84)"].replace(",", "."))
        except (KeyError, ValueError, AttributeError): # skip invalid coordinates
            continue

        # check if the gas station already exists in the database
        cur.execute("""
            SELECT cp, municipio, direccion, ST_AsText(location_point)
            FROM gasolineras.gas_stations
            WHERE id_station = %s;
        """, (id_station,))
        existing = cur.fetchone()
        if not existing:
            # station not found - insert new record
            cur.execute("""
                INSERT INTO gasolineras.gas_stations
                (id_station, cp, municipio, direccion, rating, station_name, direccion_google, location_point)
                VALUES (%s, %s, %s, %s, NULL, NULL, NULL, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
            """, (id_station, cp, municipio, direccion, lng, lat))

        else:
            # station exists - check for data changes
            old_cp, old_municipio, old_direccion, old_location = existing # the old_* variables contain the current values ​​from the database
            new_location = f"POINT({lat}, {lng})" # new location into a point

            if(old_cp != cp) or (old_municipio != municipio) or (old_direccion != direccion) or (old_location != new_location):
                cur.execute("""
                    UPDATE gasolineras.gas_stations
                    SET cp = %s,
                        municipio = %s,
                        direccion = %s, 
                        location_point = ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    WHERE id_station = %s;
                """, (cp, municipio, direccion, lng, lat, id_station))

        # Google Maps data
        google_data = find_gas_station_google(lat, lng)
        if google_data:
            cur.execute("""
                UPDATE gasolineras.gas_stations
                SET station_name = %s,
                    direccion_google = %s,
                    rating = %s
                WHERE id_station = %s;
            """, (
                google_data["name"],
                google_data["direccion_google"],
                google_data["rating"],
                id_station
            ))

        # prices
        # we iterate through all fields of the JSON/dictoionary "station" (this reprsents one gas station from the Ministerio API)
        # key — the field name (por ejemplo "Precio Gasolina 95 E5"), value - the string with the price or an ampty string
        for key, value in station.items():
            if key.startswith("Precio") and value.strip() != "":
                try:
                    price = float(value.replace(",", "."))
                except ValueError:
                    continue

                fuel_type = key.replace("Precio", "").strip()

                cur.execute("""
                    INSERT INTO gasolineras.prices (fuel_type, id_gas_station, price, fecha_informe)
                    VALUES (%s, %s, %s, %s);
                """, (fuel_type, id_station, price, today))

    conn.commit()


# Run script 
if __name__ == "__main__":
    print("Script started")
    try:
        precios = get_fuel_prices()
        print(f"Loaded {len(precios)} records from Ministerio API")
        save_to_db(precios)
        print("Data successfully saved to database")
    except Exception as e:
        print("Execution error:", e)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()