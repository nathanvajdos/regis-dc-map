"""
Build a self-contained Mapbox GL JS HTML map from a list of Regis DC Locations.

Input: hardcoded DC list (extracted from Smartsheet via MCP).
Output: dc_locations_map.html — a single HTML file that loads Mapbox GL JS client-side
        and renders all DCs as color-coded pins with click-to-detail popups.

This is the v1 generator. The weekly trigger will extend it to pull fresh data from
Smartsheet every Monday.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

MAPBOX_TOKEN = "pk.eyJ1IjoibmF0aGFudmFqZG9zIiwiYSI6ImNtbzJnZHBlaDByemMycXB1eTVyeDR1eGEifQ.WTV3pptYpG_EFZ5Y11f07Q"

DCS = [
    # Developer, DC Name, Status, Primary Market, Address, City, County, State, Zip, MW, Owner
    {"developer": "Edged Energy", "name": "Edged Fort Worth", "status": "3_In Development", "market": "DFW", "address": None, "city": "Fort Worth", "county": None, "state": "TX", "zip": None, "mw": None, "owner": None, "note": "$1.1B hyperscaler DC; zoning approved Apr 8 2026"},
    {"developer": "Google (funded)", "name": "Goodnight Data Center", "status": "3_In Development", "market": "WEST", "address": None, "city": "Goodnight", "county": "Armstrong", "state": "TX", "zip": None, "mw": None, "owner": None, "note": "Google-funded; on-site gas plant per TX air permit"},
    {"developer": "Iron Mountain", "name": "Iron Mountain Austin Campus", "status": "3_In Development", "market": "AUS", "address": None, "city": "Austin", "county": None, "state": "TX", "zip": None, "mw": None, "owner": None, "note": "7-building campus planned outside Austin"},
    {"developer": "PowerHouse Data Centers", "name": "PowerHouse Irving DC1", "status": "2_Under Construction", "market": "DFW", "address": None, "city": "Irving", "county": None, "state": "TX", "zip": None, "mw": None, "owner": None, "note": "First Irving DC; topped out Mar 2026"},
    {"developer": "Microsoft", "name": "Microsoft Medina TX (2 sites)", "status": "3_In Development", "market": "SA", "address": None, "city": "Hondo", "county": "Medina", "state": "TX", "zip": None, "mw": None, "owner": None, "note": "$52M across 2 DCs in Medina County"},
    {"developer": "TBD (Nolan County $7B)", "name": "Nolan County $7B DC (Sweetwater)", "status": "3_In Development", "market": "WEST", "address": None, "city": "Sweetwater", "county": "Nolan", "state": "TX", "zip": None, "mw": None, "owner": None, "note": "$7B project; 10-yr tax abatement approved Apr 15 2026"},
    {"developer": "Concord New Energy (HK:00182)", "name": "Concord NE TX 1GW DC", "status": "3_In Development", "market": "OTHER", "address": None, "city": None, "county": None, "state": "TX", "zip": None, "mw": 1000, "owner": None, "note": "1 GW ERCOT approval; co-located w/ solar+BESS"},
    {"developer": "xAI", "name": "Colossus 2 (Mississippi)", "status": "2_Under Construction", "market": "OTHER", "address": None, "city": "Southaven", "county": None, "state": "MS", "zip": None, "mw": None, "owner": None, "note": "xAI Colossus 2; MS gas turbines approved Mar 2026"},
    {"developer": "ACS Infrastructure", "name": "ACS Fort Worth Campus", "status": "3_In Development", "market": "DFW", "address": "10059 Hicks Field Rd", "city": "Fort Worth", "county": "Tarrant", "state": "TX", "zip": "76179", "mw": None, "owner": None, "note": "107-acre greenfield; 5-building campus; $2B investment"},
    {"developer": "Centersquare", "name": "Centersquare Dallas/Fort Worth", "status": "1_Operating", "market": "DFW", "address": "14901 FAA Blvd", "city": "Fort Worth", "county": "Tarrant", "state": "TX", "zip": "76155", "mw": None, "owner": None, "note": None},
    {"developer": "Aligned Energy", "name": "DFW-03", "status": "2_Under Construction", "market": "DFW", "address": "3801 Britton Rd", "city": "Mansfield", "county": None, "state": "TX", "zip": None, "mw": 95, "owner": None, "note": "429,600 SF"},
    {"developer": "Skybox Datacenters", "name": "Skybox - Austin 1", "status": "1_Operating", "market": "AUS", "address": "600 New Meister Lane", "city": "Pflugerville", "county": None, "state": "TX", "zip": None, "mw": 30, "owner": "Nathan", "note": None},
    {"developer": "Skybox Datacenters", "name": "Skybox - Austin 2", "status": "2_Under Construction", "market": "AUS", "address": "2515 S Kenney Fort Blvd", "city": "Pflugerville", "county": "Travis", "state": "TX", "zip": None, "mw": None, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT5-SAT6", "status": "1_Operating", "market": "SA", "address": "14719 Omicron Drive", "city": "San Antonio", "county": None, "state": "TX", "zip": "78245", "mw": 18, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT1", "status": "1_Operating", "market": "SA", "address": "9999 Westover Hills Boulevard", "city": "San Antonio", "county": None, "state": "TX", "zip": "78251", "mw": 9, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT2-SAT4", "status": "1_Operating", "market": "SA", "address": "9554 Westover Hills Boulevard", "city": "San Antonio", "county": None, "state": "TX", "zip": "78251", "mw": 36, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT2", "status": "1_Operating", "market": "SA", "address": "9655 Raba Drive", "city": "San Antonio", "county": None, "state": "TX", "zip": "78251", "mw": None, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT3", "status": "1_Operating", "market": "SA", "address": "9655 Raba Drive", "city": "San Antonio", "county": None, "state": "TX", "zip": "78251", "mw": None, "owner": None, "note": None},
    {"developer": "Cyrus One", "name": "SAT4", "status": "1_Operating", "market": "SA", "address": "9655 Raba Drive", "city": "San Antonio", "county": None, "state": "TX", "zip": "78251", "mw": None, "owner": None, "note": None},
    {"developer": "H5 Data Centers", "name": "H5 San Antonio", "status": "1_Operating", "market": "SA", "address": "100 Taylor Street", "city": "San Antonio", "county": "Bexar", "state": "TX", "zip": "78205", "mw": None, "owner": "Donald", "note": "85,000 SF"},
    {"developer": "QTS Data Centers", "name": "San Antonio 2", "status": "1_Operating", "market": "SA", "address": "8535 Potranco Road", "city": "San Antonio", "county": "Bexar", "state": "TX", "zip": "78251", "mw": 90, "owner": "Nathan", "note": None},
    {"developer": "Rowan", "name": "Project Cinco", "status": "3_In Development", "market": "SA", "address": None, "city": "Lytle", "county": "Medina", "state": "TX", "zip": "78016", "mw": 300, "owner": None, "note": None},
    {"developer": "Stream", "name": "San Antonio II", "status": "1_Operating", "market": "SA", "address": "9550 Westover Hills Blvd", "city": "San Antonio", "county": "Bexar", "state": "TX", "zip": "78251", "mw": None, "owner": None, "note": None},
    {"developer": "Stream", "name": "San Antonio III", "status": "2_Under Construction", "market": "SA", "address": "11203 Military Drive W", "city": "San Antonio", "county": "Bexar", "state": "TX", "zip": None, "mw": 200, "owner": None, "note": None},
    {"developer": "Vantage", "name": "Frontier", "status": "2_Under Construction", "market": "WEST", "address": None, "city": "Albany", "county": "Shackelford", "state": "TX", "zip": None, "mw": 1400, "owner": None, "note": "Massive Frontier DC campus"},
    {"developer": "Lancium", "name": "Stargate (Oracle/OpenAI/SoftBank)", "status": "2_Under Construction", "market": "WEST", "address": "5502 Spinks Rd", "city": "Abilene", "county": None, "state": "TX", "zip": None, "mw": None, "owner": "Donald", "note": "Stargate anchor project"},
    {"developer": "Yondr Group", "name": "Yondr Lancaster", "status": "3_In Development", "market": "DFW", "address": None, "city": "Lancaster", "county": None, "state": "TX", "zip": None, "mw": 550, "owner": None, "note": None},
    {"developer": "Stack Infrastructure", "name": "DFW02", "status": "2_Under Construction", "market": "DFW", "address": "1000 East Beltline Drive", "city": "Lancaster", "county": None, "state": "TX", "zip": "75146", "mw": 500, "owner": "Nathan", "note": None},
    {"developer": "Equinix", "name": "Infomart Dallas", "status": "1_Operating", "market": "DFW", "address": "1990 North Stemmons Freeway", "city": "Dallas", "county": None, "state": "TX", "zip": "75207", "mw": 50, "owner": None, "note": None},
    {"developer": "Equinix", "name": "DA1", "status": "1_Operating", "market": "DFW", "address": "1950 N Stemmons Fwy", "city": "Dallas", "county": None, "state": "TX", "zip": "75207", "mw": None, "owner": None, "note": None},
    {"developer": "Equinix", "name": "DA11", "status": "1_Operating", "market": "DFW", "address": "1990 North Stemmons Freeway", "city": "Dallas", "county": None, "state": "TX", "zip": "75207", "mw": None, "owner": None, "note": None},
]


STATUS_COLORS = {
    "1_Operating": "#1a7f37",
    "2_Under Construction": "#e16f24",
    "3_In Development": "#0969da",
    "4_Proposed": "#8250df",
}


def geocode(query):
    """Call Mapbox Geocoding API v5 for an address string. Returns (lon, lat) or None."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"
        f"?access_token={MAPBOX_TOKEN}&country=us&limit=1&types=address,poi,place,locality"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        feats = data.get("features", [])
        if not feats:
            return None
        center = feats[0]["center"]
        return (center[0], center[1])  # lon, lat
    except Exception as e:
        print(f"  geocode error: {e}", file=sys.stderr)
        return None


