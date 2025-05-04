import streamlit as st
import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd
import zipfile, tempfile
from skimage.graph import route_through_array
from shapely.geometry import LineString
from pathlib import Path
import folium
from streamlit_folium import st_folium

# --- Page config ---
st.set_page_config(layout="wide", page_title="Choose Your Trail In Alula")
BROWN = "#957E5B"

# --- Sidebar: landmark info ---
st.sidebar.title("AlUla Landmarks")
landmark_info = {
    "Alula Old Town":            ("images/Alula_Old_Town.png",             "A 7th‑century mudbrick settlement perched on a rocky spur overlooking the oasis. Its narrow alleys, vaulted gateways and pale‑stone houses evoke medieval caravan‑town life. Excavations reveal communal courtyards, mosques and markets, illustrating AlUla’s role as a historic trade hub."),
    "Alula Oasis":               ("images/Alula_Oasis.webp",                "Fed by artesian springs, this verdant palm grove sustained settlements for millennia. Date palms, citrus trees and terraces surround mudbrick villages, linked by falaj irrigation channels."),
    "Alula Fort":                ("images/Fort.jpg",                  "Perched above the valley, this 9th‑century stone fortress protected caravans on the incense route. Its raised walls, towers and vaulted chambers command sweeping views. Archaeologists believe it served both military and administrative functions."),
    "Old Town Market Street":    ("images/Old_Town_Market_Street.webp",     "Lined with restored shopfronts and cafés, this narrow bazaar street echoes centuries of trade. Stall‑holders once sold spices, textiles and pottery, drawing merchants from Yemen, India and the Levant."),
    "Jabal Ikmah":               ("images/Jabal_Ikmah.webp",                "A natural sandstone amphitheater bearing over 500 pre‑Islamic inscriptions. Pilgrims and traders once carved graffiti, petitions and prayers here in Dadanite, Lihyanite and early Arabic scripts."),
    "Harrat Viewpoint":          ("images/Harrat_Viewpoint.webp",           "This rocky overlook surveys the Harrat Khaybar lava field. From sunrise to sunset, visitors witness sculpted volcanic flows and fairy‑chimney cones, highlighting AlUla’s dramatic geology."),
    "Hegra":                     ("images/Hegra.webp",                      "Saudi Arabia’s first UNESCO site (2008), Hegra preserves over 130 rock‑cut Nabataean tombs carved into sandstone hills. Monumental façades with urns, columns and rosettes testify to its prosperity."),
    "Elephant Rock Jabal Alfil": ("images/Elephant_Rock_Jabal_Alfil.jpg",  "A massive sandstone arch sculpted by wind erosion into an elephant profile. Its natural tunnel frames desert vistas and hosts evening light shows."),
    "Maraya Concert Hall":       ("images/Maraya.jpg",                     "A world‑record mirror‑clad structure reflecting the valley. Its LED‑lined interior hosts concerts and festivals."),
    "Athlab Mount":              ("images/Athlab_Mount.jpg",               "A granite‑capped hill with prehistoric rock art and ancient fortifications. The summit offers 360° views of AlUla’s oasis and mesas."),
    "Alula OldTown Village":    ("images/Alula_Old_Town_Village.webp",    "Adjacent to Old Town, this compact stone‑and‑mudbrick village features clustered courtyards and wind‑towers. Restored houses now host cultural exhibits, offering insight into rural Najdi life and traditional irrigation over a millennium."),
    "AlUsood Cemetry":           ("images/AlUsood_Cemetry.jpg",            "A hillside necropolis of Nabataean to early Islamic tombs. Weathered stone markers overlook the oasis."),
    "Banyan Tree":               ("images/Banyan_Tree.webp",               "Banyan Tree AlUla is a luxury desert resort overlooking the dramatic Wadi Ashar in Saudi Arabia’s Al‑‘Ula region."),
    "Daimumah Amphitheater":     ("images/Daimumah_Amphitheater.webp",     "A natural rock cirque converted into a gathering place. Seating platforms carved into the cliff suggest public ceremonies or performances."),
    "Habitas AlUla Resort":      ("images/Habitas_AlUla_Resort.jpg",       "An eco‑boutique camp of modular canvas suites nestled among palm groves and canyons, emphasizing sustainability and local culture."),
    "Jabal Alahmar":             ("images/Jabal_Alahmar.jpg",              "Known as the “Red Mountain,” its reddish sandstone slopes contain ancient graves and caravan‑trail remnants, offering panoramic desert views."),
    "Jabal Albanat":             ("images/Jabal_Albanat.jpg",              "This eroded sandstone mountain bears ruins of watchtowers, terraces and cisterns—evidence of its role guarding caravan routes."),
    "OldTown Water Well":       ("images/Old_Town_Water_Well.jpg",        "A vaulted cistern hewn into bedrock, fed by underground channels. Villagers drew water daily by rope‑and‑bucket."),
    "Shaden Resort":             ("images/Shaden_Resort.webp",             "An eco‑luxury lodge set within a sandstone amphitheater. Its timber‑and‑stone villas overlook dunes and palms, powered by solar energy."),
    "Tomb Of Lihyan Son Of Kuza":("images/Tomb_Of_Lihyan_Son_Of_Kuza.jpg", "One of the largest 2nd‑century BCE Lihyanite tombs, its monumental façade features columns and carved niches."),
    # …add any remaining…
}
for name, (img, desc) in landmark_info.items():
    st.sidebar.header(name)
    if Path(img).exists():
        st.sidebar.image(img, use_container_width=True)
    else:
        st.sidebar.write("_Image not found_")
    st.sidebar.write(desc)

