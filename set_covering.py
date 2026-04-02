# -*- coding: utf-8 -*-
"""
Created on Mon Oct 20 16:19:55 2025

@author: Defne Karaman
"""

import gurobipy as gp
from gurobipy import GRB
import pandas as pd


excel_file_path = "UMKE-Facility-Data-1.xlsx"

# District-to-district distances
df_dist_dist = pd.read_excel(excel_file_path, sheet_name="District Distance", index_col=0)

# Road-to-district distances
df_dist_road_raw = pd.read_excel(excel_file_path, sheet_name="Distance - 25x20")

# convert to numeric
df_dist_road_raw = df_dist_road_raw.dropna(how="all", axis=0).dropna(how="all", axis=1)
df_dist_road = df_dist_road_raw.apply(pd.to_numeric, errors="coerce").dropna(how="all")

df_dist_road.index = [f"Road_{i+1}" for i in range(len(df_dist_road))]
df_dist_road.columns = [f"D{j+1}" for j in range(len(df_dist_road.columns))]

# Convert from meters → km
df_dist_road = df_dist_road / 1000.0
df_dist_dist = df_dist_dist / 1000.0


# BUILD SETS & DISTANCE DICTIONARY
districts = df_dist_dist.index.tolist()
road_locations = df_dist_road.index.tolist()
candidate_locs = districts + road_locations

distances = {}

# district–district
for i in df_dist_dist.index:
    for j in df_dist_dist.columns:
        distances[(i, j)] = df_dist_dist.loc[i, j]

# road–district
for road in df_dist_road.index:
    for dist_name in df_dist_road.columns:
        distances[(dist_name, road)] = df_dist_road.loc[road, dist_name]


# SOLVE FOR EACH SERVICE RADIUS
radii_to_test = [2, 3, 4, 5, 6]  # km
results_summary = []

print(f"Loaded {len(districts)} districts and {len(road_locations)} road candidates.")
print("Example distances (km):")
print(df_dist_road.head(), "\n")

for R in radii_to_test:
    print(f"\n Solving for Radius R = {R} km")

    m = gp.Model(f"SetCover_R{R}")
    m.Params.OutputFlag = 0

    x = m.addVars(candidate_locs, vtype=GRB.BINARY, name="x")

    # Coverage constraints
    for i in districts:
        m.addConstr(
            gp.quicksum(x[j] for j in candidate_locs
                        if distances.get((i, j), float("inf")) <= R) >= 1,
            name=f"cover_{i}"
        )

    # Objective: minimize # of facilities
    m.setObjective(gp.quicksum(x[j] for j in candidate_locs), GRB.MINIMIZE)

    m.optimize()

    if m.status == GRB.OPTIMAL:
        selected = [str(j) for j in candidate_locs if x[j].X > 0.5]  # convert all to str
        print(f" Optimal number of facilities: {len(selected)}")
        print(f" Chosen facility locations: {', '.join(selected)}")
    else:
        selected = []
        print(f" No feasible solution (status {m.status})")

    
    results_summary.append({
        "Radius (km)": R,
        "Min Facilities": len(selected),
        "Chosen Facilities": ", ".join(selected)
    })


# SUMMARY
print("\n FINAL SUMMARY ")
df_summary = pd.DataFrame(results_summary)
print(df_summary.to_string(index=False))