def build_query(dc):
    parts = [p for p in [dc["address"], dc["city"], dc["county"], dc["state"], dc["zip"]] if p]
    if not parts:
        return None
    return ", ".join(parts)


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    features = []

    print(f"Geocoding {len(DCS)} DC locations via Mapbox...")
    for i, dc in enumerate(DCS):
        query = build_query(dc)
        if not query:
            print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} SKIP (no location)")
            continue
        coords = geocode(query)
        if not coords:
            print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} FAIL  ({query})")
            continue
        lon, lat = coords
        print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} OK    {lat:.4f}, {lon:.4f}")

        status_label = dc["status"].replace("1_", "").replace("2_", "").replace("3_", "").replace("4_", "")
        props = {
            "developer": dc["developer"],
            "name": dc["name"] or "",
            "status": status_label,
            "status_key": dc["status"],
            "market": dc["market"] or "",
            "mw": dc["mw"] or "",
            "owner": dc["owner"] or "",
            "note": dc["note"] or "",
            "color": STATUS_COLORS.get(dc["status"], "#6e7781"),
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )
        time.sleep(0.1)  # be polite to Mapbox

    geojson = {"type": "FeatureCollection", "features": features}

    html = generate_html(geojson)
    out_path = os.path.join(out_dir, "dc_locations_map.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    geojson_path = os.path.join(out_dir, "dc_locations.geojson")
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print(f"\n[OK] Geocoded {len(features)}/{len(DCS)} DCs.")
    print(f"[OK] Wrote {out_path}")
    print(f"[OK] Wrote {geojson_path}")


def generate_html(geojson):
    geojson_str = json.dumps(geojson)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Regis DC Locations - Competitive Map</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.css" rel="stylesheet" />
<script src="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.js"></script>
<style>
  body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  #map {{ position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}
  .map-overlay {{
    position: absolute; top: 14px; left: 14px; background: #fff;
    border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    padding: 14px 16px; font-size: 13px; z-index: 2; max-width: 280px;
  }}
  .map-overlay h1 {{ font-size: 15px; margin: 0 0 8px 0; color: #0d1117; }}
  .map-overlay p {{ margin: 4px 0; color: #57606a; font-size: 12px; }}
  .legend {{ margin-top: 10px; }}
  .legend-row {{ display: flex; align-items: center; margin: 3px 0; font-size: 12px; color: #24292f; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 1px solid rgba(0,0,0,0.1); }}
  .filter-controls {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid #d0d7de; }}
  .filter-controls label {{ display: block; font-size: 11px; color: #57606a; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
  .filter-controls select {{ width: 100%; padding: 5px; font-size: 12px; border: 1px solid #d0d7de; border-radius: 4px; background: #fff; color: #24292f; }}
  .mapboxgl-popup-content {{ font-family: -apple-system, 'Segoe UI', sans-serif; padding: 12px 14px; font-size: 12px; max-width: 280px; }}
  .mapboxgl-popup-content h3 {{ margin: 0 0 4px 0; font-size: 13px; color: #0d1117; }}
  .mapboxgl-popup-content .dev {{ font-size: 11px; color: #57606a; margin-bottom: 6px; font-weight: 500; }}
  .mapboxgl-popup-content .field {{ margin: 3px 0; color: #24292f; }}
  .mapboxgl-popup-content .field strong {{ color: #57606a; font-weight: 500; min-width: 60px; display: inline-block; }}
  .mapboxgl-popup-content .note {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #eaeef2; font-style: italic; color: #57606a; font-size: 11px; }}
  .footer {{ position: absolute; bottom: 8px; left: 14px; background: #fff; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #57606a; box-shadow: 0 1px 4px rgba(0,0,0,0.1); z-index: 2; }}
  .footer a {{ color: #0969da; text-decoration: none; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="map-overlay">
  <h1>Regis — DC Competitive Map</h1>
  <p>{len(geojson['features'])} data centers tracked · Auto-updated every Monday 7am CT</p>
  <div class="legend">
    <div class="legend-row"><span class="legend-dot" style="background:#1a7f37"></span>Operating</div>
    <div class="legend-row"><span class="legend-dot" style="background:#e16f24"></span>Under Construction</div>
    <div class="legend-row"><span class="legend-dot" style="background:#0969da"></span>In Development</div>
    <div class="legend-row"><span class="legend-dot" style="background:#8250df"></span>Proposed</div>
  </div>
  <div class="filter-controls">
    <label for="marketFilter">Market</label>
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
    <label for="statusFilter">Status</label>
    <select id="statusFilter">
      <option value="">All statuses</option>
      <option value="1_Operating">Operating</option>
      <option value="2_Under Construction">Under Construction</option>
      <option value="3_In Development">In Development</option>
      <option value="4_Proposed">Proposed</option>
    </select>
  </div>
</div>
<div class="footer">
  Source: <a href="https://app.smartsheet.com/sheets/MfQHrM892gvWm38j44Vh3C5R2X3xxjxvC6G89vQ1" target="_blank">Smartsheet DC Locations</a>
  · Prepared for Regis Energy Partners
</div>
<script>
mapboxgl.accessToken = '{MAPBOX_TOKEN}';
const GEOJSON = {geojson_str};

const map = new mapboxgl.Map({{
  container: 'map',
  style: 'mapbox://styles/mapbox/light-v11',
  center: [-99.5, 31.2],
  zoom: 5.2,
  minZoom: 3,
  maxZoom: 17,
}});
map.addControl(new mapboxgl.NavigationControl(), 'top-right');
map.addControl(new mapboxgl.FullscreenControl(), 'top-right');
map.addControl(new mapboxgl.ScaleControl({{ maxWidth: 120, unit: 'imperial' }}), 'bottom-right');

map.on('load', () => {{
  map.addSource('dcs', {{ type: 'geojson', data: GEOJSON }});
  map.addLayer({{
    id: 'dcs-circles',
    type: 'circle',
    source: 'dcs',
    paint: {{
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 5, 12, 10, 16, 18],
      'circle-color': ['get', 'color'],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
      'circle-opacity': 0.9,
    }},
  }});

  map.on('click', 'dcs-circles', (e) => {{
    const f = e.features[0];
    const p = f.properties;
    const html = `
      <h3>${{p.name || p.developer}}</h3>
      <div class="dev">${{p.developer}}</div>
      <div class="field"><strong>Status:</strong> ${{p.status}}</div>
      <div class="field"><strong>Market:</strong> ${{p.market}}</div>
      ${{p.mw ? `<div class="field"><strong>Capacity:</strong> ${{p.mw}} MW</div>` : ''}}
      ${{p.owner ? `<div class="field"><strong>Regis owner:</strong> ${{p.owner}}</div>` : ''}}
      ${{p.note ? `<div class="note">${{p.note}}</div>` : ''}}
    `;
    new mapboxgl.Popup({{ closeButton: true, maxWidth: '300px' }})
      .setLngLat(f.geometry.coordinates)
      .setHTML(html)
      .addTo(map);
  }});

  map.on('mouseenter', 'dcs-circles', () => {{ map.getCanvas().style.cursor = 'pointer'; }});
  map.on('mouseleave', 'dcs-circles', () => {{ map.getCanvas().style.cursor = ''; }});

  const applyFilter = () => {{
    const market = document.getElementById('marketFilter').value;
    const status = document.getElementById('statusFilter').value;
    const conds = ['all'];
    if (market) conds.push(['==', ['get', 'market'], market]);
    if (status) conds.push(['==', ['get', 'status_key'], status]);
    map.setFilter('dcs-circles', conds.length > 1 ? conds : null);
  }};
  document.getElementById('marketFilter').addEventListener('change', applyFilter);
  document.getElementById('statusFilter').addEventListener('change', applyFilter);
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
