""" Process inventory data
"""
import logging

import geopandas as gpd
from cygne.core.inventory import PanCollection
from cygne.io.mtl_opendata import read_mtl_open_data

logger = logging.getLogger(__name__)


def main():
    """ Main
    """

    logger.info('Query data')
    inventaire = gpd.read_file(
        './data/inventaire/inventaire_lapi_20240808.geojson'
    )
    support = gpd.read_file(
        './data/inventaire/rp_support_20240809.geojson'
    )
    panneau = gpd.read_file(
        './data/inventaire/rp_panneau_20240809.geojson'
    )
    period = gpd.read_file(
        './data/inventaire/rp_panneau_periode_20240809.geojson'
    )
    geobase = read_mtl_open_data(
        'https://data.montreal.ca/dataset/' +
        '984f7a68-ab34-4092-9204-4bdfcca767c5/' +
        'resource/9d3d60d8-4e7f-493e-8d6a-dcd040319d8d/download/geobase.json'
    )
    geobase = geobase.to_crs('epsg:32188')
    support = support.to_crs('epsg:32188')

    df = inventaire.join(
        support.set_index('parentglobalid'),
        on='globalid',
        lsuffix='_inventaire',
        how='right'
    ).join(
        panneau.set_index('parentglobalid'),
        on='globalid',
        rsuffix='_panneau',
        how='right'
    ).join(
        period.set_index('parentglobalid'),
        on='globalid_panneau',
        rsuffix='_period',
        how='left'
    )

    logger.info("Create panels collection")
    panc = PanCollection.from_inventory(df)
    logger.info("Enrich panels location with geobase info")
    panc.enrich_with_roadnetwork(geobase)
    logger.info("Group panels with street and side")
    curbs = panc.group_pannels_by_street_and_side()
    segs = panc._create_lines()
    logger.info([p.location.linear_reference for p in curbs[1240182, 1]])
    logger.info('finish ?')


if __name__ == '__main__':
    main()