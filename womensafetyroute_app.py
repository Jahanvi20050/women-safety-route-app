

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box, Point
import networkx as nx
import json
import xml.etree.ElementTree as ET
import folium
from streamlit_folium import st_folium
import streamlit as st
import webbrowser  # to open maps in separate window
import base64
from io import BytesIO


# STREAMLIT PAGE CONFIG

st.set_page_config(layout="wide")
st.title("Women Safety Route App")

file_path = r"C:\Users\dell\Documents\JN\all syllabussss\crime_dataset (1).json"
with open(file_path, 'r') as file:
    data = json.load(file)

df = pd.DataFrame(data)
df.rename(columns={'longitude': 'Longitude', 'latitude': 'Latitude'}, inplace=True)
df["Longitude"] = df["Longitude"].round(2)
df["Latitude"] = df["Latitude"].round(2)

location_df = pd.read_csv(r"C:/Users/dell/Documents/JN/all syllabussss/Delhi metro.csv")
location_df["Longitude"] = location_df["Longitude"].round(2)
location_df["Latitude"] = location_df["Latitude"].round(2)

merged_df = pd.merge(df, location_df, on=["Latitude", "Longitude"], how="left")
merged_df = merged_df[merged_df['Station Names'].notna()]

#to Convert KML to CSV (police stations) ---
kml_file = r"C:/Users/dell/Documents/JN/all syllabussss/delhi_police_station_locs.kml"
csv_file = "delhi_police_station_locs.csv"

tree = ET.parse(kml_file)
root = tree.getroot()
namespace = {"kml": "http://www.opengis.net/kml/2.2"}

stations, latitudes, longitudes = [], [], []
for placemark in root.findall(".//kml:Placemark", namespace):
    name_tag = placemark.find("kml:name", namespace)
    coord_tag = placemark.find(".//kml:coordinates", namespace)
    if name_tag is not None and coord_tag is not None:
        coords = coord_tag.text.strip().split(",")  # lon, lat, alt
        stations.append(name_tag.text.strip())
        longitudes.append(float(coords[0]))
        latitudes.append(float(coords[1]))

df_kml = pd.DataFrame({
    "Police Station": stations,
    "Latitude": latitudes,
    "Longitude": longitudes
})
df_kml.to_csv(csv_file, index=False)

# USER INPUT (STREAMLIT)

st.subheader("Enter Start & End Coordinates")
col1, col2 = st.columns(2)

with col1:
    start_lat = st.number_input("Start Latitude", value=28.6139, format="%.6f")
    start_lon = st.number_input("Start Longitude", value=77.2090, format="%.6f")

with col2:
    end_lat = st.number_input("End Latitude", value=28.7041, format="%.6f")
    end_lon = st.number_input("End Longitude", value=77.1025, format="%.6f")

