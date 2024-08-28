""" Module to load an treat inventory
"""
from __future__ import annotations

from ast import literal_eval
from dataclasses import (
    dataclass,
    field,
)
from itertools import groupby
import logging
from warnings import catch_warnings

import pandas as pd
import geopandas as gpd
from shapely import to_geojson

from cygne.core import (
    Panel,
    Regulation
)
from cygne.core.curblr import (
    MANIFEST,
    CRS
)
from cygne.core.enum import (
    TrafficDir,
    SideOfStreet
)
from cygne.tranform.points_to_line import (
    create_segments,
    cut_linestring
)


logger = logging.getLogger(__name__)


Segment = dict[tuple[int, int],
               list[tuple[Regulation, list[tuple[float, float]], str]]]


def create_little_pans_from_df(little_pans: pd.DataFrame) -> list[Panel]:
    """_summary_

    Parameters
    ----------
    little_pans : pd.DataFrame
        _description_

    Returns
    -------
    list[Panel]
        _description_
    """

    little_pans_object = []

    # Assert data is a Dataframe
    if isinstance(little_pans, pd.Series):
        little_pans = little_pans.to_frame().T

    if not little_pans.empty:
        for this_little_pan in little_pans.itertuples():
            little_pan_o = Panel.from_inventory(
                this_little_pan
                )
            little_pans_object.append(little_pan_o)

    return little_pans_object


