# Regis DC Map

Public map hosting for Regis Energy Partners data center tracking.

## Live map

- **Latest:** https://raw.githack.com/nathanvajdos/regis-dc-map/main/index.html
- **Production (cached):** https://rawcdn.githack.com/nathanvajdos/regis-dc-map/main/index.html
- **GitHub Pages (if enabled):** https://nathanvajdos.github.io/regis-dc-map/

## Data source

Map is generated from the **DC Locations Sheet** in the Regis Smartsheet workspace `0 - Data Center Workspace` → `08 - Data Center Locations/Developers`.

Auto-regenerated every Monday at 7am CT by the Weekly DC Competitive Intel Update agent.

## Files

- `index.html` — self-contained Mapbox GL JS map. Open in any browser.
- `dc_locations.geojson` — underlying GeoJSON data (can be dropped into QGIS, Mapbox Studio, Google My Maps, kepler.gl, etc.)
- `build_map.py` — generator script. Reads DC data, geocodes via Mapbox API, emits `index.html` + `dc_locations.geojson`.

## Map features

- All tracked Texas data centers as color-coded pins by Status (Operating / Under Construction / In Development / Proposed)
- Click pin → popup with Developer, MW, Market, Regis owner, notes
- Filter dropdowns: by Market (DFW / AUS / SA / HOU / WEST / WACO / OTHER) and Status
- Fullscreen, zoom, pan, imperial scale bar
- Mapbox Light basemap