if st.button("Generate Maps"):
    
    # safety grid  and the route
   
    gdf_boundary = gpd.read_file(r"C:\Users\dell\Documents\JN\all syllabussss\Delhi_Boundary.geojson")
    # Work in a projected CRS (meters) for grid and routing
    gdf_boundary = gdf_boundary.to_crs(epsg=32643)

    minx, miny, maxx, maxy = gdf_boundary.total_bounds
    grid_size = 500  # meters
    grid_cells = [box(x, y, x + grid_size, y + grid_size)
                  for x in np.arange(minx, maxx, grid_size)
                  for y in np.arange(miny, maxy, grid_size)]
    grid_gdf = gpd.GeoDataFrame({'geometry': grid_cells}, crs=gdf_boundary.crs)
    grid_gdf = gpd.overlay(grid_gdf, gdf_boundary, how='intersection')

    gdf_crime = gpd.GeoDataFrame(
        merged_df,
        geometry=gpd.points_from_xy(merged_df["Longitude"], merged_df["Latitude"]),
        crs="EPSG:4326"
    ).to_crs(grid_gdf.crs)

    joined = gpd.sjoin(gdf_crime, grid_gdf, how="left", predicate="within")
    crime_counts = joined.groupby('index_right').size()
    max_crime = crime_counts.max() if len(crime_counts) > 0 else 1
    grid_gdf["safety_score"] = 1 - (crime_counts / max_crime).reindex(grid_gdf.index).fillna(0)

    start_point = gpd.GeoSeries([Point(start_lon, start_lat)], crs="EPSG:4326").to_crs(grid_gdf.crs)[0]
    end_point = gpd.GeoSeries([Point(end_lon, end_lat)], crs="EPSG:4326").to_crs(grid_gdf.crs)[0]

    G = nx.Graph()
    for idx, row in grid_gdf.iterrows():
        G.add_node(idx, geometry=row.geometry, safety_score=row.safety_score)

    sindex = grid_gdf.sindex
    for idx, cell in grid_gdf.iterrows():
        possible_neighbors = list(sindex.intersection(cell.geometry.bounds))
        for n_idx in possible_neighbors:
            if idx != n_idx and cell.geometry.touches(grid_gdf.at[n_idx, "geometry"]):
                weight = 1 - ((cell.safety_score + grid_gdf.at[n_idx, "safety_score"]) / 2)
                G.add_edge(idx, n_idx, weight=weight)

    def nearest_node(point):
        distances = grid_gdf.geometry.distance(point)
        return distances.idxmin()

    start_node = nearest_node(start_point)
    end_node = nearest_node(end_point)

    if not nx.has_path(G, start_node, end_node):
        path = None
    else:
        path = nx.shortest_path(G, source=start_node, target=end_node, weight="weight")

    police_df = pd.read_csv(csv_file)

    # STREAMLIT: BAR PLOT
    st.subheader("Crime Type Distribution (Bar Chart)")
    fig_bar, ax_bar = plt.subplots(figsize=(10, 4))
    merged_df['crime_type'].value_counts().plot(kind='bar', ax=ax_bar, title="Crime Type Distribution in Delhi")
    ax_bar.set_xlabel('Crime Type')
    ax_bar.set_ylabel('Count')
    plt.xticks(rotation=60)
    st.pyplot(fig_bar)

    # STREAMLIT: SCATTER PLOT
    st.subheader("Crime Locations (Scatter Plot)")
    fig_scatter, ax_scatter = plt.subplots(figsize=(10, 4))
    ax_scatter.scatter(merged_df['Latitude'], merged_df['Longitude'], alpha=0.5)
    ax_scatter.set_xlabel('Latitude')
    ax_scatter.set_ylabel('Longitude')
    ax_scatter.set_title('Crime Locations')
    st.pyplot(fig_scatter)

    #  STREAMLIT: SAFETY GRID + ROUTE (Folium)
 
    st.subheader("Safety Score Map (Grid) with Safest Route")
    m_grid = folium.Map(location=[28.6139, 77.2090], zoom_start=11)
    folium.GeoJson(
        gdf_boundary.to_crs(epsg=4326),
        style_function=lambda x: {"color": "black", "weight": 2, "fillOpacity": 0}
    ).add_to(m_grid)

    # Safety grid polygons (colored by safety_score)
    for _, row in grid_gdf.iterrows():
        rgba = plt.cm.RdYlGn(row.safety_score)  # RGBA tuple
        color_hex = '#%02x%02x%02x' % tuple(int(255 * c) for c in rgba[:3])
        folium.GeoJson(
            row.geometry.__geo_interface__,
            style_function=lambda feature, col=color_hex: {
                'fillColor': col,
                'color': 'black',
                'weight': 0.2,
                'fillOpacity': 0.5
            }
        ).add_to(m_grid)

    # Route path (centroids in WGS84)
    if path is not None:
        grid_gdf_4326 = grid_gdf.to_crs(epsg=4326)
        route_coords = [list(grid_gdf_4326.loc[node].geometry.centroid.coords)[0] for node in path]
        folium.PolyLine(route_coords, color="blue", weight=3, opacity=0.8, tooltip="Safest Route").add_to(m_grid)

    folium.Marker([start_lat, start_lon], popup="Start", icon=folium.Icon(color='green')).add_to(m_grid)
    folium.Marker([end_lat, end_lon], popup="End", icon=folium.Icon(color='red')).add_to(m_grid)

    st_folium(m_grid, width=850, height=520)

    # POLICE-ONLY MAP (SEPARATE WINDOW)
    m_police = folium.Map(location=[28.6139, 77.2090], zoom_start=11)
    folium.GeoJson(
        gdf_boundary.to_crs(epsg=4326),
        style_function=lambda x: {"color": "black", "weight": 2, "fillOpacity": 0}
    ).add_to(m_police)

    # Police station markers
    for _, row in police_df.iterrows():
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=row['Police Station'],
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m_police)

    police_map_file = "delhi_police_stations_only.html"
    m_police.save(police_map_file)
    try:
        webbrowser.open_new_tab(police_map_file)
    except:
        pass

    st.success(f"Police stations map opened in a new window: {police_map_file}")

    # SAFETY SCORE MAP (MATPLOTLIB POPUP VIA HTML)
   
    # Plot in projected CRS to match grid units
    st.subheader("Safety Score Map (Matplotlib Popup)")
    fig_popup, ax_popup = plt.subplots(figsize=(8, 8))
    grid_gdf.plot(column='safety_score', cmap='RdYlGn', legend=True, ax=ax_popup)

    if path is not None:
        # Route in same CRS as grid for Matplotlib
        route_x = [grid_gdf.loc[node].geometry.centroid.x for node in path]
        route_y = [grid_gdf.loc[node].geometry.centroid.y for node in path]
        ax_popup.plot(route_x, route_y, linewidth=2, label="Safest Route")

    ax_popup.set_title("Safety Score Grid with Route")
    ax_popup.legend()

    # Save figure to PNG in-memory
    buf = BytesIO()
    fig_popup.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig_popup)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Build minimal HTML file that embeds the PNG (so it "pops up" in a new tab)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Safety Score Map</title></head>
    <body style="margin:0; padding:0; background:#fff;">
      <img src="data:image/png;base64,{img_base64}" style="width:100%; height:auto; display:block;" />
    </body>
    </html>
    """

    popup_html_file = "safety_score_map_popup.html"
    with open(popup_html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        webbrowser.open_new_tab(popup_html_file)
    except:
        pass

    st.success(f"Safety Score Map opened in a new window: {popup_html_file}")