@dataclass
class Inventory():
    """Collection of panels
    """
    pans: dict[int, Panel] = field(default_factory=dict)

    def __post_init__(self):
        self._merge_pannels_after_inventory()
        self._drop_duplicates()

    def _merge_pannels_after_inventory(self):
        for panel_id, panels in self.pans.items():
            panel = panels[0]
            for other_pan in panels[1:]:
                panel.merge(other_pan)

            self.pans[panel_id] = panel

    def group_pannels_by_street_and_side(self):
        """ Group panels by street, side_of_street
        """
        curbs = {}
        for _, panel in self.pans.items():
            road_id = panel.location.street_id
            side_of_street = panel.location.side_of_street
            try:
                curbs[(road_id, side_of_street)].append(panel)
            except KeyError:
                curbs[(road_id, side_of_street)] = [panel]

        for id_curb, panels in curbs.items():
            curbs[id_curb] = sorted(
                panels,
                key=lambda x: x.location.linear_reference
            )

        return curbs

    def enrich_with_roadnetwork(self, roads: gpd.GeoDataFrame):
        """_summary_

        Parameters
        ----------
        roads : gpd.GeoDataFrame
            _description_

        Returns
        -------
        _type_
            _description_
        """
        roads.copy()
        roads = roads.set_index("ID_TRC")
        for id_pan, panel in self.pans.items():
            try:
                road = roads.loc[panel.location.street_id]
            except KeyError:
                logger.info(
                    "Wrong road id for panel %s, roads id does not exits : %s",
                    id_pan,
                    panel.location.street_id
                )
                road = roads.iloc[
                    roads.sindex.nearest(
                        panel.location.location,
                        return_all=False)[1][0]
                ]
                logger.info('Infered road id %s', road.name)
            panel.linear_reference_from_geom(road.geometry)
            panel.location.street_id = int(road.name)
            panel.location.traffic_dir = road.SENS_CIR
            panel.location.road_geometry = road.geometry
            panel.location.road_length = road.geometry.length

    def _drop_duplicates(self):
        panel_hash = []
        to_rm = []
        for pan_id, panel in self.pans.items():
            if hash(panel) in panel_hash:
                logger.info(
                    "Panel %s is duplicated. It will be removed",
                    pan_id
                )
                to_rm.append(pan_id)
            else:
                panel_hash.append(hash(panel))

        for pan_id in to_rm:
            self.pans.pop(pan_id)

    def _create_segment(self) -> Segment:
        curbs_reg = {}
        curbs = self.group_pannels_by_street_and_side()

        # for all panel on roads
        for road_id, panels in curbs.items():
            traffic_dir = panels[0].location.traffic_dir
            # for each regulation
            for regulation, panels_g in groupby(
                sorted(
                    panels,
                    key=lambda x: repr(x.regulation)
                ), lambda x: x.regulation
            ):

                # sort by linear_ref
                panels_g = sorted(
                    panels_g,
                    key=lambda x: x.location.linear_reference
                )

                points = [p.location.location for p in panels_g]
                linear_ref = [p.location.linear_reference for p in panels_g]
                chain = [p.arrow for p in panels_g]
                panel_id = [p.unique_id for p in panels_g]

                # handle reversed traffic direction from road digitalization
                if (
                    traffic_dir == TrafficDir.REVERSE_DIR or
                    (traffic_dir == TrafficDir.BOTH_DIR and
                     road_id[1] == SideOfStreet.LEFT)
                ):
                    points = list(reversed(points))
                    linear_ref = list(reversed(linear_ref))
                    chain = list(reversed(chain))
                    panel_id = list(reversed(panel_id))

                    linear_ref = [panels[0].location.road_length - lr
                                  for lr in linear_ref]

                segments = create_segments(points, linear_ref, chain)
                try:
                    curbs_reg[road_id].append([
                        regulation,
                        segments,
                        panel_id
                    ])
                except KeyError:
                    curbs_reg[road_id] = [[
                        regulation,
                        segments,
                        panel_id
                    ]]

        return curbs_reg

    def _create_lines_geom(self):
        segments = self._create_segment()

        for _, segments_break in segments.items():
            for arr in segments_break:
                breaks = arr[1]
                panels_id = arr[2]

                road_geom = self.pans[panels_id[0]].location.road_geometry
                traffic_dir = self.pans[panels_id[0]].location.traffic_dir
                side = self.pans[panels_id[0]].location.side_of_street

                if (
                    traffic_dir == TrafficDir.REVERSE_DIR or
                    (traffic_dir == TrafficDir.BOTH_DIR and
                     side == SideOfStreet.LEFT)
                ):
                    breaks = [[road_geom.length - x, road_geom.length - y]
                              for x, y in breaks]

                lines_geom = [cut_linestring(road_geom, x, y)
                              for x, y in breaks]
                arr.append(lines_geom)

        return segments

    def to_curblr(self):
        """ Convert the collection of signs to CurbLR
        """
        segments = self._create_lines_geom()
        curblr = {}
        features = []

        curblr["manifest"] = MANIFEST
        curblr["type"] = "FeatureCollection"
        curblr['crs'] = CRS
        curblr["features"] = features

        i = 0
        for segments_break in segments.values():
            for (regs, lr_breaks, panels_id, lines) in segments_break:
                regulations = []
                for reg in regs:
                    regulation = reg.to_curblr()
                    regulations.append(regulation)

                # usefull var on the street treated
                tf_dir = self.pans[panels_id[0]].location.traffic_dir
                side = self.pans[panels_id[0]].location.side_of_street
                road_length = self.pans[panels_id[0]].location.road_length

                for lr_break, line in zip(lr_breaks, lines):
                    pan_id = [
                        self.pans[p].unique_id
                        for p in panels_id
                        if (
                            lr_break[0] <=
                            self.pans[p].location.linear_reference <=
                            lr_break[-1]
                        )
                    ]
                    if (
                        tf_dir == TrafficDir.REVERSE_DIR or
                        (tf_dir == TrafficDir.BOTH_DIR and
                         side == SideOfStreet.LEFT)
                    ):
                        pan_id = [
                            self.pans[p].unique_id
                            for p in panels_id
                            if (
                                lr_break[0] <=
                                (road_length -
                                 self.pans[p].location.linear_reference) <=
                                lr_break[-1]
                            )
                        ]

                    # there is something weird
                    if not line:
                        logger.info(
                            "This sign %s make a regulation of 0 meters." +
                            " There must be an error. This regulation will" +
                            " not be incorporated into the CurbLR data.",
                            pan_id
                        )
                        continue

                    geometry = to_geojson(line)
                    location = self.pans[panels_id[0]].location.to_curblr()
                    location["objectId"] = i
                    location["shstLocationStart"] = lr_break[0]
                    location["shstLocationEnd"] = lr_break[-1]
                    if str(lr_break[-1]) == 'inf':
                        location["shstLocationEnd"] = road_length

                    location["derivedFrom"] = pan_id

                    this_feat = {
                        "type": "Feature",
                        "properties": {
                            "location": location,
                            "regulations": regulations,
                        },
                        "geometry": literal_eval(geometry)
                    }
                    features.append(this_feat)

                    i += 1

        curblr["manifest"]["priorityHierarchy"] = (
            list({
                rule['rule']['activity']
                for feat in curblr['features']
                for rule in feat['properties']['regulations']
            }) +
            list({
                rule['rule']['priorityCategory']
                for feat in curblr['features']
                for rule in feat['properties']['regulations']
            })
        )

        return curblr

    def test_chaining(self) -> list[str]:
        """ Test if there is some regulation that has several starts or
        several ends.

        Return
        ------
        list[str]
            Problematic panel id.
        """
        segments = self._create_segment()

        pb_panels = []
        for id_street, segments_break in segments.items():
            for arr in segments_break:
                panels_id = arr[2]
                chain = [self.pans[p_id].arrow for p_id in panels_id]

                state = -1
                for i, c in enumerate(chain):
                    if state == -1:
                        if c in [1, 2]:
                            state = 1   # open
                        else:
                            state = 0   # close
                    if state == 1:
                        if c == 1:
                            logger.warning(
                                'One panel was already open without being' +
                                ' closed on street: %s, for regulation: %s' +
                                ' and panel: %s',
                                id_street,
                                arr[0][0],
                                panels_id[i]
                            )
                            pb_panels.append(panels_id[i])
                        if c == 3:
                            state = 0
                    if state == 0:
                        if c == 3:
                            logger.warning(
                                "regulation was closed already. No opening" +
                                " for this regulation before closing it. On" +
                                " street: %s for regulation: %s and" +
                                " panel: %s.",
                                id_street,
                                arr[0][0],
                                panels_id[i]
                            )
                            pb_panels.append(panels_id[i])
                        if c in [1, 2]:
                            state = 1

        return pb_panels

    @classmethod
    def from_inventory(cls, data: pd.DataFrame):
        """ take a flat dataframe of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : pd.dataframe
            the flat inventory data
        """

        pans_store = {}

        # iter over poteau
        for _, poteau in data.groupby(['globalid']):
            little_pans = poteau[poteau.ObjetType == 'panonceau'].copy()
            pans = poteau[poteau.ObjetType != 'panonceau'].copy()

            if not little_pans.empty:
                little_pans = little_pans.set_index(['IdObjetRefExt'])

            # iter over signs
            for pan in pans.itertuples():
                logger.debug('Panel %s being proccessed', pan.globalid_panneau)
                try:
                    pan_object = Panel.from_inventory(pan)
                except ValueError as ve:
                    logger.warning(
                        "Panel %s is not formed as expected, please check." +
                        " Not processed",
                        pan.globalid_panneau
                    )
                    logger.error(ve)
                    continue

                # handle little pans
                try:
                    his_little_pans = little_pans.loc[pan.id_rp_panneau]
                except KeyError:
                    pass
                else:
                    little_pans_o = create_little_pans_from_df(
                        little_pans=his_little_pans
                    )
                    # apply each regulations of each little pan on this panel
                    for little_pan_o in little_pans_o:
                        for reg in little_pan_o.regulation:
                            with catch_warnings(record=True) as ws:
                                pan_object.extend_regulation(reg)
                                if ws:
                                    logger.warning(
                                        "Sign %s and little sign %s have " +
                                        "overlapping elements",
                                        pan_object.unique_id,
                                        little_pan_o.unique_id
                                    )
                                    for w in ws:
                                        logger.warning(w.message.args[0])

                try:
                    pans_store[pan.globalid_panneau].append(pan_object)
                except KeyError:
                    pans_store[pan.globalid_panneau] = [pan_object]

        collection = Inventory(pans_store)

        return collection
