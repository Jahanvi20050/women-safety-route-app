# Women Safety Route App

An interactive Python-based application that identifies safer routes in Delhi by analyzing crime data using geospatial analysis and graph-based pathfinding.

## Problem Statement
Urban women safety is a critical concern. This project analyzes spatial crime data and assigns safety scores to city regions, enabling the computation of safer routes between two locations.

## Tech Stack
- Python
- Pandas, NumPy
- GeoPandas, Shapely
- NetworkX (graph-based routing)
- Folium (interactive maps)
- Matplotlib (visualization)
- Streamlit (web interface)

## Key Features
- Merges crime data with metro station coordinates for spatial alignment
- Converts police station KML data into CSV for analysis
- Creates a city-wide safety grid using geospatial boundaries
- Calculates safety scores based on crime density per grid cell
- Constructs a weighted graph and computes the safest route using shortest-path algorithms
- Interactive maps displaying:
  - Crime distribution
  - Safety score grid
  - Safest route between user-defined locations
  - Nearby police station locations
- Streamlit-based UI for user input and visualization

## Dataset
- Crime data in JSON format
- Delhi Metro station coordinates (CSV)
- Delhi police station locations (KML converted to CSV)
- Delhi city boundary (GeoJSON)

## Output
- Safety score heatmap
- Safest route overlay on map
- Crime distribution plots
- Police station location map

## Status
Under active development. currenly working on this 

