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
            GeoDataFrame containing

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
