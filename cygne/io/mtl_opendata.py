""" This module provide function to read and preprocess some of the montreal's
open data portal datasets """
import urllib.request
import geopandas as gpd


def read_mtl_open_data(url: str, encoding: str = 'utf-8') -> gpd.GeoDataFrame:
    """_summary_

    Parameters
    ----------
    url : _type_
        _description_
    encoding : str, optional
        _description_, by default 'utf-8'

    Returns
    -------
    _type_
        _description_
    """
    req = urllib.request.Request(
        url=url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as req:
        lines = req.readlines()
    if not encoding:
        encoding = req.headers.get_content_charset()
    lines = [line.decode(encoding) for line in lines]
    data = gpd.read_file(''.join(lines))

    return data
