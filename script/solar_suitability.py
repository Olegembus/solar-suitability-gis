# -*- coding: utf-8 -*-

import arcpy
from arcpy import env
from arcpy.sa import *
import os
import sys
import datetime
import numpy as np

def setup_environment(workspace_path):
    """Setup ArcGIS environment and check extensions"""
    print("Setting up environment...")
    
    # Check if workspace exists
    if not os.path.exists(workspace_path):
        raise ValueError(f"Workspace path does not exist: {workspace_path}")
    
    # Setup ArcGIS environment
    env.workspace = workspace_path
    env.overwriteOutput = True
    
    # Check Spatial Analyst extension
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        raise RuntimeError("Spatial Analyst license is not available")
    
    # Create necessary directories
    for directory in ['results', 'results/scores', 'results/output_zones']:
        dir_path = os.path.join(workspace_path, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

def check_input_data(dem_path, roads_path, mask_path=None):
    """Validate input data and their projections"""
    print("Checking input data...")
    
    # Check if input files exist
    if not arcpy.Exists(dem_path):
        raise ValueError(f"DEM file not found: {dem_path}")
    if not arcpy.Exists(roads_path):
        raise ValueError(f"Roads file not found: {roads_path}")
    
    # Get spatial references
    dem_sr = arcpy.Describe(dem_path).spatialReference
    roads_sr = arcpy.Describe(roads_path).spatialReference
    
    # Check if projections match
    if dem_sr.name != roads_sr.name:
        print(f"Warning: Different projections detected!")
        print(f"DEM: {dem_sr.name}")
        print(f"Roads: {roads_sr.name}")
    
    # Check mask if provided
    if mask_path and not arcpy.Exists(mask_path):
        raise ValueError(f"Mask file not found: {mask_path}")

def calculate_slope(dem_path, output_dir):
    """Calculate and reclassify slope"""
    print("Processing slope...")
    
    # Calculate slope
    slope = Slope(dem_path, "DEGREE")
    slope.save(os.path.join(output_dir, "slope.tif"))
    
    # Reclassify slope
    remap = RemapRange([
        [0, 5, 5],    # 0-5° = 5 (ideal)
        [5, 10, 4],   # 5-10° = 4
        [10, 15, 3],  # 10-15° = 3
        [15, 20, 2],  # 15-20° = 2
        [20, 90, 1]   # >20° = 1 (unsuitable)
    ])
    slope_reclass = Reclassify(slope, "VALUE", remap)
    slope_reclass.save(os.path.join(output_dir, "scores", "slope_score.tif"))
    return slope_reclass

def calculate_aspect(dem_path, output_dir):
    """Calculate and reclassify aspect"""
    print("Processing aspect...")
    
    # Calculate aspect
    aspect = Aspect(dem_path)
    aspect.save(os.path.join(output_dir, "aspect.tif"))
    
    # Reclassify aspect (maximum score for south-facing slopes)
    remap = RemapRange([
        [0, 45, 2],      # N-NE = 2
        [45, 135, 4],    # E-SE = 4
        [135, 225, 5],   # SE-SW = 5 (ideal)
        [225, 315, 4],   # SW-NW = 4
        [315, 360, 2],   # NW-N = 2
        [-1, 0, 3]       # Flat = 3
    ])
    aspect_reclass = Reclassify(aspect, "VALUE", remap)
    aspect_reclass.save(os.path.join(output_dir, "scores", "aspect_score.tif"))
    return aspect_reclass

def calculate_solar_radiation(dem_path, output_dir, latitude=48.5):
    """Calculate and normalize solar radiation using quantile breaks"""
    print("Processing solar radiation...")
    
    # Calculate solar radiation for summer months
    solar = AreaSolarRadiation(
        dem_path,
        latitude=latitude,
        sky_size=200,
        time_configuration="MultiDays 2020",
        start_date="2020-06-01",
        end_date="2020-08-31",
        day_interval=14,
        hour_interval=2
    )
    solar.save(os.path.join(output_dir, "solar.tif"))
    
    # Convert to array for quantile calculation
    solar_array = arcpy.RasterToNumPyArray(solar)
    valid_values = solar_array[solar_array > 0]  # Exclude NoData values
    
    # Calculate quantile breaks
    quantiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    breaks = [np.percentile(valid_values, q * 100) for q in quantiles]
    
    # Reclassify using quantile breaks
    remap = RemapRange([
        [breaks[0], breaks[1], 1],  # Bottom 20% = 1
        [breaks[1], breaks[2], 2],  # 20-40% = 2
        [breaks[2], breaks[3], 3],  # 40-60% = 3
        [breaks[3], breaks[4], 4],  # 60-80% = 4
        [breaks[4], breaks[5], 5]   # Top 20% = 5
    ])
    
    solar_reclass = Reclassify(solar, "VALUE", remap)
    solar_reclass.save(os.path.join(output_dir, "scores", "solar_score.tif"))
    return solar_reclass

def calculate_distance_to_roads(roads_path, dem_path, output_dir):
    """Calculate and reclassify distance to roads"""
    print("Processing distance to roads...")
    
    # Calculate Euclidean distance
    cell_size = arcpy.Describe(dem_path).meanCellHeight
    distance = EucDistance(roads_path, cell_size=cell_size)
    distance.save(os.path.join(output_dir, "distance_to_roads.tif"))
    
    # Reclassify distance
    remap = RemapRange([
        [0, 500, 5],        # 0-500m = 5 (ideal)
        [500, 1000, 4],     # 500-1000m = 4
        [1000, 2000, 3],    # 1-2km = 3
        [2000, 3000, 2],    # 2-3km = 2
        [3000, 100000, 1]   # >3km = 1 (unsuitable)
    ])
    distance_reclass = Reclassify(distance, "VALUE", remap)
    distance_reclass.save(os.path.join(output_dir, "scores", "distance_score.tif"))
    return distance_reclass

def calculate_suitability(slope_score, aspect_score, solar_score, distance_score, 
                         output_dir, mask_path=None):
    """Calculate final suitability score"""
    print("Calculating final suitability...")
    
    # Calculate weighted sum
    suitability = (0.3 * slope_score + 
                  0.2 * aspect_score + 
                  0.4 * solar_score + 
                  0.1 * distance_score)
    
    # Apply mask if provided
    if mask_path:
        suitability = ExtractByMask(suitability, mask_path)
    
    suitability.save(os.path.join(output_dir, "suitability.tif"))
    return suitability

def extract_best_zones(suitability, output_dir, min_area_ha=2):
    """Extract and process best suitable zones"""
    print("Extracting best zones...")
    
    # Select areas with score >= 4.5
    best_zones = Con(suitability >= 4.5, 1)
    best_zones.save(os.path.join(output_dir, "output_zones", "best_zones.tif"))
    
    # Convert to polygons
    best_zones_poly = os.path.join(output_dir, "output_zones", "best_zones.shp")
    arcpy.RasterToPolygon_conversion(best_zones, best_zones_poly, "NO_SIMPLIFY")
    
    # Add and calculate area field
    arcpy.AddField_management(best_zones_poly, "Area_Ha", "DOUBLE")
    arcpy.CalculateField_management(best_zones_poly, "Area_Ha", 
                                  "!shape.area@hectares!", "PYTHON")
    
    # Select areas larger than minimum area
    arcpy.MakeFeatureLayer_management(best_zones_poly, "zones_lyr")
    arcpy.SelectLayerByAttribute_management("zones_lyr", "NEW_SELECTION", 
                                          f"Area_Ha >= {min_area_ha}")
    
    final_zones = os.path.join(output_dir, "output_zones", "selected_zones.shp")
    arcpy.CopyFeatures_management("zones_lyr", final_zones)
    
    return final_zones

def create_hillshade_map(dem_path, final_zones, output_dir):
    """Create hillshade and final map document"""
    print("Creating hillshade and final map...")
    
    # Calculate hillshade
    hillshade = Hillshade(dem_path, azimuth=315, altitude=45)
    hillshade.save(os.path.join(output_dir, "hillshade.tif"))
    
    # Create new map document
    mxd = arcpy.mapping.MapDocument("NEW")
    df = arcpy.mapping.ListDataFrames(mxd)[0]
    
    # Add layers
    layers_to_add = [
        ("Hillshade", os.path.join(output_dir, "hillshade.tif")),
        ("Suitability", os.path.join(output_dir, "suitability.tif")),
        ("Best Zones", final_zones)
    ]
    
    for name, path in layers_to_add:
        layer = arcpy.mapping.Layer(path)
        layer.name = name
        arcpy.mapping.AddLayer(df, layer)
    
    # Save map document and export to PDF
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    mxd.saveACopy(os.path.join(output_dir, f"solar_suitability_{timestamp}.mxd"))
    arcpy.mapping.ExportToPDF(mxd, os.path.join(output_dir, 
                             f"solar_suitability_{timestamp}.pdf"))
    del mxd

def main():
    try:
        # Configuration
        workspace = r"E:\solar_suitability_project"
        dem_path = os.path.join(workspace, "data", "dem.tif")
        roads_path = os.path.join(workspace, "data", "roads.shp")
        output_dir = os.path.join(workspace, "results")
        mask_path = None  # Optional: path to exclusion mask
        
        # Setup and validation
        setup_environment(workspace)
        check_input_data(dem_path, roads_path, mask_path)
        
        # Calculate all criteria
        slope_score = calculate_slope(dem_path, output_dir)
        aspect_score = calculate_aspect(dem_path, output_dir)
        solar_score = calculate_solar_radiation(dem_path, output_dir)
        distance_score = calculate_distance_to_roads(roads_path, dem_path, output_dir)
        
        # Calculate suitability and extract zones
        suitability = calculate_suitability(
            slope_score, aspect_score, solar_score, distance_score,
            output_dir, mask_path
        )
        final_zones = extract_best_zones(suitability, output_dir)
        
        # Create final map
        create_hillshade_map(dem_path, final_zones, output_dir)
        
        print("✅ Analysis completed successfully!")
        
    except arcpy.ExecuteError:
        print("ArcGIS error occurred:")
        print(arcpy.GetMessages(2))
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        arcpy.CheckInExtension("Spatial")

if __name__ == "__main__":
    main()