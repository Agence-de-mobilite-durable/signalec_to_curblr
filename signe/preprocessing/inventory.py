""" Process inventory data
"""
import geopandas as gpd
from signe.core.inventory import PanCollection


def main():

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

    panc = PanCollection.from_inventory(df)
    print('finish ?')


if __name__ == '__main__':
    main()