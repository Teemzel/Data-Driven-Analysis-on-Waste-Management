#waste_pipelie.py
"""Nigeria waste data pipeline: clean -> map join -> Lagos forecast -> Excel/CSV/GeoJSON/PNG outputs.
Inputs : /mnt/user-data/uploads/{lagos_waste_data.xlsx, State Level OFMSW Amounts Generated - Nigeria.xlsx, nigeria_state_boundaries_geojson.txt}
Outputs: /mnt/user-data/outputs/ """
#waste_projection.py
"""
Driver-based projection of waste generation and sustainability indicators for Nigeria (2023-2035).
  Install once:    pip install pandas numpy openpyxl matplotlib
  Run:             python waste_projection.py     
  Generation(state, t) = Generation_2023(state) x PopIndex(t) x PerCapitaMultiplier(t) x BaselineScale
     PopIndex(t)              = UN national population(t) / population(2023)          [driver 1: population]
     PerCapitaMultiplier(t)   = (UrbanShare(t) / UrbanShare(2023)) ** elasticity       [driver 2: urbanization]
  Organic share(state, t)     = share_2023 + slope x per_capita_2023 x (multiplier - 1) [driver 3: composition shift]
"""
