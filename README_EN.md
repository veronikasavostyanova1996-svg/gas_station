# Gas Stations ETL & Streamlit Dashboard (A Coruña)

### Overview
This project automates the collection, cleaning, and visualization of fuel price data in the province of **A Coruña, Spain**.  
Every day, a Python script downloads fresh data from the official Ministerio de Industria API, enriches it with **Google Places API** data, stores it in **Supabase (PostgreSQL + PostGIS)**, and visualizes the results in an **interactive Streamlit dashboard**.

---

## ETL Architecture

```mermaid
flowchart LR
    A["Task Scheduler (daily at 07:00)"] --> B["Python import_data_v2.py"]

    subgraph Extract
        B --> C1["Ministerio de Industria API (httpx + TLS configuration)"]
        B --> C2["Google Places API (by coordinates)"]
    end

    subgraph Transform
        D1["Filter by province Coruña"]
        D2["Coordinate parsing and cleaning"]
        D3["Normalize prices 'Precio Gasolina 95 E5' -> (fuel_type, price)"]
        D4["Google enrichment: name, rating, address"]
        C1 --> D1 --> D2 --> D3
        C2 --> D4
        D2 --> D4
    end

    subgraph Load ["Supabase Postgres + PostGIS"]
        E1["gasolineras.gas_stations"]
        E2["gasolineras.prices"]
    end

    D3 --> E2
    D4 --> E1
    D2 --> E1

    subgraph Serve ["BI Layer"]
        F["Streamlit Cloud Dashboard.py"]
        G["GitHub Repository"]
        G --> F
        F -->|psycopg2| E1
        F -->|JOIN + CURRENT_DATE| E2
    end

```

---

## Data Model (ER Diagram)

```mermaid
erDiagram
  gas_stations {
    bigint id_station PK
    text   cp
    text   municipio
    text   direccion
    text   station_name
    text   direccion_google
    numeric rating
    geography location_point
  }

  prices {
    serial id PK
    text   fuel_type
    bigint id_gas_station FK
    numeric price
    date    fecha_informe
  }

  gas_stations ||--o{ prices : "id_station = id_gas_station"
```

---

## Tech Stack

| Category | Technology |
|-----------|-------------|
| **Language** | Python 3.11+ |
| **Database** | Supabase (PostgreSQL + PostGIS) |
| **Interface** | Streamlit Cloud |
| **HTTP Clients** | httpx, requests |
| **Libraries** | psycopg2, dotenv, pandas, folium, geopy |
| **Scheduler** | Windows Task Scheduler (local) |
| **Code Hosting** | GitHub |

---

## How It Works

1. **`import_data_v2.py`**  
   - Fetches JSON from [Ministerio de Industria API](https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/)  
   - Filters only the province *A Coruña*  
   - Enriches stations with *Google Places API*  
   - Saves updated data into Supabase (tables `gasolineras.gas_stations` and `gasolineras.prices`)

2. **`Dashboard.py`**  
   - Runs on **Streamlit Cloud**  
   - Connects to Supabase via `psycopg2`  
   - Displays an interactive dashboard with:
     - Fuel type filter  
     - Address search  
     - Top-10 nearest stations  
     - Map visualization using Folium

---

## Automation
- The `import_data_v2.py` script runs **daily at 07:00** via Windows Task Scheduler.  
- The results are stored in the cloud database (Supabase).  
- The Streamlit dashboard automatically reflects the most recent data.

---

## Demo
- **Dashboard (Streamlit Cloud):** [[Dashboard Link](https://thfu5xjpz3f2danqkbxaxa.streamlit.app/)]  
- **Source Code:** [[GitHub Repository Link](https://github.com/veronikasavostyanova1996-svg/gas_station)]


---

## Author
**Savostianova Veronika**  
Data Analyst 
LinkedIn: [LinkedIn Profile](https://www.linkedin.com/in/veronika-savostianova/)  
GitHub: [github.com/veronikasavostyanova1996-svg](https://github.com/veronikasavostyanova1996-svg)
