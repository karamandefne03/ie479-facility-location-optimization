# -*- coding: utf-8 -*-
"""
Created on Fri Oct 17 22:49:10 2025

@author: Defne Karaman
"""


import gurobipy as gp
from gurobipy import GRB
import pandas as pd


# DATA
excel_file_path = "UMKE-Facility-Data-1.xlsx"

df_population = pd.read_excel(excel_file_path, sheet_name="District Population")
df_dist_dist = pd.read_excel(excel_file_path, sheet_name="District Distance", index_col=0)
df_dist_road = pd.read_excel(excel_file_path, sheet_name="Distance - 25x20")

# population data
df_population.columns = [c.strip() for c in df_population.columns]

# sets
districts = df_dist_dist.index.tolist()          # 20 districts expected
df_dist_road_raw = pd.read_excel(excel_file_path,
                                 sheet_name="Distance - 25x20",
                                 header=None)

# Row 0 has district numbers in columns 2 +
district_numbers = []
for i in range(2, df_dist_road_raw.shape[1]):
    val = df_dist_road_raw.iloc[0, i]
    if pd.notna(val) and isinstance(val, (int, float)):
        district_numbers.append(int(val))
    else:
        break

# road → district distance matrix
df_road_to_dist = df_dist_road.iloc[:, 1:1 + len(district_numbers) + 1].copy()
df_road_to_dist.columns = ["Road_Index"] + district_numbers
df_road_to_dist = df_road_to_dist.dropna(subset=["Road_Index"])
df_road_to_dist = df_road_to_dist.set_index("Road_Index")

# road and candidate sets 
road_locations = [f"Road_{int(i)}" for i in df_road_to_dist.index.tolist()]
candidate_locs = districts + road_locations

# population dictionary 
population = {}
for i in districts:
    row = df_population[df_population.iloc[:, 0] == i]
    if not row.empty:
        population[i] = float(row.iloc[0, 1])
    else:
        population[i] = 1000.0  # default if missing
        print(f" Population missing for district {i}; defaulting to 1000")

# distance dictionary (converted to km) 
distances = {}

# District ↔ district
for i in df_dist_dist.index:
    for j in df_dist_dist.columns:
        val = float(df_dist_dist.loc[i, j])
        distances[(i, j)] = val / 1000.0  # convert m → km if needed

# Road → district
for road_id in df_road_to_dist.index:
    road_name = f"Road_{int(road_id)}"
    for dist_id in df_road_to_dist.columns:
        val = float(df_road_to_dist.loc[road_id, dist_id])
        distances[(dist_id, road_name)] = val / 1000.0  # convert m → km

# Symmetry: district → road
for i in districts:
    for j in road_locations:
        if (i, j) not in distances:
            rid = int(j.split("_")[1])
            if rid in df_road_to_dist.index and i in df_road_to_dist.columns:
                distances[(i, j)] = float(df_road_to_dist.loc[rid, i]) / 1000.0
            else:
                distances[(i, j)] = float("inf")

# PARAMETERS
radii_to_test = [3, 4, 5, 6]   # km
p = 4                           # number of facilities to open
results_summary = []
detailed_assignments = {}

print(f"Districts: {len(districts)} | Road locations: {len(road_locations)} | "
      f"Candidates: {len(candidate_locs)} | Facilities to open: {p}")
print(f"Service radii tested: {radii_to_test} km")

# OPTIMIZATION
for R in radii_to_test:
    print(f"\n Solving for Service Radius R = {R} km ")

    # Coverage parameter a[i,j]
    a = {(i, j): 1 if distances.get((i, j), float("inf")) <= R else 0
         for i in districts for j in candidate_locs}

    # Model definition
    m = gp.Model(f"pMedian_R{R}")
    x = m.addVars(candidate_locs, vtype=GRB.BINARY, name="facility")
    y = m.addVars(districts, candidate_locs, vtype=GRB.BINARY, name="assign")

    # Objective: minimize total distance ( km )
    m.setObjective(gp.quicksum(distances[(i, j)] * y[i, j]
                               for i in districts for j in candidate_locs
                               if distances.get((i, j), float("inf")) < float("inf")),
                   GRB.MINIMIZE)

    # Constraints
    for i in districts:
        m.addConstr(gp.quicksum(y[i, j] for j in candidate_locs) == 1)      # assignment
    m.addConstr(gp.quicksum(x[j] for j in candidate_locs) == p)             # facility count
    for i in districts:
        for j in candidate_locs:
            m.addConstr(y[i, j] <= x[j])                                    
            if a[i, j] == 0:
                m.addConstr(y[i, j] == 0)                                   # coverage limit

   
    m.Params.OutputFlag = 0
    m.optimize()

    # Results
    if m.status == GRB.OPTIMAL:
        print(f" Optimal solution found for R = {R} km")

        selected = [j for j in candidate_locs if x[j].X > 0.5]
        assignments = {i: j for i in districts for j in candidate_locs if y[i, j].X > 0.5}

        total_dist = m.ObjVal
        pop_weighted = sum(population[i] * distances[(i, assignments[i])] for i in districts)
        max_dist = max(distances[(i, assignments[i])] for i in districts)
        avg_dist = total_dist / len(districts)

        print(f"  Facilities selected: {selected}")
        print(f"  Total distance: {total_dist:.2f} km | "
              f"Population-weighted: {pop_weighted:.2f} person-km | "
              f"Max distance: {max_dist:.2f} km")

        results_summary.append({
            "Radius (km)": R,
            "Selected Facilities": ", ".join(str(s) for s in selected),
            "Total Distance (km)": f"{total_dist:.2f}",
            "Pop-Weighted (person-km)": f"{pop_weighted:.2f}",
            "Average Distance (km)": f"{avg_dist:.3f}",
            "Maximum Distance (km)": f"{max_dist:.2f}"
        })

        # assignment table
        detailed_assignments[f"R_{R}km"] = [
            {"District": i,
             "Assigned Facility": assignments[i],
             "Distance (km)": round(distances[(i, assignments[i])], 2),
             "Population": int(population[i]),
             "Pop × Dist": round(population[i] * distances[(i, assignments[i])], 2)}
            for i in districts
        ]
    else:
        print(f" No feasible solution for R = {R} km (status {m.status})")
        results_summary.append({
            "Radius (km)": R,
            "Selected Facilities": "INFEASIBLE",
            "Total Distance (km)": "N/A",
            "Pop-Weighted (person-km)": "N/A",
            "Average Distance (km)": "N/A",
            "Maximum Distance (km)": "N/A"
        })
        detailed_assignments[f"R_{R}km"] = None

# RESULT SUMMARY

print("\n")
print("SUMMARY OF RESULTS – PROBLEM 3")

df_summary = pd.DataFrame(results_summary)
print(df_summary.to_string(index=False))


