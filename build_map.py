"""
Regis DC Competitive Map — automated builder.

Pulls competitor DC data live from Smartsheet API, geocodes any rows missing
Lat/Long via Mapbox, merges with the Regis project list (projects.json), and
writes index.html + dc_locations.geojson.

Designed to run in GitHub Actions on a weekly cron. Secrets required:
  SMARTSHEET_TOKEN  - Smartsheet personal access token (read sheet)
  MAPBOX_TOKEN      - Mapbox public token (pk.*) for geocoding + map tiles

Local run:
  export SMARTSHEET_TOKEN=...
  export MAPBOX_TOKEN=...
  python build_map.py
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

SHEET_ID = 943562557443972
SHEET_PERMALINK = "MfQHrM892gvWm38j44Vh3C5R2X3xxjxvC6G89vQ1"  # for deep-link URLs to specific rows

# Smartsheet column IDs (stable; from one-time discovery)
COL = {
    "DC Type": 8264483543928708,
    "DC Developer": 3760883916558212,
    "DC Name": 5605446339743620,
    "Status": 4450297705615236,
    "Primary Market": 3197933963136900,
    "Total Cap (MW)": 4403984200847236,
    "Address": 4863784541966212,
    "City": 2611984728280964,
    "County": 4344744589348740,
    "State": 3382424082009988,
    "Zip": 6899660847533956,
    "Owner": 1272839225429892,
    "Latitude": 7658186925707140,
    "Longitude": 2028687391494020,
    "Location Notes": 7886023709380484,
}

STATUS_COLORS = {
    "1_Operating": "#1a7f37",
    "2_Under Construction": "#e16f24",
    "3_ In Development": "#0969da",
    "3_In Development": "#0969da",
    "4_Proposed": "#8250df",
}

PLACEHOLDER_DEVELOPERS = {"zzz - Add New DC Here", "TEST"}


def smartsheet_get_sheet(token, sheet_id):
    url = f"https://api.smartsheet.com/2.0/sheets/{sheet_id}?pageSize=10000"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cell_value(row_cells_by_col, col_id):
    cell = row_cells_by_col.get(col_id, {})
    v = cell.get("displayValue", cell.get("value", ""))
    if v is None:
        return ""
    return str(v).strip()


def parse_dcs_from_sheet(sheet):
    rows = sheet.get("rows", [])
    out = []
    for row in rows:
        cells_by_col = {c["columnId"]: c for c in row.get("cells", [])}
        developer = cell_value(cells_by_col, COL["DC Developer"])
        if not developer or developer in PLACEHOLDER_DEVELOPERS:
            continue

        lat_str = cell_value(cells_by_col, COL["Latitude"])
        lon_str = cell_value(cells_by_col, COL["Longitude"])
        try:
            lat = float(lat_str) if lat_str else None
            lon = float(lon_str) if lon_str else None
        except ValueError:
            lat = lon = None

        zip_str = cell_value(cells_by_col, COL["Zip"])
        if zip_str.endswith(".0"):
            zip_str = zip_str[:-2]

        out.append({
            "row_id": row.get("id"),
            "developer": developer,
            "name": cell_value(cells_by_col, COL["DC Name"]),
            "status": cell_value(cells_by_col, COL["Status"]),
            "market": cell_value(cells_by_col, COL["Primary Market"]),
            "address": cell_value(cells_by_col, COL["Address"]),
            "city": cell_value(cells_by_col, COL["City"]),
            "county": cell_value(cells_by_col, COL["County"]),
            "state": cell_value(cells_by_col, COL["State"]),
            "zip": zip_str,
            "mw": cell_value(cells_by_col, COL["Total Cap (MW)"]),
            "owner": cell_value(cells_by_col, COL["Owner"]),
            "note": cell_value(cells_by_col, COL["Location Notes"]),
            "lat": lat,
            "lon": lon,
        })
    return out


def mapbox_geocode(query, mapbox_token):
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"
        f"?access_token={mapbox_token}&country=us&limit=1&types=address,poi,place,locality"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        feats = data.get("features", [])
        if not feats:
            return None
        center = feats[0]["center"]
        return (center[0], center[1])
    except Exception as e:
        print(f"  geocode error for '{query}': {e}", file=sys.stderr)
        return None


def build_query(dc):
    parts = [p for p in [dc["address"], dc["city"], dc["county"], dc["state"], dc["zip"]] if p]
    if not parts:
        return None
    return ", ".join(parts)


def main():
    smartsheet_token = os.environ.get("SMARTSHEET_TOKEN")
    mapbox_token = os.environ.get("MAPBOX_TOKEN")
    if not smartsheet_token:
        print("ERROR: SMARTSHEET_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)
    if not mapbox_token:
        print("ERROR: MAPBOX_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Fetching DC Locations Sheet (id {SHEET_ID})...")
    sheet = smartsheet_get_sheet(smartsheet_token, SHEET_ID)
    all_dcs = parse_dcs_from_sheet(sheet)
    print(f"  -> {len(all_dcs)} non-placeholder rows")

    dc_features = []
    geocoded = 0
    skipped = 0
    cached = 0
    for dc in all_dcs:
        if dc["lat"] is None or dc["lon"] is None:
            query = build_query(dc)
            if not query:
                skipped += 1
                continue
            coords = mapbox_geocode(query, mapbox_token)
            if not coords:
                skipped += 1
                continue
            dc["lon"], dc["lat"] = coords
            geocoded += 1
            time.sleep(0.05)
        else:
            cached += 1

        status_label = dc["status"].replace("1_", "").replace("2_", "").replace("3_", "").replace("4_", "").strip()
        # Build full address line for display
        addr_parts = [p for p in [dc["address"], dc["city"], dc["state"], dc["zip"]] if p]
        full_addr = ", ".join(addr_parts)
        # Deep-link to the row in Smartsheet
        ss_url = f"https://app.smartsheet.com/sheets/{SHEET_PERMALINK}?rowId={dc['row_id']}" if dc["row_id"] else ""
        dc_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [dc["lon"], dc["lat"]]},
            "properties": {
                "layer": "dc",
                "developer": dc["developer"],
                "name": dc["name"] or "",
                "status": status_label,
                "status_key": dc["status"],
                "market": dc["market"] or "",
                "mw": dc["mw"] or "",
                "owner": dc["owner"] or "",
                "note": dc["note"] or "",
                "address": full_addr,
                "city": dc["city"] or "",
                "county": dc["county"] or "",
                "state": dc["state"] or "",
                "ss_url": ss_url,
                "color": STATUS_COLORS.get(dc["status"], "#6e7781"),
            },
        })

    print(f"  -> {len(dc_features)} DCs on map ({cached} cached coords, {geocoded} freshly geocoded, {skipped} skipped no location)")

    projects_path = os.path.join(out_dir, "projects.json")
    with open(projects_path, "r", encoding="utf-8") as f:
        projects_doc = json.load(f)
    projects = projects_doc.get("projects", [])
    print(f"\nLoading {len(projects)} Regis project sites from projects.json...")

    project_features = []
    for p in projects:
        print(f"  * Project {p['name']:<10} ({'EXACT' if p.get('precise') else 'approx'}) {p.get('aka', ''):<12} -> {p['lat']:.4f}, {p['lon']:.4f}")
        project_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "layer": "project",
                "developer": "REGIS",
                "name": f"Project {p['name']}",
                "aka": p.get("aka", ""),
                "county": p.get("county", ""),
                "utility": p.get("utility", ""),
                "stage": p.get("stage", ""),
                "mw": p.get("mw", ""),
                "note": p.get("note", ""),
                "precise": p.get("precise", False),
                "color": "#cf222e",
            },
        })

    features = dc_features + project_features
    geojson = {"type": "FeatureCollection", "features": features}

    with open(os.path.join(out_dir, "dc_locations.geojson"), "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(generate_html(geojson, len(dc_features), len(project_features), mapbox_token))

    print(f"\n[OK] {len(dc_features)} DCs + {len(project_features)} Regis projects = {len(features)} pins total.")
    print(f"[OK] Wrote index.html and dc_locations.geojson")


def generate_html(geojson, n_dcs, n_projects, mapbox_token):
    geojson_str = json.dumps(geojson)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Regis DC Competitive Map</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.css" rel="stylesheet" />
<script src="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.js"></script>
<style>
  body {{ margin: 0; padding: 0; font-family: -apple-system, 'Segoe UI', Arial, sans-serif; }}
  #map {{ position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}
  .map-overlay {{ position: absolute; top: 14px; left: 14px; background: #fff; border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.15); padding: 14px 16px; font-size: 13px; z-index: 2; max-width: 300px; }}
  .map-overlay h1 {{ font-size: 15px; margin: 0 0 6px 0; color: #0d1117; }}
  .map-overlay p {{ margin: 4px 0; color: #57606a; font-size: 12px; }}
  .legend {{ margin-top: 10px; }}
  .legend h2 {{ font-size: 11px; margin: 8px 0 4px 0; color: #57606a; text-transform: uppercase; letter-spacing: 0.4px; }}
  .legend-row {{ display: flex; align-items: center; margin: 3px 0; font-size: 12px; color: #24292f; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 1px solid rgba(0,0,0,0.1); }}
  .legend-star {{ width: 12px; height: 12px; margin-right: 8px; color: #cf222e; font-size: 14px; line-height: 1; }}
  .filter-controls {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid #d0d7de; }}
  .filter-controls label {{ display: block; font-size: 11px; color: #57606a; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
  .filter-controls select {{ width: 100%; padding: 5px; font-size: 12px; border: 1px solid #d0d7de; border-radius: 4px; background: #fff; color: #24292f; }}
  .filter-controls .layer-toggles {{ display: flex; gap: 10px; margin-top: 6px; }}
  .filter-controls .layer-toggles label {{ flex: 1; display: flex; align-items: center; font-size: 12px; color: #24292f; cursor: pointer; text-transform: none; letter-spacing: 0; font-weight: 500; }}
  .filter-controls .layer-toggles input {{ margin-right: 5px; }}
  .mapboxgl-popup-content {{ font-family: -apple-system, 'Segoe UI', sans-serif; padding: 12px 14px; font-size: 12px; max-width: 300px; }}
  .mapboxgl-popup-content h3 {{ margin: 0 0 4px 0; font-size: 13px; color: #0d1117; }}
  .mapboxgl-popup-content .dev {{ font-size: 11px; color: #57606a; margin-bottom: 6px; font-weight: 500; }}
  .mapboxgl-popup-content .field {{ margin: 3px 0; color: #24292f; }}
  .mapboxgl-popup-content .field strong {{ color: #57606a; font-weight: 500; min-width: 76px; display: inline-block; }}
  .mapboxgl-popup-content .note {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #eaeef2; font-style: italic; color: #57606a; font-size: 11px; }}
  .mapboxgl-popup-content .regis-badge {{ background: #cf222e; color: #fff; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; letter-spacing: 0.4px; }}
  .footer {{ position: absolute; bottom: 8px; left: 14px; background: #fff; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #57606a; box-shadow: 0 1px 4px rgba(0,0,0,0.1); z-index: 2; }}
  .footer a {{ color: #0969da; text-decoration: none; }}
  .table-toggle {{ background: #0969da; color: #fff; border: 0; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; width: 100%; margin-top: 8px; }}
  .table-toggle:hover {{ background: #0857b8; }}
  #tablePanel {{ position: absolute; top: 0; right: 0; bottom: 0; width: 540px; max-width: 90vw; background: #fff; box-shadow: -4px 0 16px rgba(0,0,0,0.15); z-index: 3; transform: translateX(100%); transition: transform 0.25s ease-out; display: flex; flex-direction: column; overflow: hidden; }}
  #tablePanel.open {{ transform: translateX(0); }}
  .tp-header {{ padding: 12px 16px; border-bottom: 1px solid #d0d7de; display: flex; align-items: center; justify-content: space-between; background: #f6f8fa; }}
  .tp-header h2 {{ margin: 0; font-size: 14px; color: #0d1117; }}
  .tp-close {{ background: transparent; border: 0; font-size: 20px; cursor: pointer; color: #57606a; padding: 0 6px; }}
  .tp-tabs {{ display: flex; border-bottom: 1px solid #d0d7de; }}
  .tp-tab {{ flex: 1; padding: 10px 14px; border: 0; background: transparent; cursor: pointer; font-size: 12px; font-weight: 600; color: #57606a; border-bottom: 2px solid transparent; }}
  .tp-tab.active {{ color: #0969da; border-bottom-color: #0969da; background: #fff; }}
  .tp-search {{ padding: 8px 12px; border-bottom: 1px solid #eaeef2; }}
  .tp-search input {{ width: 100%; padding: 6px 10px; border: 1px solid #d0d7de; border-radius: 4px; font-size: 12px; box-sizing: border-box; }}
  .tp-body {{ flex: 1; overflow-y: auto; padding: 0; }}
  .tp-body table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  .tp-body thead {{ position: sticky; top: 0; background: #f6f8fa; box-shadow: 0 1px 0 #d0d7de; z-index: 1; }}
  .tp-body th {{ text-align: left; padding: 8px 10px; font-weight: 600; color: #57606a; border-bottom: 1px solid #d0d7de; cursor: pointer; user-select: none; white-space: nowrap; }}
  .tp-body th:hover {{ background: #eaeef2; }}
  .tp-body th.sort-asc::after {{ content: ' ▲'; font-size: 9px; color: #0969da; }}
  .tp-body th.sort-desc::after {{ content: ' ▼'; font-size: 9px; color: #0969da; }}
  .tp-body td {{ padding: 7px 10px; border-bottom: 1px solid #eaeef2; color: #24292f; vertical-align: top; }}
  .tp-body tr:hover td {{ background: #f6f8fa; }}
  .tp-body tr.regis td {{ background: #fff5f5; }}
  .tp-body tr.regis:hover td {{ background: #ffecec; }}
  .tp-body .status-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
  .tp-body .mw-bar {{ display: inline-block; height: 4px; background: #0969da; border-radius: 2px; vertical-align: middle; margin-right: 6px; min-width: 2px; }}
  .tp-body tr.regis .mw-bar {{ background: #cf222e; }}
  .tp-footer {{ padding: 6px 12px; border-top: 1px solid #d0d7de; font-size: 10px; color: #57606a; background: #f6f8fa; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="map-overlay">
  <h1>Regis DC Competitive Map</h1>
  <p>{n_dcs} competitor DCs + {n_projects} Regis project sites · Auto-updated weekly via GitHub Actions</p>
  <div class="legend">
    <h2>Competitor DCs</h2>
    <div class="legend-row"><span class="legend-dot" style="background:#1a7f37"></span>Operating</div>
    <div class="legend-row"><span class="legend-dot" style="background:#e16f24"></span>Under Construction</div>
    <div class="legend-row"><span class="legend-dot" style="background:#0969da"></span>In Development</div>
    <div class="legend-row"><span class="legend-dot" style="background:#8250df"></span>Proposed</div>
    <h2>Regis Projects</h2>
    <div class="legend-row"><span class="legend-star">*</span>Project site (red)</div>
  </div>
  <div class="filter-controls">
    <label for="marketFilter">Market (DCs)</label>
    <select id="marketFilter">
      <option value="">All markets</option>
      <option value="DFW">DFW</option>
      <option value="AUS">AUS</option>
      <option value="SA">SA</option>
      <option value="HOU">HOU</option>
      <option value="WEST">WEST</option>
      <option value="WACO">WACO</option>
      <option value="OTHER">OTHER</option>
    </select>
  </div>
  <div class="filter-controls">
    <label for="statusFilter">Status (DCs)</label>
    <select id="statusFilter">
      <option value="">All statuses</option>
      <option value="1_Operating">Operating</option>
      <option value="2_Under Construction">Under Construction</option>
      <option value="3_ In Development">In Development</option>
      <option value="4_Proposed">Proposed</option>
    </select>
  </div>
  <div class="filter-controls">
    <label>Layers</label>
    <div class="layer-toggles">
      <label><input type="checkbox" id="toggleDCs" checked>DCs</label>
      <label><input type="checkbox" id="toggleProjects" checked>Regis projects</label>
    </div>
  </div>
  <button class="table-toggle" id="openTable">Open Summary Table</button>
  <p style="font-size: 10px; color: #8b949e; margin-top: 8px;">Pin size = MW capacity (area proportional to MW).</p>
</div>

<div id="tablePanel">
  <div class="tp-header">
    <h2>Summary Tables</h2>
    <button class="tp-close" id="closeTable">x</button>
  </div>
  <div class="tp-tabs">
    <button class="tp-tab active" data-tab="regis">Regis Projects (<span id="regisCount">0</span>)</button>
    <button class="tp-tab" data-tab="dcs">Competitor DCs (<span id="dcCount">0</span>)</button>
  </div>
  <div class="tp-search">
    <input type="text" id="tableSearch" placeholder="Search by name, developer, market, county...">
  </div>
  <div class="tp-body" id="tableBody"></div>
  <div class="tp-footer" id="tableFooter">Click any row to zoom to that pin. Click a column header to sort.</div>
</div>

<div class="footer">
  Source: <a href="https://app.smartsheet.com/sheets/MfQHrM892gvWm38j44Vh3C5R2X3xxjxvC6G89vQ1" target="_blank">Smartsheet DC Locations</a>
  · <a href="https://github.com/nathanvajdos/regis-dc-map">GitHub repo</a>
</div>
<script>
mapboxgl.accessToken = '{mapbox_token}';
const GEOJSON = {geojson_str};

const map = new mapboxgl.Map({{
  container: 'map',
  style: 'mapbox://styles/mapbox/light-v11',
  center: [-99.5, 31.5],
  zoom: 5.2,
  minZoom: 3,
  maxZoom: 17,
}});
map.addControl(new mapboxgl.NavigationControl(), 'top-right');
map.addControl(new mapboxgl.FullscreenControl(), 'top-right');
map.addControl(new mapboxgl.ScaleControl({{ maxWidth: 120, unit: 'imperial' }}), 'bottom-right');

map.on('load', () => {{
  map.addSource('points', {{ type: 'geojson', data: GEOJSON }});

  map.addLayer({{
    id: 'dcs-circles', type: 'circle', source: 'points',
    filter: ['==', ['get', 'layer'], 'dc'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 3, 50, 4, 200, 5, 500, 7, 1000, 9, 1500, 11, 3000, 14], 4],
        10, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 5, 50, 7, 200, 10, 500, 14, 1000, 19, 1500, 23, 3000, 30], 7]
      ],
      'circle-color': ['get', 'color'],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
      'circle-opacity': 0.9,
    }},
  }});

  map.addLayer({{
    id: 'projects-halo', type: 'circle', source: 'points',
    filter: ['==', ['get', 'layer'], 'project'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 10, 500, 15, 1500, 22, 3000, 30], 12],
        10, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 20, 500, 28, 1500, 40, 3000, 55], 22]
      ],
      'circle-color': '#cf222e',
      'circle-opacity': 0.18,
      'circle-stroke-width': 0,
    }},
  }});
  map.addLayer({{
    id: 'projects-circles', type: 'circle', source: 'points',
    filter: ['==', ['get', 'layer'], 'project'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 6, 500, 9, 1500, 13, 3000, 18], 7],
        10, ['case', ['>', ['to-number', ['get', 'mw']], 0],
            ['interpolate', ['linear'], ['to-number', ['get', 'mw']], 0, 12, 500, 17, 1500, 25, 3000, 34], 13]
      ],
      'circle-color': '#cf222e',
      'circle-stroke-width': 3,
      'circle-stroke-color': '#ffffff',
      'circle-opacity': 1.0,
    }},
  }});

  const popupFor = (f) => {{
    const p = f.properties;
    if (p.layer === 'project') {{
      return `
        <div class="regis-badge">REGIS PROJECT</div>
        <h3 style="margin-top:8px;">${{p.name}}</h3>
        <div class="dev">${{p.aka}} (${{p.county}} County) · ${{p.stage}}</div>
        <div class="field"><strong>Utility:</strong> ${{p.utility}}</div>
        ${{p.mw ? `<div class="field"><strong>Target capacity:</strong> ${{p.mw}} MW</div>` : ''}}
        <div class="field"><strong>Accuracy:</strong> ${{p.precise === 'true' || p.precise === true ? 'exact coords' : 'approximate'}}</div>
        ${{p.note ? `<div class="note">${{p.note}}</div>` : ''}}
      `;
    }}
    return `
      <h3>${{p.name || p.developer}}</h3>
      <div class="dev">${{p.developer}}</div>
      <div class="field"><strong>Status:</strong> ${{p.status}}</div>
      <div class="field"><strong>Market:</strong> ${{p.market}}</div>
      ${{p.mw ? `<div class="field"><strong>Capacity:</strong> ${{p.mw}} MW</div>` : ''}}
      ${{p.address ? `<div class="field"><strong>Address:</strong> ${{p.address}}</div>` : ''}}
      ${{p.owner ? `<div class="field"><strong>Regis owner:</strong> ${{p.owner}}</div>` : ''}}
      ${{p.note ? `<div class="note">${{p.note}}</div>` : ''}}
      ${{p.ss_url ? `<div class="field" style="margin-top:8px;"><a href="${{p.ss_url}}" target="_blank" style="color:#0969da; text-decoration:none; font-weight:600;">↗ Open row in Smartsheet</a></div>` : ''}}
    `;
  }};

  const clickHandler = (e) => {{
    const f = e.features[0];
    new mapboxgl.Popup({{ closeButton: true, maxWidth: '320px' }})
      .setLngLat(f.geometry.coordinates).setHTML(popupFor(f)).addTo(map);
  }};

  map.on('click', 'dcs-circles', clickHandler);
  map.on('click', 'projects-circles', clickHandler);
  ['dcs-circles', 'projects-circles'].forEach(id => {{
    map.on('mouseenter', id, () => {{ map.getCanvas().style.cursor = 'pointer'; }});
    map.on('mouseleave', id, () => {{ map.getCanvas().style.cursor = ''; }});
  }});

  const applyFilter = () => {{
    const market = document.getElementById('marketFilter').value;
    const status = document.getElementById('statusFilter').value;
    const conds = ['all', ['==', ['get', 'layer'], 'dc']];
    if (market) conds.push(['==', ['get', 'market'], market]);
    if (status) conds.push(['==', ['get', 'status_key'], status]);
    map.setFilter('dcs-circles', conds);
  }};
  document.getElementById('marketFilter').addEventListener('change', applyFilter);
  document.getElementById('statusFilter').addEventListener('change', applyFilter);

  const applyLayerToggle = () => {{
    const dcVis = document.getElementById('toggleDCs').checked ? 'visible' : 'none';
    const projVis = document.getElementById('toggleProjects').checked ? 'visible' : 'none';
    map.setLayoutProperty('dcs-circles', 'visibility', dcVis);
    map.setLayoutProperty('projects-circles', 'visibility', projVis);
    map.setLayoutProperty('projects-halo', 'visibility', projVis);
  }};
  document.getElementById('toggleDCs').addEventListener('change', applyLayerToggle);
  document.getElementById('toggleProjects').addEventListener('change', applyLayerToggle);

  const panel = document.getElementById('tablePanel');
  const tableBody = document.getElementById('tableBody');
  const searchBox = document.getElementById('tableSearch');
  let activeTab = 'regis';
  let sortCol = 'mw';
  let sortDir = 'desc';

  const features = GEOJSON.features;
  const regisFeatures = features.filter(f => f.properties.layer === 'project');
  const dcFeatures = features.filter(f => f.properties.layer === 'dc');
  document.getElementById('regisCount').textContent = regisFeatures.length;
  document.getElementById('dcCount').textContent = dcFeatures.length;

  const regisCols = [
    {{ key: 'name',     label: 'Project',     type: 'text'   }},
    {{ key: 'aka',      label: 'Location',    type: 'text'   }},
    {{ key: 'county',   label: 'County',      type: 'text'   }},
    {{ key: 'utility',  label: 'Utility',     type: 'text'   }},
    {{ key: 'mw',       label: 'MW',          type: 'num'    }},
    {{ key: 'stage',    label: 'Stage',       type: 'text'   }},
    {{ key: 'precise',  label: 'Coord',       type: 'bool'   }},
  ];
  const dcCols = [
    {{ key: 'developer', label: 'Developer',  type: 'text'   }},
    {{ key: 'name',      label: 'DC Name',    type: 'text'   }},
    {{ key: 'market',    label: 'Market',     type: 'text'   }},
    {{ key: 'mw',        label: 'MW',         type: 'num'    }},
    {{ key: 'status',    label: 'Status',     type: 'text'   }},
    {{ key: 'address',   label: 'Address',    type: 'text'   }},
    {{ key: 'owner',     label: 'Regis Owner',type: 'text'   }},
    {{ key: 'ss_url',    label: 'Smartsheet', type: 'link'   }},
  ];

  const getVal = (f, key) => {{
    const v = f.properties[key];
    return v === undefined || v === null ? '' : v;
  }};

  const renderTable = () => {{
    const cols = activeTab === 'regis' ? regisCols : dcCols;
    const data = activeTab === 'regis' ? [...regisFeatures] : [...dcFeatures];
    const searchTerm = (searchBox.value || '').toLowerCase().trim();
    const filtered = searchTerm
      ? data.filter(f => Object.values(f.properties).some(v => String(v).toLowerCase().includes(searchTerm)))
      : data;
    filtered.sort((a, b) => {{
      let av = getVal(a, sortCol); let bv = getVal(b, sortCol);
      const col = cols.find(c => c.key === sortCol);
      if (col && col.type === 'num') {{ av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; }}
      else {{ av = String(av).toLowerCase(); bv = String(bv).toLowerCase(); }}
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    }});
    const maxMW = Math.max(...data.map(f => parseFloat(getVal(f, 'mw')) || 0), 1);
    let html = '<table><thead><tr>';
    cols.forEach(c => {{
      const cls = c.key === sortCol ? `sort-${{sortDir}}` : '';
      html += `<th class="${{cls}}" data-col="${{c.key}}">${{c.label}}</th>`;
    }});
    html += '</tr></thead><tbody>';
    if (filtered.length === 0) {{
      html += `<tr><td colspan="${{cols.length}}" style="text-align:center; padding: 20px; color:#8b949e;">No results</td></tr>`;
    }} else {{
      filtered.forEach((f, idx) => {{
        const p = f.properties;
        const rowClass = activeTab === 'regis' ? 'regis' : '';
        html += `<tr class="${{rowClass}}" data-layer="${{activeTab}}" data-idx="${{idx}}">`;
        cols.forEach(c => {{
          let v = getVal(f, c.key);
          if (c.key === 'mw' && v) {{
            const mwNum = parseFloat(v) || 0;
            const pct = Math.min(100, (mwNum / maxMW) * 100);
            v = `<span class="mw-bar" style="width: ${{pct * 0.6}}px;"></span>${{mwNum.toLocaleString()}}`;
          }} else if (c.key === 'status' && v) {{
            v = `<span class="status-dot" style="background:${{p.color}}"></span>${{v}}`;
          }} else if (c.key === 'precise') {{
            v = v === true || v === 'true' ? 'exact' : 'approx';
          }} else if (c.key === 'ss_url') {{
            v = v ? `<a href="${{v}}" target="_blank" onclick="event.stopPropagation()" style="color:#0969da; text-decoration:none; font-weight:600;">↗ Open</a>` : '';
          }} else if (c.key === 'address' && v) {{
            v = `<span style="font-size:10px; color:#57606a;">${{v}}</span>`;
          }}
          html += `<td>${{v || '—'}}</td>`;
        }});
        html += '</tr>';
      }});
    }}
    html += '</tbody></table>';
    tableBody.innerHTML = html;
    tableBody.querySelectorAll('th').forEach(th => {{
      th.addEventListener('click', () => {{
        const col = th.dataset.col;
        if (sortCol === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else {{ sortCol = col; sortDir = 'desc'; }}
        renderTable();
      }});
    }});
    tableBody.querySelectorAll('tbody tr').forEach(tr => {{
      tr.addEventListener('click', () => {{
        const idx = parseInt(tr.dataset.idx, 10);
        const layer = tr.dataset.layer;
        const list = layer === 'regis' ? regisFeatures : dcFeatures;
        const fSrc = list[idx];
        if (!fSrc) return;
        map.flyTo({{ center: fSrc.geometry.coordinates, zoom: 11, duration: 1200 }});
        setTimeout(() => {{
          new mapboxgl.Popup({{ closeButton: true, maxWidth: '320px' }})
            .setLngLat(fSrc.geometry.coordinates).setHTML(popupFor(fSrc)).addTo(map);
        }}, 1250);
      }});
    }});
    document.getElementById('tableFooter').textContent =
      `Showing ${{filtered.length}} of ${{data.length}} · sorted by ${{sortCol}} ${{sortDir}} · click row to fly to pin`;
  }};

  sortCol = 'mw'; sortDir = 'desc';
  renderTable();

  document.querySelectorAll('.tp-tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
      document.querySelectorAll('.tp-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeTab = tab.dataset.tab;
      sortCol = 'mw'; sortDir = 'desc';
      renderTable();
    }});
  }});

  searchBox.addEventListener('input', renderTable);
  document.getElementById('openTable').addEventListener('click', () => panel.classList.add('open'));
  document.getElementById('closeTable').addEventListener('click', () => panel.classList.remove('open'));
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
