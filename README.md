#Data-Driven Framework Analysis and Predicting Waste Generation in Nigeria for Sustainable Waste Management
#Project overview
-This project studies how much waste Nigeria produces now and how much it is likely to produce up to 2035. It uses real data and shows what the numbers mean for managing waste sustainably.
-There are three parts:
`#waste_pipelie.py`
- Describe: clean the available data and map where waste is generated and what it is made of.
- Test: use the Lagos monthly dumpsite records to find which forecasting method works best.
`#waste_projection.py`
- Project: estimate national and state waste to 2035 under low, central and high assumptions about how fast cities grow.
#Research Questions
- Data quality: Which of the available waste data can be trusted, and what corrections does it need?
- Spatial pattern: Where in Nigeria is waste generated, and how much of it is organic?
- Forecasting: Which simple method best predicts waste reaching the Lagos dumpsites, and how much of Lagos’s estimated waste actually reaches them?
- Projection: How much waste and organic waste will Nigeria generate by 2035 if population and urbanisation grow as projected?

#Objecctives
- i.	assemble, screen and validate the available state-level and city-level waste data and document every correction.
- ii.	characterise the spatial distribution and composition of waste generation across states and geopolitical zones.
- iii.	evaluate forecasting methods on the only available high-frequency disposal record (Lagos, 2022 to 2024) and quantify the gap between disposal and estimated generation.
- iv.	project generation and organic waste to 2035 using population, urbanisation and composition as explicit drivers.
#Data sources and description
`Three datasets were analysed, supplemented by published parameters` 
- The state-level dataset, for each of 37 areas, the per capita generation rate (kg per person per day), the 2006 and 2023 populations, the organic fraction (%), and annual MSW and OFMSW (t per year) from Atughwe et al. (2026) for the state capitals. https://zenodo.org/records/22206719
- The Lagos dataset records trips and tonnage for each of five disposal sites (Olushosun, Solous, Badagry, Epe and Ikorodu) for 36 months from eko360. https://eko360.ng/search-dataset
- Boundaries are 37 polygons in the WGS84 coordinate system. https://raw.githubusercontent.com/iamspruce/intro-d3/main/data/nigeria_state_boundaries.geojson
- National population and urban share for 2023 to 2035  are from the United Nations World Population Prospects 2024, medium variant (United Nations, 2024). https://www.worldometers.info/world-population/nigeria-population/
- 
#Tools & Technologies
- Analyses were run in Python using pandas, NumPy, statsmodels, GeoPandas and Matplotlib.
#Methodology
- 1. Collect the data. Four sources were used: the state estimates, the Lagos monthly records, the state boundaries, and UN population data. Published studies supplied the figures used to check and calibrate them.
- 2. Clean and check. The data was screened for errors. One wrong entry (Olushosun, June 2023) was fixed, and a 50% drop in trips at one dumpsite (Solous) was flagged. Every state name was matched to the map.
- 3. Describe the states. I calculated waste per person, total waste, organic share, and density for each state and zone, and drew maps. I also tested whether states with more waste per person have a lower organic share.
- 4. Test forecasting methods on Lagos.
`Seven methods were tried, from “same as last month” to a straight-line trend.`
- Each one was tested like a practice exam: it forecast months it had not seen, and its guesses were compared with reality. This was repeated from seven starting points.
- The method with the smallest average error was the 12-month linear trend (6.4%).
- The 2025 and 2026 results are shown as three scenarios (low, central and high).
- Lagos receipts were compared with estimated waste generation to see what share reaches the dumpsites.
- 5. Project waste to 2035.
- Each state’s 2023 waste is multiplied by two growth factors: population growth and a rise in waste per person as cities grow.
- Three scenarios were run. In the low scenario waste per person stays flat. In the central scenario it rises moderately (calibrated to a World Bank projection). In the high scenario it rises as fast as the urban share.
- The organic share is lowered as waste per person rises, following the pattern across states.
- 6. Check the results. The calculations were done twice, in Python and in Excel, and gave the same answers. The state-level baseline was compared with World Bank figures, and a scaling factor shows how much the level would change.

`Main limitation: the baseline level is the weakest point, and every state is assumed to grow at the national rate.`
