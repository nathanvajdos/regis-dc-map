"""
Build a self-contained Mapbox GL JS HTML map from Regis DC Locations
+ Regis project sites as a distinct layer.

Input: hardcoded DC list (extracted from Smartsheet DC Locations Sheet)
       + hardcoded Regis project site list (from DC Land Sheet + emails).
Output: index.html  — single HTML file with two layers.

Run: python build_map.py
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

MAPBOX_TOKEN = "pk.eyJ1IjoibmF0aGFudmFqZG9zIiwiYSI6ImNtbzJnZHBlaDByemMycXB1eTVyeDR1eGEifQ.WTV3pptYpG_EFZ5Y11f07Q"

# ============================================================================
# COMPETITOR DATA CENTERS (from Smartsheet DC Locations Sheet)
# ============================================================================
DCS = [
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

# ============================================================================
# REGIS PROJECT SITES (from SharePoint Active Projects folder + email coords)
# ============================================================================
# Active Projects per SharePoint (bizdev/08_Data Center Development/03_DC Projects by Utility/Active Projects):
#   Sumlin (Laredo), Price (Hillsboro), Carswell (Corsicana), Elko (Schertz),
#   Fisher (Clear Fork), Kubiak (Houston).
# Plus Oklaunion (Wilbarger) — in early diligence per Regis-internal POI email
# (not yet in Active Projects SharePoint folder).
#
# Coords are approximate city centroids unless flagged "precise".
# KMZ boundaries live in SharePoint project folders; pull precise coords later.
PROJECTS = [
    {"name": "Sumlin",    "aka": "Laredo",     "county": "Webb",     "utility": "AEP Texas",   "lon": -99.275759, "lat": 27.578866, "stage": "Executed LOA: 300 MW N. Laredo Switch + 500 MW Lobo pending", "mw": "800",   "note": "Lobo Substation / Project Site on FM 255, ~5 mi north of Laredo, Webb County. Executed AEP LOA for 300 MW via North Laredo Switch (Q1 2029 / Q2 2030 ISD). Lobo 500 MW secondary request pending (Apr 17 2026 memo). Hachar Family Trust: 688 ac primary + 1,198 ac expansion = 1,886 ac. EXACT coordinate from Lobo 500 MW memo.", "precise": True},
    {"name": "Price",     "aka": "Hillsboro",  "county": "Hill",     "utility": "Oncor",       "lon": -96.958196, "lat": 31.915673, "stage": "POI analysis done",         "mw": "1500",  "note": "Hill County, TX. 1.5 GW BTM Gas + Grid target. Sam Switch POI delivered Apr 10 2026 by Donald. EXACT coordinate from Regis POI email. Master KMZ: /Price (Hillsboro)/10 - KMZ & GIS/Price_Master_KMZ_2026-04-09_agent.kmz.", "precise": True},
    {"name": "Carswell",  "aka": "Corsicana",  "county": "Navarro",  "utility": "Oncor (dual w/ Navarro EC)", "lon": -96.499874, "lat": 31.963114, "stage": "Active development",        "mw": "1500",  "note": "7 miles SW of Corsicana, TX (Navarro County) — NOT Fort Worth/Carswell AFB. Substation S+W of Corsicana, adjacent to Riot Blockchain facility. 622 ac pursuing LOI + 100+ ac expansion w/ multiple landowners. Oncor 345kV + Atmos 10.75\" pipeline. 1.5 GW target (300 MW BTM gas by 2028, 250 MW grid expanding). EXACT coordinate from Feb 11 2026 Regis Portfolio Overview.", "precise": True},
    {"name": "Elko",      "aka": "Schertz",    "county": "Guadalupe","utility": "CPS Energy",  "lon": -98.2697,   "lat": 29.6321,   "stage": "INFERENCE project",         "mw": "250",   "note": "Tri-County substation, Schertz, TX (Guadalupe County, NE San Antonio). Flagged INFERENCE project (not full data center) per Regis Fee Breakdown. City centroid approximate — Tri-County substation precise coord still needed (pending Donald). Planned 250 MW.", "precise": False},
    {"name": "Fisher",    "aka": "Lockhart",   "county": "Caldwell", "utility": "BBEC",        "lon": -97.726184, "lat": 29.859999, "stage": "Active development",        "mw": "1500",  "note": "1 mile SW of Lockhart, TX (Caldwell County — NOT Fisher County; DC Land Sheet was stale). Served by BBEC (Bluebonnet EC). 327 ac LOI in negotiation + 579 ac expansion w/ 2 landowners. Kinder Morgan 42\" + Energy Transfer 20\" gas pipelines adjacent. LCRA 345kV. 1.5 GW target (287 MW BTM gas 2028, 40-74 MW grid expanding). 25 mi from Austin Bergstrom. EXACT coordinate from Feb 11 2026 Regis Portfolio Overview.", "precise": True},
    {"name": "Kubiak",    "aka": "Houston",    "county": "Harris",   "utility": "CenterPoint 345kV", "lon": -95.3698, "lat": 29.7604, "stage": "Pre-site control (no land yet)", "mw": "1200",  "note": "Houston, TX (Harris County). 1,200 MW target on CenterPoint 345kV. Per Apr 11 2026 assessment: NO lead, NO land, NO model clarity (32% probability of success). Strong macro fundamentals (Houston gas liquidity, labor, fiber, water) but worst execution status. Houston centroid used as placeholder pin until land is identified.", "precise": False},
]

STATUS_COLORS = {
    "1_Operating": "#1a7f37",
    "2_Under Construction": "#e16f24",
    "3_In Development": "#0969da",
    "4_Proposed": "#8250df",
}


def geocode(query):
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
        return (center[0], center[1])
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

    # ---- Geocode DCs ----
    dc_features = []
    print(f"Geocoding {len(DCS)} competitor DCs...")
    for i, dc in enumerate(DCS):
        query = build_query(dc)
        if not query:
            print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} SKIP")
            continue
        coords = geocode(query)
        if not coords:
            print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} FAIL")
            continue
        lon, lat = coords
        print(f"  [{i+1:>2}/{len(DCS)}] {dc['developer']:<30} OK")
        status_label = dc["status"].replace("1_", "").replace("2_", "").replace("3_", "").replace("4_", "")
        dc_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
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
                "color": STATUS_COLORS.get(dc["status"], "#6e7781"),
            },
        })
        time.sleep(0.1)

    # ---- Regis project sites (pre-coded coordinates) ----
    project_features = []
    print(f"\nAdding {len(PROJECTS)} Regis project sites...")
    for p in PROJECTS:
        print(f"  * Project {p['name']:<10} ({'EXACT' if p['precise'] else 'approx'}) {p['aka']:<12} -> {p['lat']:.4f}, {p['lon']:.4f}")
        project_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "layer": "project",
                "developer": "REGIS",
                "name": f"Project {p['name']}",
                "aka": p["aka"],
                "county": p["county"],
                "utility": p["utility"],
                "stage": p["stage"],
                "mw": p.get("mw", ""),
                "note": p["note"],
                "precise": p["precise"],
                "color": "#cf222e",
            },
        })

    features = dc_features + project_features
    geojson = {"type": "FeatureCollection", "features": features}

    with open(os.path.join(out_dir, "dc_locations.geojson"), "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(generate_html(geojson, len(dc_features), len(project_features)))

    print(f"\n[OK] {len(dc_features)} DCs + {len(project_features)} Regis projects = {len(features)} pins total.")
    print(f"[OK] Wrote index.html and dc_locations.geojson in {out_dir}")


def generate_html(geojson, n_dcs, n_projects):
    geojson_str = json.dumps(geojson)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Regis DC Competitive Map + Project Sites</title>
<meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no" />
<link href="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.css" rel="stylesheet" />
<script src="https://api.mapbox.com/mapbox-gl-js/v3.9.1/mapbox-gl.js"></script>
<style>
  body {{ margin: 0; padding: 0; font-family: -apple-system, 'Segoe UI', Arial, sans-serif; }}
  #map {{ position: absolute; top: 0; bottom: 0; left: 0; right: 0; }}
  .map-overlay {{
    position: absolute; top: 14px; left: 14px; background: #fff;
    border-radius: 6px; box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    padding: 14px 16px; font-size: 13px; z-index: 2; max-width: 300px;
  }}
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
  #tablePanel {{
    position: absolute; top: 0; right: 0; bottom: 0; width: 540px; max-width: 90vw;
    background: #fff; box-shadow: -4px 0 16px rgba(0,0,0,0.15); z-index: 3;
    transform: translateX(100%); transition: transform 0.25s ease-out;
    display: flex; flex-direction: column; overflow: hidden;
  }}
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
  .tp-body .flyto {{ color: #0969da; cursor: pointer; text-decoration: none; font-size: 10px; margin-left: 6px; }}
  .tp-footer {{ padding: 6px 12px; border-top: 1px solid #d0d7de; font-size: 10px; color: #57606a; background: #f6f8fa; }}
</style>
</head>
<body>
<div id="map"></div>
<div class="map-overlay">
  <h1>Regis DC Competitive Map</h1>
  <p>{n_dcs} competitor DCs + {n_projects} Regis project sites · Auto-updated Mon 7am CT</p>
  <div class="legend">
    <h2>Competitor DCs</h2>
    <div class="legend-row"><span class="legend-dot" style="background:#1a7f37"></span>Operating</div>
    <div class="legend-row"><span class="legend-dot" style="background:#e16f24"></span>Under Construction</div>
    <div class="legend-row"><span class="legend-dot" style="background:#0969da"></span>In Development</div>
    <div class="legend-row"><span class="legend-dot" style="background:#8250df"></span>Proposed</div>
    <h2>Regis Projects</h2>
    <div class="legend-row"><span class="legend-star">★</span>Project site (red star)</div>
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
      <option value="3_In Development">In Development</option>
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
  <button class="table-toggle" id="openTable">📋 Open Summary Table</button>
  <p style="font-size: 10px; color: #8b949e; margin-top: 8px;">Pin size = MW capacity (area ∝ MW).</p>
</div>

<div id="tablePanel">
  <div class="tp-header">
    <h2>Summary Tables</h2>
    <button class="tp-close" id="closeTable">×</button>
  </div>
  <div class="tp-tabs">
    <button class="tp-tab active" data-tab="regis">Regis Projects (<span id="regisCount">0</span>)</button>
    <button class="tp-tab" data-tab="dcs">Competitor DCs (<span id="dcCount">0</span>)</button>
  </div>
  <div class="tp-search">
    <input type="text" id="tableSearch" placeholder="Search by name, developer, market, county…">
  </div>
  <div class="tp-body" id="tableBody"></div>
  <div class="tp-footer" id="tableFooter">Click any row to zoom to that pin. Click a column header to sort.</div>
</div>

<div class="footer">
  Source: <a href="https://app.smartsheet.com/sheets/MfQHrM892gvWm38j44Vh3C5R2X3xxjxvC6G89vQ1" target="_blank">Smartsheet DC Locations</a>
  · Regis project sites from DC Land Sheet + POI emails
</div>
<script>
mapboxgl.accessToken = '{MAPBOX_TOKEN}';
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

  // ----- MW-based radius formulas -----
  // Radius scales with sqrt(MW) since area ∝ MW (area-proportional sizing).
  // Defaults are used when MW is missing/0 so every pin is visible.

  // DC layer — circle area proportional to MW capacity
  map.addLayer({{
    id: 'dcs-circles',
    type: 'circle',
    source: 'points',
    filter: ['==', ['get', 'layer'], 'dc'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 3, 50, 4, 200, 5, 500, 7, 1000, 9, 1500, 11, 3000, 14],
          4
        ],
        10, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 5, 50, 7, 200, 10, 500, 14, 1000, 19, 1500, 23, 3000, 30],
          7
        ]
      ],
      'circle-color': ['get', 'color'],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
      'circle-opacity': 0.9,
    }},
  }});

  // Regis project layer — larger base size, MW-scaled, with halo
  map.addLayer({{
    id: 'projects-halo',
    type: 'circle',
    source: 'points',
    filter: ['==', ['get', 'layer'], 'project'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 10, 500, 15, 1500, 22, 3000, 30],
          12
        ],
        10, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 20, 500, 28, 1500, 40, 3000, 55],
          22
        ]
      ],
      'circle-color': '#cf222e',
      'circle-opacity': 0.18,
      'circle-stroke-width': 0,
    }},
  }});
  map.addLayer({{
    id: 'projects-circles',
    type: 'circle',
    source: 'points',
    filter: ['==', ['get', 'layer'], 'project'],
    paint: {{
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 6, 500, 9, 1500, 13, 3000, 18],
          7
        ],
        10, [
          'case',
          ['>', ['to-number', ['get', 'mw']], 0],
          ['interpolate', ['linear'], ['to-number', ['get', 'mw']],
            0, 12, 500, 17, 1500, 25, 3000, 34],
          13
        ]
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
        <div class="field"><strong>Accuracy:</strong> ${{p.precise === 'true' ? 'exact coords (from POI email)' : 'approximate — city/county centroid; precise KMZ in SharePoint'}}</div>
        ${{p.note ? `<div class="note">${{p.note}}</div>` : ''}}
      `;
    }}
    return `
      <h3>${{p.name || p.developer}}</h3>
      <div class="dev">${{p.developer}}</div>
      <div class="field"><strong>Status:</strong> ${{p.status}}</div>
      <div class="field"><strong>Market:</strong> ${{p.market}}</div>
      ${{p.mw ? `<div class="field"><strong>Capacity:</strong> ${{p.mw}} MW</div>` : ''}}
      ${{p.owner ? `<div class="field"><strong>Regis owner:</strong> ${{p.owner}}</div>` : ''}}
      ${{p.note ? `<div class="note">${{p.note}}</div>` : ''}}
    `;
  }};

  const clickHandler = (e) => {{
    const f = e.features[0];
    new mapboxgl.Popup({{ closeButton: true, maxWidth: '320px' }})
      .setLngLat(f.geometry.coordinates)
      .setHTML(popupFor(f))
      .addTo(map);
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

  // ============================================================
  // Summary Table Panel
  // ============================================================
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
    {{ key: 'owner',     label: 'Regis Owner',type: 'text'   }},
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
      ? data.filter(f => {{
          const props = f.properties;
          return Object.values(props).some(v => String(v).toLowerCase().includes(searchTerm));
        }})
      : data;

    filtered.sort((a, b) => {{
      let av = getVal(a, sortCol);
      let bv = getVal(b, sortCol);
      const col = cols.find(c => c.key === sortCol);
      if (col && col.type === 'num') {{
        av = parseFloat(av) || 0; bv = parseFloat(bv) || 0;
      }} else {{
        av = String(av).toLowerCase(); bv = String(bv).toLowerCase();
      }}
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
        const dataId = `${{f.geometry.coordinates[0]}},${{f.geometry.coordinates[1]}}`;
        html += `<tr class="${{rowClass}}" data-coords="${{dataId}}" data-layer="${{activeTab}}" data-idx="${{idx}}">`;
        cols.forEach(c => {{
          let v = getVal(f, c.key);
          if (c.key === 'mw' && v) {{
            const mwNum = parseFloat(v) || 0;
            const pct = Math.min(100, (mwNum / maxMW) * 100);
            v = `<span class="mw-bar" style="width: ${{pct * 0.6}}px;"></span>${{mwNum.toLocaleString()}}`;
          }} else if (c.key === 'status' && v) {{
            v = `<span class="status-dot" style="background:${{p.color}}"></span>${{v}}`;
          }} else if (c.key === 'precise') {{
            v = v === true || v === 'true' ? '✅ exact' : '~ approx';
          }}
          html += `<td>${{v || '—'}}</td>`;
        }});
        html += '</tr>';
      }});
    }}
    html += '</tbody></table>';
    tableBody.innerHTML = html;

    // Header click to sort
    tableBody.querySelectorAll('th').forEach(th => {{
      th.addEventListener('click', () => {{
        const col = th.dataset.col;
        if (sortCol === col) {{
          sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        }} else {{
          sortCol = col;
          sortDir = 'desc';
        }}
        renderTable();
      }});
    }});

    // Row click to fly-to
    tableBody.querySelectorAll('tbody tr').forEach(tr => {{
      tr.addEventListener('click', () => {{
        const coords = tr.dataset.coords;
        const idx = parseInt(tr.dataset.idx, 10);
        const layer = tr.dataset.layer;
        const list = layer === 'regis' ? regisFeatures : dcFeatures;
        const fSrc = list[idx] || list.find(ff => `${{ff.geometry.coordinates[0]}},${{ff.geometry.coordinates[1]}}` === coords);
        if (!fSrc) return;
        map.flyTo({{ center: fSrc.geometry.coordinates, zoom: 11, duration: 1200 }});
        setTimeout(() => {{
          new mapboxgl.Popup({{ closeButton: true, maxWidth: '320px' }})
            .setLngLat(fSrc.geometry.coordinates)
            .setHTML(popupFor(fSrc))
            .addTo(map);
        }}, 1250);
      }});
    }});

    document.getElementById('tableFooter').textContent =
      `Showing ${{filtered.length}} of ${{data.length}} · sorted by ${{sortCol}} ${{sortDir}} · click row to fly to pin`;
  }};

  // Default: sort Regis by MW desc initially
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

  document.getElementById('openTable').addEventListener('click', () => {{
    panel.classList.add('open');
  }});
  document.getElementById('closeTable').addEventListener('click', () => {{
    panel.classList.remove('open');
  }});
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
