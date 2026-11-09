#Data-Driven Framework Analysis and Predicting Waste Generation in Nigeria for Sustainable Waste Management
#waste_pipelie.py
#waste_projection.py
"""
Driver-based projection of waste generation and sustainability indicators for Nigeria (2023-2035).
pip install pandas numpy openpyxl matplotlib
python waste_projection.py     
Generation(state, t) = Generation_2023(state) x PopIndex(t) x PerCapitaMultiplier(t) x BaselineScale
PopIndex(t)              = UN national population(t) / population(2023)          [driver 1: population]
PerCapitaMultiplier(t)   = (UrbanShare(t) / UrbanShare(2023)) ** elasticity       [driver 2: urbanization]
Organic share(state, t)     = share_2023 + slope x per_capita_2023 x (multiplier - 1) [driver 3: composition shift]
"""
#Objecctives
- i.	assemble, screen and validate the available state-level and city-level waste data and document every correction.
- ii.	characterise the spatial distribution and composition of waste generation across states and geopolitical zones.
- iii.	evaluate forecasting methods on the only available high-frequency disposal record (Lagos, 2022 to 2024) and quantify the gap between disposal and estimated generation.
- iv.	project generation and organic waste to 2035 using population, urbanisation and composition as explicit drivers.
#Data sources
Three datasets were analysed, supplemented by published parameters 
- The state-level dataset, for each of 37 areas, the per capita generation rate (kg per person per day), the 2006 and 2023 populations, the organic fraction (%), and annual MSW and OFMSW (t per year) from Atughwe et al. (2026) for the state capitals.
- The Lagos dataset records trips and tonnage for each of five disposal sites (Olushosun, Solous, Badagry, Epe and Ikorodu) for 36 months from eko360. (n.d).
- Boundaries are 37 polygons in the WGS84 coordinate system.
- National population and urban share for 2023 to 2035 (D4) are from the United Nations World Population Prospects 2024, medium variant (United Nations, 2024).
#Tools & Technologies
- Analyses were run in Python using pandas, NumPy, statsmodels, GeoPandas and Matplotlib.