# --- Load landmarks (EPSG:4326) ---
geo_files = list(Path().glob("Sites*.geojson")) + list(Path().glob("Sites*.json"))
if not geo_files:
    st.error("No Sites.geojson/JSON found."); st.stop()
landmarks = gpd.read_file(str(geo_files[0])).to_crs(epsg=4326)

# --- Load boundary (KMZ→KML) ---
boundary = None
kmz_files = list(Path().glob("Boundries*.kmz")) + list(Path().glob("Boundaries*.kmz"))
if kmz_files:
    with zipfile.ZipFile(kmz_files[0]) as z:
        kml = next(f for f in z.namelist() if f.lower().endswith(".kml"))
        tmp = tempfile.NamedTemporaryFile(suffix=".kml", delete=False)
        tmp.write(z.read(kml)); tmp.flush()
        boundary = gpd.read_file(tmp.name).to_crs(epsg=4326)

# --- Load cost raster TIFF ---
tif_files = list(Path().glob("Suitability*.tif"))
if not tif_files:
    st.error("No Suitability*.tif found."); st.stop()
src = rasterio.open(str(tif_files[0]))
arr = src.read(1).astype(float)
if src.nodata is not None:
    arr[arr == src.nodata] = np.nan
transform = src.transform

# --- Main UI ---
st.title("Choose Your Trai; In Alula")
st.write("Select your landmarks and starting point:")

choices = st.multiselect("Choose landmarks to connect", landmarks["Landmark"].tolist())
start   = st.selectbox("Select starting landmark", [""] + choices) or None

if len(choices) >= 2 and start:
    # split into geo (4326) and proj (raster CRS) sets
    geo = landmarks[landmarks["Landmark"].isin(choices)]
    coords4326 = {r["Landmark"]:(r.geometry.y, r.geometry.x) for _,r in geo.iterrows()}
    proj = geo.to_crs(src.crs)
    inds = {r["Landmark"]: src.index(r.geometry.x, r.geometry.y) for _,r in proj.iterrows()}

    # build NN sequence
    cost_arr = np.where(np.isnan(arr), np.nanmax(arr)*10, arr)
    def cost(a,b):
        _,c = route_through_array(cost_arr, inds[a], inds[b], fully_connected=True)
        return c

    seq = [start]
    rem = [l for l in choices if l != start]
    while rem:
        nxt = min(rem, key=lambda x: cost(seq[-1], x))
        seq.append(nxt); rem.remove(nxt)

    # folium map
    m = folium.Map(location=coords4326[start], zoom_start=13,
                   tiles="CartoDB Positron", attr="CartoDB")

    # region boundary
    if boundary is not None:
        folium.GeoJson(
            boundary.boundary.__geo_interface__,
            style_function=lambda f: {"color":"black","weight":2,"dashArray":"5,5"}
        ).add_to(m)

    # markers
    for lm,(lat,lon) in coords4326.items():
        folium.CircleMarker(
            location=[lat,lon], radius=5,
            color=BROWN, fill=True, fill_color=BROWN,
            popup=lm
        ).add_to(m)

    # draw Brown path segments
    lines = []
    for a,b in zip(seq[:-1], seq[1:]):
        path,_ = route_through_array(cost_arr, inds[a], inds[b], fully_connected=True)
        pts    = [transform*(c,r) for r,c in path]
        lines.append(LineString(pts))
    pf = gpd.GeoDataFrame(geometry=lines, crs=src.crs).to_crs(epsg=4326)

    for geom in pf.geometry:
        folium.PolyLine(
            # swap x,y → lat,lon
            locations=[(y, x) for x,y in geom.coords],
            color="#957E5B", weight=4
        ).add_to(m)

    # fit map
    all_lats = [y for geom in pf.geometry for _,y in geom.coords]
    all_lons = [x for geom in pf.geometry for x,_ in geom.coords]
    m.fit_bounds([[min(all_lats),min(all_lons)],[max(all_lats),max(all_lons)]])

    # render
    st_folium(m, width=900, height=600)

    # compute metrics
    pf3857   = pf.to_crs(epsg=3857)
    dist_km  = pf3857.length.sum()/1000
    time_h   = dist_km/5
    calories = dist_km*60

    df = pd.DataFrame({
        "Metric": ["Distance (km)", "Time (h)", "Number of Sites", "Calories Burned (kcal)"],
        "Value":  [f"{dist_km:.2f}", f"{time_h:.2f}", len(choices), f"{calories:.0f}"]
    })
    st.subheader("Route Metrics")
    st.table(df)

else:
    st.info("Please pick at least two landmarks **and** a starting landmark.")
