---

# Geospatial County-Level Flood Prediction 

This project builds a county-level flash flood prediction model using NASA and NOAA datasets to support local emergency planning and risk mitigation.
We leveraged skills in **Python, data engineering, geospatial processing, and machine learning** as part of the **AI4ALL Ignite** program to create a scalable, data-driven alternative to costly physics-based flood models.

---

## Problem Statement

Among Florida counties, to what extent can environmental features such as rainfall, soil moisture, elevation, and slope be used to predict whether a flood event will occur on a given day?


---

## Key Results

1. **Integrated Multi-Source Dataset:**

   * Combined NASA GPM daily rainfall, SMAP soil moisture, SRTM terrain, and NOAA Storm Events data for Florida counties.
2. **Final Labeled Dataset:**

   * Created a county × date dataset with **flooded (1)** / **not flooded (0)** labels using NOAA storm events.
3. **Modeling Framework:**

   * Prepared for **Random Forest**, **XGBoost**, and **Logistic Regression** classification models.
4. **Temporal Training Split:**

   * Trained on **2015–2021** data, with **2022-2024** reserved for testing/prediction.

---

## Methodologies

* **Data Engineering & Aggregation**

  * Aggregated NASA satellite rasters and NOAA CSV data to the **county (GEOID)** level.
  * Merged rainfall, soil moisture, and elevation data with flood occurrence labels.
* **Exploratory Data Analysis (EDA)**

  * Conducted class distribution analysis, temporal drift checks, and feature distributions via histograms and KDE plots.
* **Machine Learning for Imbalanced Classification**

  * Designed workflows for **Random Forest**, **XGBoost**, and **Logistic Regression**.
  * Applied techniques like **class weighting** and **SMOTE** to address class imbalance.

---

## Data Sources

1. **NASA Shuttle Radar Topography Mission (SRTM)** – Elevation and slope
   [https://earthexplorer.usgs.gov/](https://earthexplorer.usgs.gov/)
2. **NASA Global Precipitation Measurement (GPM IMERG)** – Daily rainfall
   [https://disc.gsfc.nasa.gov/datasets/GPM\_3IMERGDF\_07/summary](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
3. **NASA Soil Moisture Active Passive (SMAP)** – Daily soil moisture
   [https://nsidc.org/data/data-access-tool/SPL3SMP\_E/versions/6](https://nsidc.org/data/data-access-tool/SPL3SMP_E/versions/6)
4. **NOAA Storm Events Database** – Flood occurrence ground truth
   [https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
5. **U.S. Census TIGER/Line Shapefiles (2024)** – County boundaries for spatial joins
   [https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/](https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/)

---

## Technologies Used

* **Python** (pandas, NumPy, matplotlib, seaborn)
* **scikit-learn** (RandomForestClassifier, SMOTE, evaluation metrics)
* **xgboost** (for gradient boosting models)
* **geopandas** & **rasterio** (for geospatial data processing)
* **Jupyter Notebook** (EDA and experimentation)

---

## Authors

*This project was completed in collaboration through AI4ALL Ignite:*

* **Kossi Sessou** ([GitHub](https://github.com/KossiSessou))
* **\[Team Member 2 Name]**
* **Xinshu Yi** ([GitHub](https://github.com/Yi66tech))
* **\[Team Member 4 Name]**

---
