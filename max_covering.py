# -*- coding: utf-8 -*-
import math
import pandas as pd
from docplex.mp.model import Model


excel_file_path = r"C://Users//lalka//OneDrive//Desktop//UMKE-Facility-Data-1 (1).xlsx"


SHEET_POP = "District Population"
SHEET_DD  = "District Distance"
SHEET_DR  = "Distance - 25x20"   


df_population = pd.read_excel(excel_file_path, sheet_name=SHEET_POP)
df_dist_dist  = pd.read_excel(excel_file_path, sheet_name=SHEET_DD, index_col=0)
df_dist_road_raw = pd.read_excel(excel_file_path, sheet_name=SHEET_DR)


district_numbers_header = []
for col_i in range(2, df_dist_road_raw.shape[1]):
    val = df_dist_road_raw.iloc[0, col_i]
    if pd.notna(val) and isinstance(val, (int, float)):
        district_numbers_header.append(int(val))
    else:
        break

#"Road_Index" column then the district columns
n_dcols = len(district_numbers_header)
df_road_to_dist = df_dist_road_raw.iloc[:, 1:1 + n_dcols + 1].copy()
df_road_to_dist.columns = ["Road_Index"] + district_numbers_header


df_road_to_dist = df_road_to_dist.dropna(subset=["Road_Index"]).copy()
df_road_to_dist["Road_Index"] = df_road_to_dist["Road_Index"].astype(int)
df_road_to_dist = df_road_to_dist.set_index("Road_Index")

h = df_population.set_index("Districts")["Population"].to_dict()

# Sets
districts = list(df_dist_dist.index)                 # demand points (I)
road_locations = [f"Road_{i}" for i in df_road_to_dist.index.tolist()]  # road sites
candidate_locs = districts + road_locations          # facility candidates (J = districts ∪ roads)

distances_m = {}

# District-to-district 
for i in df_dist_dist.index:
    for j in df_dist_dist.columns:
        val = df_dist_dist.loc[i, j]
        if isinstance(val, str) and val.strip() == "-":
            val_m = math.inf
        else:
            try:
                val_m = float(val)
            except (TypeError, ValueError):
                val_m = math.inf
        distances_m[(i, j)] = val_m

# Road-to-district
for road_idx in df_road_to_dist.index:
    road_name = f"Road_{int(road_idx)}"
    for dist_id in df_road_to_dist.columns:
        val = df_road_to_dist.loc[road_idx, dist_id]
        if isinstance(val, str) and val.strip() == "-":
            val_m = math.inf
        else:
            try:
                val_m = float(val)
            except (TypeError, ValueError):
                val_m = math.inf
        distances_m[(road_name, dist_id)] = val_m

#unique labels
districts = pd.Index(districts).drop_duplicates().tolist()
candidate_locs = pd.Index(candidate_locs).drop_duplicates().tolist()


facility_limit = 4
radii_to_test = [2, 3, 4, 5, 6]  # km
total_population = sum(h[d] for d in districts if d in h)

print(f"  #Districts: {len(districts)}")
print(f"  #Road locations: {len(road_locations)}")
print(f"  #Candidate sites: {len(candidate_locs)}")
results_summary = []


for R in radii_to_test:
    print(f"\Running analysis for Service Radius R = {R} km")


    a = {}
    for i in candidate_locs:   
        for j in districts:     
            d_m = distances_m.get((i, j), math.inf)
            d_km = d_m / 1000.0 if math.isfinite(d_m) else math.inf
            a[(i, j)] = 1 if d_km <= R else 0


    mdl = Model(name=f"MCLP_R{R}")

    # Decision variables:
    # x[j] = 1 if district j is covered
    x = mdl.binary_var_dict(districts, name="x")
    # y[i] = 1 if a facility is opened at candidate i
    y = mdl.binary_var_dict(candidate_locs, name="y")

    # Objective: maximize covered population
    mdl.maximize(mdl.sum(h[j] * x[j] for j in districts if j in h))

    # Facility limit
    mdl.add_constraint(mdl.sum(y[i] for i in candidate_locs) <= facility_limit, ctname="facility_limit")

    # Coverage: for each district j, sum over facilities i that can cover j
    for j in districts:
        mdl.add_constraint(mdl.sum(a[(i, j)] * y[i] for i in candidate_locs) >= x[j], ctname=f"cover_{j}")

    sol = mdl.solve(log_output=False)
    if not sol:
        print(f"[FAIL] No feasible solution found for R = {R} km.")
        continue

    selected_locations = [i for i in candidate_locs if y[i].solution_value > 0.5]
    covered_districts = [j for j in districts if x[j].solution_value > 0.5]

    selected_districts = [loc for loc in selected_locations if loc in districts]
    selected_roads = [loc for loc in selected_locations if loc in road_locations]

    served_population = sum(h[j] for j in covered_districts if j in h)
    pct_served = 100.0 * served_population / total_population if total_population > 0 else 0.0

    print(f"R = {R} km | Obj (people covered) = {int(mdl.objective_value)}")
    print(f"  Population served: {pct_served:.2f}%")
    print(f"  Facilities opened: {selected_locations}")
    print(f"    - at Districts: {len(selected_districts)}")
    print(f"    - at Roads    : {len(selected_roads)}")
    print(f"  Total Covered districts: {len(covered_districts)}")

    results_summary.append({
        "R(km)": R,
        "People Covered": int(mdl.objective_value),
        "Coverage %": round(pct_served, 2),
        "Facilities": selected_locations,
        "Facilities@Districts": selected_districts,
        "Facilities@Roads": selected_roads,
        "Total Covered Districts": len(covered_districts),
    })



print("SUMMARY:")
for r in results_summary:
    print(f"R={r['R(km)']} → Covered={r['Coverage %']}% | Facilities={r['Facilities']}")
