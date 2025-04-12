# ☀️ Solar Suitability Project — GIS Analysis for Solar Power Plant Site Selection

This project implements spatial analysis for **determining suitable areas for solar power plant installation** using **ArcGIS 10.8**, **ArcPy**, and **Spatial Analyst**.

The project is fully automated through the Python script `solar_suitability.py`. The script processes DEM, calculates slope, aspect, solar radiation, distance to roads, combines these factors into an evaluation model, and identifies the best sites.

---

## 📂 Project Structure

E:\solar_suitability_project
│
├── 📁 data\                          # Input data
│   ├── 🗂️ dem.tif                   # Digital Elevation Model (reprojected from WGS84 → Web Mercator)
│   │   └── 📝 EPSG:4326 → EPSG:3857  # Coordinate system transformation
│   └── 🗂️ roads.shp                 # Road network (EPSG:3857, metric system)
│
├── 📁 results\                       # Analysis results
│   ├── 🗂️ slope.tif                 # Slopes (degrees)
│   ├── 🗂️ aspect.tif                # Aspect (0-360°)
│   ├── 🗂️ solar.tif                 # Raw solar radiation (kWh/m²)
│   │
│   ├── 📁 scores\                    # Normalized indicators (1-5)
│   │   ├── 🗂️ solar_score.tif       # Solar radiation (5 - highest priority)
│   │   ├── 🗂️ slope_score.tif       # Slope (1 - gentle, 5 - steep)
│   │   ├── 🗂️ aspect_score.tif      # Aspect (5 - south, 1 - north)
│   │   └── 🗂️ distance_score.tif    # Distance to roads (5 - closest)
│   │
│   ├── 🗂️ suitability.tif           # Final score (Σ weighted indicators)
│   │   └── ⚖️ 0.4(solar) + 0.3(slope) + 0.2(aspect) + 0.1(distance)
│   │
│   └── 📁 output_zones\              # Final zones
│       ├── 🗂️ best_zones.tif        # Binary mask (≥4.5 points)
│       └── 🗂️ best_zones.shp        # Vectorized zones (area >2 ha)
│
├── 📁 scripts\
│   └── 🐍 solar_suitability.py       # Automated pipeline:
│       ├── 📌 DEM preprocessing
│       ├── 📌 Solar radiation calculation
│       └── 📌 GIS analysis by criteria
│
└── 📄 README.md                      # Documentation:
    ├── 🌍 Coordinate systems
    ├── ⚙️ Analysis parameters
    └── 📊 Results interpretation


---

## ⚙️ Requirements

- ArcMap 10.8 with **Spatial Analyst** license
- Python 2.7 (included with ArcMap)
- All input data projected to the same coordinate system (recommended: UTM Zone 36N)
- Working directory path set to `E:\solar_suitability_project` in the script

---

## 🧪 How to Run

1. Copy the repository/folder to drive `E:`
2. Add your input data to the `data/` folder:
   - `dem.tif` — Digital Elevation Model
   - `roads.shp` — Road network layer
3. Open `solar_suitability.py` in ArcGIS Python environment (ArcMap Python 2.7)
4. Modify paths in the **CONFIGURATION** section if needed
5. Run the script — it will automatically create all layers in the `results/` folder

---

## 📈 Methodology

### Suitability Criteria:
| Criterion      | Source            | Weight | Comment                        |
|----------------|-------------------|--------|--------------------------------|
| Slope          | DEM               | 30%    | <10° — ideal                  |
| Aspect         | DEM               | 20%    | South-facing slopes           |
| Solar Radiation| AreaSolarRadiation| 40%    | June-August                   |
| Distance to Roads| Roads layer     | 10%    | <500m — priority              |

### Combination:
Through `Raster Calculator` using the formula:
(slope_score * 0.3) + (aspect_score * 0.2) + (solar_score * 0.4) + (distance_score * 0.1)

### Final Zones:
- Selection of pixels with total score ≥ 4.5
- Conversion to polygons
- Selection of areas > 2 ha

---

## 🗺️ Output Results

All results are saved in `results/`:

- `suitability.tif` — overall suitability raster (1–5)
- `best_zones.tif` — binary mask of areas ≥4.5
- `selected_zones.shp` — best areas > 2 ha, ready for further analysis or mapping

---

## 🧩 Possible Extensions

- Masking forests, buildings, water bodies (using Extract by Mask)
- Generating hillshade or designer map
- Export to PDF / interactive web map
- Automation through ModelBuilder or Task Scheduler

---

## 📞 Feedback

This project was created for learning and demonstrating Spatial Analyst capabilities. If you have ideas or questions — contact the author or customize it for your needs 😉 
