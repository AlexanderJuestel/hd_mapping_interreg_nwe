"""
Contributors: Alexander Jüstel, Elias Khashfe, Eileen Herbst

"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
from itertools import product


def create_polygon_mask(gdf: gpd.GeoDataFrame,
                        stepsize: int,
                        crs: str = 'EPSG:3034'):
    """Creating a mask GeoDataFrame consisting of squares with a defined stepsize

    Parameters:
    ----------

        gdf: gpd.GeoDataFrame
            GeoDataFrame over which a mask is created

        stepsize: int
            Size of the rasterized squares in meters.

    Returns:
    --------

        gdf_mask: gpd.GeoDataFrame
            GeoDataFrame containing the masked polygons

    """

    # Creating arrays
    x = np.arange(gdf.total_bounds[0], gdf.total_bounds[2], stepsize)
    y = np.arange(gdf.total_bounds[1], gdf.total_bounds[3], stepsize)

    # Creating polygons
    polygons = [Polygon([(a, b), (a + stepsize, b), (a + stepsize, b + stepsize), (a, b + stepsize)]) for a, b in
                product(x, y)]

    # Converting polygons to GeoDataFrame
    gdf_mask = gpd.GeoDataFrame(geometry=polygons,
                                crs=crs)

    return gdf_mask


def data_intersect(data_intersected: gpd.GeoDataFrame,
                   mask_gdf: gpd.GeoDataFrame,
                   hd_column: str):
    """Assigning the HD of each cut polygon to the corresponding mask-polygons.

    Parameters:
    ----------

        data_intersected: gpd.GeoDataFrame
            GeoDataFrame containing the intersected heat demand polygons

        mask_gdf: gpd.GeoDataFrame
            GeoDataFrame containing the 100x100 m2 mask polygons

    Returns:
    --------
        gdf_HD: gpd.GeoDataFrame
            GeoDataFrame with 100x100 m2 cells containing the heat demand

    """

    # Performing left join on the GeoDataFrames
    leftjoin_gdf = gpd.sjoin(left_df=data_intersected,
                             right_df=mask_gdf,
                             how="left")

    # Calculating the heat demand
    gdf_grouped = (leftjoin_gdf.groupby('index_right')[hd_column].sum())

    # Concatenating cut polygons with mask polygons
    gdf_hd = pd.concat([gdf_grouped, mask_gdf], axis=1)

    # Reprojecting GeoDataFrame
    gdf_hd = gdf_hd.to_crs('EPSG:3034')

    # Filling NaNs
    gdf_hd.fillna(0, inplace=True)

    # Removing cells with no heat demand value
    gdf_hd = gdf_hd[gdf_hd[hd_column] != 0]

    # Dropping duplicate values
    gdf_hd = gdf_hd.drop_duplicates()

    # Resetting index
    gdf_hd = gdf_hd.reset_index().drop('index',
                                       axis=1)

    # Creating new column for heat demand in MWh
    gdf_hd['HD[MWh/ha]'] = gdf_hd[hd_column]/1000

    return gdf_hd


def create_polygon_masks(gdf: gpd.GeoDataFrame,
                         stepsize: int,
                         crs: str = 'EPSG:3034'):
    """Creating a list of mask GeoDataFrames consisting of squares with a defined stepsize

    Parameters:
    ----------

        gdf: gpd.GeoDataFrame
            GeoDataFrame containing several polygons from which masks are made

        stepsize: int
            Size of the rasterized squares in meters.

    Returns:
    --------

        masks: list
            List of GeoDataFrames containing the masks

    """

    # Resetting index
    gdf = gdf.reset_index()

    # Creating the list of masked GeoDataFrames
    masks = [create_polygon_mask(gdf=gdf.loc[gdf.index == i],
                                                 stepsize=stepsize) for i in range(len(gdf))]

    return masks


def overlay_input_data_with_mask(df1,
                                 df2):
    overlay = gpd.overlay(df1=df1,
                          df2=df2)

    return overlay


def overlay_input_data_with_masks(df1,
                                  list_df2):
    overlays = [overlay_input_data_with_mask(df1=df1,
                                             df2=df2) for df2 in list_df2]

    return overlays


def calculate_hd(mask_gdf: gpd.GeoDataFrame,
                 input_hd_gdf: gpd.GeoDataFrame,
                 hd_type: 'str'):

    if hd_type == 'res':
        average_hd = 'HD_res_m2'
    elif hd_type == 'com':
        average_hd = 'HD_com_m2'
    else:
        raise ValueError('Residential or commercial heat demand must be provided')

    # Creating 100m masks for each 10 km mask polygon
    masks = create_polygon_masks(gdf=mask_gdf,
                                 stepsize=100)

    # Overlaying input data with each 100x100 m mask
    masked_heat_demand = overlay_input_data_with_masks(df1=input_hd_gdf,
                                                       list_df2=masks)

    # Calculating HD and new geometry
    for masked_heat_demand_gdf in masked_heat_demand:
        masked_heat_demand_gdf['HD[MWh/ha]'] = masked_heat_demand_gdf[average_hd] * masked_heat_demand_gdf.area
        masked_heat_demand_gdf['geometry'] = masked_heat_demand_gdf.centroid

    # Calculating final HD with spatial join
    hd = [data_intersect(data_intersected=masked_heat_demand[i],
                                         mask_gdf=masks[i],
                                         hd_column='HD[MWh/ha]') for i in range(len(masked_heat_demand))]

    # Concatenating DataFrames
    hd = pd.concat(hd)

    return hd



