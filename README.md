# IE479 Facility Location Optimization – UMKE Disaster Response

## Overview
This project addresses the strategic placement of emergency field health facilities for disaster response following a large-scale earthquake.

The objective is to determine optimal facility locations to ensure rapid medical response, accessibility, and efficient coverage of affected districts.

---

## Objectives
- Ensure all districts are covered within a service radius
- Maximize population coverage under limited resources
- Minimize total travel distance between districts and facilities

---

## Problem Description
Due to large-scale disasters, it is not feasible to deploy medical units at every location.

Instead, facilities must be strategically located:
- Near major roads for accessibility
- Within a service radius of affected districts
- To serve the largest possible population

---

## Models Implemented

### 1. Set Covering Model
- Objective: minimize number of facilities
- Ensures every district is covered
- Analyzed for different service radii

### 2. Maximal Covering Model (MCLP)
- Objective: maximize population covered
- Constraint: maximum number of facilities (p = 4)
- Evaluates trade-off between coverage and resources

### 3. P-Median Model
- Objective: minimize total distance
- Assigns each district to the nearest facility
- Ensures efficient emergency response

---

## Technologies Used
- Python
- Gurobi (gurobipy)
- CPLEX (docplex)
- Excel (data input)

---

## How to Run
1. Install required libraries:
```bash
pip install gurobipy docplex pandas
```

2. Place dataset in the data folder  

3. Run models:
```bash
python set_covering.py
python max_covering.py
python p_median.py
```

---

## Key Insights
- Increasing service radius reduces number of required facilities
- Full coverage achieved at relatively small radii
- Limited facility scenarios require prioritization of high-population areas
- Optimal locations remain stable for larger radii in distance-based models

---

## Industrial Engineering Perspective
This project demonstrates:
- Facility location optimization
- Trade-offs between cost, coverage, and distance
- Disaster response planning
- Resource allocation under constraints
- Multi-objective decision making

---

## Notes
This project applies classical operations research models to a real-world disaster management problem, demonstrating the role of optimization in emergency planning.
