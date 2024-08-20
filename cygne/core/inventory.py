""" Module to load an treat inventory
"""
from __future__ import annotations

from ast import literal_eval
from dataclasses import dataclass, field
import datetime
from enum import IntEnum
import inspect
from itertools import groupby
import logging
from typing import NamedTuple

import pandas as pd
import geopandas as gpd
from shapely import (
    Point,
    LineString,
    to_geojson
)

from cygne.core.curblr import (
    MANIFEST,
    DAYS as CDAYS,
    CRS
)
from cygne.tools.ctime import Ctime
from cygne.tranform.points_to_line import (
    create_segments,
    cut_linestring
)


logger = logging.getLogger(__name__)


DAYS = ['lundi', 'mardi', 'mercredi', 'jeudi',
        'vendredi', 'samedi', 'dimanche']


def parse_days(day: str) -> list[int]:
    """
    Parse a days interval express by string to a list of intergers representing
    the day of week value with 0 = monday (lundi) and 6 = sunday (dimanche).

    Parameters
    ----------
    day : str
        A string containing one or more 3-letters day notations and zero or
        more operators to create intervals. Intervals of a single day are
        accepted.

        Accepted values for day notations are 'lun', 'mar', 'mer', 'jeu',
        'ven', 'sam', and 'dim'.

        Accepted values for operators are '-' (from to) and '+' (and).

    Return
    ------
    list_of_days : list of int
        int representation of the day interval.

    Example
    -------
    1. Joint interval of several days :
        >>> parse_days('lun-mer') ---> return [0, 1, 2]

    2. Interval of disjoint days :
        >>> parse_days('lun+mer') ---> return [0, 3]

    3. Interval of only one day :
        >>> parse_days('lun') ----> return [0]
    """
    if day == 'dim-sam':
        return list(range(0, 7))
    day = day.strip()
    if day in DAYS:
        return [DAYS.index(day)]

    if '-' in day:
        first = DAYS.index(day.split('-')[0].strip())
        last = DAYS.index(day.split('-')[-1].strip())

        return list(range(first, last+1))

    if '+' in day:
        return [DAYS.index(d.strip()) for d in day.split('+')]

    raise NotImplementedError


MONTHS_MAP = {
  "janvier": 0,
  "février": 1,
  "mars": 2,
  "avril": 3,
  "mai": 4,
  "juin": 5,
  "juillet": 6,
  "août": 7,
  "septembre": 8,
  "octobre": 9,
  "novembre": 10,
  "décembre": 11,
}


SCHOOL_PERIOD = {
    'days': [0, 1, 2, 3, 4],
    'start_hour': datetime.time(7, 0),
    'end_hour': datetime.time(17, 0),
    'months': [0, 1, 2, 3, 4, 5, 8, 9, 10, 11],
    'start_day_month': 1,
    'end_day_month': 31,
}


class Arrow(IntEnum):
    """ Euneration for Arrow
    """
    START = 1
    END = 3
    NO_ARROW = 2


class Nature(IntEnum):
    """ Euneration for Arrow
    """
    INTERDICTION = 0
    PERMISSION = 1


class SideOfStreet(IntEnum):
    """ Euneration for Arrow
    """
    RIGHT = 1
    LEFT = -1


class TrafficDir(IntEnum):
    """ Euneration for Arrow
    """
    DIGITALIZATION_DIR = 1
    REVERSE_DIR = -1
    BOTH_DIR = 0
    UNSET = -2


@dataclass
class Period():
    """ Table representing the period of a regulation
    """
    is_except: bool
    start_hour: datetime.time
    end_hour: datetime.time
    days: list[int]
    months: list[int]
    start_day_month: int
    end_day_month: int

    @classmethod
    def from_inventory(cls, pan: NamedTuple):
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        is_except = pan.RegTmpExcept == 'oui'
        if pan.RegTmpEcole:
            return Period(
                is_except=is_except,
                **SCHOOL_PERIOD
            )

        if pd.isna(pan.RegTmpHeureDebut):
            start_hour = None
        else:
            start_hour = Ctime.from_string(
                time=pan.RegTmpHeureDebut,
                hour_format="HH:MM:SS"
            ).as_datetime()
        if pd.isna(pan.RegTmpHeureFin):
            end_hour = None
        else:
            end_hour = Ctime.from_string(
                time=pan.RegTmpHeureFin,
                hour_format="HH:MM:SS"
            ).as_datetime()
        if pd.isna(pan.RegTmpJours):
            days = []
        else:
            days = parse_days(pan.RegTmpJours.replace(',', '-'))
        if pd.isna(pan.panneau_mois):
            months = []
        else:
            months = [*map(MONTHS_MAP.get, pan.panneau_mois.split(','))]
        if pd.isna(pan.panneau_an_jour_debut):
            start_day_month = None
        else:
            start_day_month = pan.panneau_an_jour_debut
        if pd.isna(pan.panneau_an_jour_fin):
            end_day_month = None
        else:
            end_day_month = pan.panneau_an_jour_fin

        return Period(
            is_except=is_except,
            start_hour=start_hour,
            end_hour=end_hour,
            days=days,
            months=months,
            start_day_month=start_day_month,
            end_day_month=end_day_month
        )

    @property
    def is_empty(self) -> bool:
        """Is empty ?

        Returns
        -------
        bool
        """
        return not (
            self.start_hour or
            self.end_hour or
            self.days or
            self.months or
            self.start_day_month or
            self.end_day_month
        )

    def _effective_dates(self):
        if (
            self.end_day_month is None or
            self.start_day_month is None or
            self.months is None
        ):
            return {}
        if self.is_except:
            return {
                "effectiveDates": [{
                        "from": f"{self.end_day_month}-{self.months[-1] + 1}",
                        "to": f"{self.start_day_month}-{self.months[0] + 1}"
                    }]
            }
        return {
            "effectiveDates": [{
                "from": f"{self.start_day_month}-{self.months[0] + 1}",
                "to": f"{self.end_day_month}-{self.months[-1] + 1}"
            }]
        }

    def _days_of_week(self):
        if self.days is None:
            return {}
        if self.is_except:
            return {
                "daysOfWeek": {
                    "days": [d for d in CDAYS if d not in
                             [CDAYS[i] for i in self.days]]
                }
            }
        return {
            "daysOfWeek": {
                "days": [CDAYS[i] for i in self.days]
            }
        }

    def _times_of_day(self):
        if self.start_hour is None or self.end_hour is None:
            return {}
        if self.is_except:
            return {
                "timesOfDay": [
                    {
                        "from": '00:00',
                        "to": self.start_hour.strftime('%H:%M')
                    },
                    {
                        "from": self.end_hour.strftime('%H:%M'),
                        "to": '23:59'
                    }
                ]
            }
        return {
            "timesOfDay": [{
                "from": self.start_hour.strftime('%H:%M'),
                "to": self.end_hour.strftime('%H:%M')
            }]
        }

    def to_curblr(self) -> dict:
        """ Convert Period to CurbLR dict

        Returns
        -------
        dict
            Curblr
        """
        if self.is_empty:
            return {}

        curb = {}
        curb.update(self._effective_dates())
        curb.update(self._days_of_week())
        curb.update(self._times_of_day())

        return curb

    def __eq__(self, other: Period) -> bool:
        return (
            self.is_except == other.is_except and
            self.start_hour == other.start_hour and
            self.end_hour == other.end_hour and
            self.days == other.days and
            self.months == other.months and
            self.start_day_month == other.start_day_month and
            self.end_day_month == other.end_day_month
        )

    def __hash__(self) -> int:
        return hash((
            self.is_except,
            self.start_hour,
            self.end_hour,
            tuple(self.days),
            tuple(self.months),
            self.start_day_month,
            self.end_day_month,
        ))


@dataclass
class UserClass():
    """ Type of vehicule allowed in a regulation
    """
    is_except: bool
    category: list[str] = field(default=None)
    permit: list[int] = field(default=None)

    @classmethod
    def from_inventory(cls, pan: NamedTuple):
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        is_except = pan.RegVehExcept == 'oui'
        if pd.isna(pan.RegVehType):
            category = []
        else:
            category = pan.RegVehType.split(',')
        if pd.isna(pan.RegVehSRRR):
            permit = []
        else:
            permit = pan.RegVehSRRR.split(',')
            is_except = pan.RegNature == 'interdiction'

        return UserClass(
            is_except=is_except,
            category=category,
            permit=permit
        )

    def is_empty(self) -> bool:
        """Is empty ?

        Returns
        -------
        bool
        """
        return not (
            self.category or self.permit
        )

    def to_curblr(self) -> dict:
        """ Export UserClass as CurbLR
        """
        if self.is_empty():
            return {}

        return {
            "classes": self.category,
            "subclasses": self.permit
        }

    def __eq__(self, other: UserClass):
        return (
            self.is_except == other.is_except and
            self.category == other.category and
            self.permit == other.permit
        )

    def __hash__(self) -> int:
        return hash((
            self.is_except,
            tuple(self.category),
            tuple(self.permit)
        ))


@dataclass
class Rule():
    """ Rule
    """
    activity: Nature
    type: str
    reason: str
    # This is the position of the panel on the support. It's not clear what
    # to do with this information. Maybe we'll remove it further down the line.
    priority: int
    max_stay: int
    _authority: dict = field(default_factory=dict)

    @classmethod
    def from_inventory(cls, pan: NamedTuple):
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        activity = Nature.INTERDICTION
        if pan.RegNature == 'permission':
            activity = Nature.PERMISSION
        if pd.isna(pan.RegNature):
            activity = -1
        reason = None
        if not pd.isna(pan.panneau_type):
            reason = pan.panneau_type

        type_ = pan.RegTypeImmo if not pd.isna(pan.RegTypeImmo) else None
        if type_ is None or type_ == 'stationnement':
            type_ = 'parking'
        if type_ == 'arrêt':
            type_ = 'standing'

        priority = (
            pan.ObjetPositionSeq if not
            pd.isna(pan.ObjetPositionSeq)
            else None
        )
        max_stay = pan.RegTmpDuree if not pd.isna(pan.RegTmpDuree) else None

        authority = {
            'name': pan.arrondissement
        }

        return Rule(
            activity=activity,
            type=type_,
            reason=reason,
            priority=priority,
            max_stay=max_stay,
            _authority=authority
        )

    def is_empty(self):
        """_summary_

        Returns
        -------
        _type_
            _description_
        """
        return (
            self.activity == -1 and
            not self.type and
            not self.reason and
            not self.priority and
            not self.max_stay
        )

    def to_curblr(self, reverse=False) -> dict[str, str]:
        """ Rule to CurbLR

        Returns
        -------
        dict[str, str]
            CurbLR of the rule
        """
        if not reverse:
            activity = "no " if not self.activity else ""
        else:
            activity = "no " if self.activity else ""
        activity += self.type
        priority_category = self.reason if self.reason else activity

        curblr = {
            "activity": activity,
            "priorityCategory": priority_category,
        }

        if self.max_stay:
            curblr["maxStay"] = self.max_stay

        if self._authority:
            curblr["authority"] = self._authority

        return curblr

    def __eq__(self, other: Rule) -> bool:
        if self.is_empty or other.is_empty:
            return True

        return (
            (
                self.activity == other.activity or
                other.activity == -1 or
                self.activity == -1
            ) and
            self.type == other.type and
            self.reason == other.reason and
            self.priority == other.priority and
            self.max_stay == other.max_stay
        )

    def __hash__(self) -> int:
        return hash((self.activity, self.type, self.priority, self.max_stay))


@dataclass
class Regulation():
    """ Regulation class
    """
    rule: Rule
    user_class: list[UserClass] = field(default_factory=list)
    period: list[Period] = field(default_factory=list)
    _other_text: str = field(default="")

    @classmethod
    def from_inventory(cls, pan: NamedTuple):
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        rule = Rule.from_inventory(pan)
        user_class = [UserClass.from_inventory(pan)]
        period = [Period.from_inventory(pan)]
        other_text = pan.AutreTexte

        # handicap special case
        if pan.RegHandicap == 'oui':
            user_class.append(
                UserClass(
                    is_except=True,
                    category=['handicap']
                )
            )

        # all userclass should be the same except value
        except_uc = [uc.is_except for uc in user_class]
        if sum(except_uc) > 0 and sum(except_uc) < len(except_uc):
            raise ValueError(
                'All userclass should either be expect=True or except=False'
            )

        return Regulation(
            rule=rule,
            user_class=user_class,
            period=period,
            _other_text=other_text
        )

    def __eq__(self, other: Regulation) -> bool:
        return (
            self.rule == other.rule and
            self.user_class == other.user_class and
            self.period == other.period
        )

    def __hash__(self) -> int:
        return hash((
            self.rule,
            tuple(self.user_class),
            tuple(self.period),
            self._other_text
        ))

    def update(self, other: Regulation) -> None:
        """_summary_

        Parameters
        ----------
        other : Regulation
            _description_

        Raises
        ------
        ValueError
            _description_
        """
        if self.rule != other.rule:
            raise ValueError('There cannot be two rules on one panel.')

        if self == other:
            raise RuntimeWarning('Trying to merge two of the same regulation.')

        if self.period != other.period:
            self.period.extend(other.period)

        if self.user_class != other.user_class:
            self.user_class.extend(other.user_class)

    def to_curblr(self) -> dict:
        """ Create a CurbLR representation of the Regulation

        Return
        ------
        dict
            CurbLR representation of the regulation
        """

        curblr = {}
        user_class_exception = any(uc.is_except for uc in self.user_class)
        curblr['rule'] = self.rule.to_curblr(reverse=user_class_exception)
        curblr['userClasses'] = [uc.to_curblr() for uc in self.user_class]
        if not curblr['userClasses']:
            curblr.pop('userClasses')
        curblr['timeSpans'] = [p.to_curblr() for p in self.period]

        return curblr


def get_class_name():
    """Get previous class caller name"""
    prev_frame = inspect.currentframe().f_back
    try:
        class_name = prev_frame.f_locals['self'].__class__.__name__
    except KeyError:
        class_name = None

    return class_name


@dataclass
class Location():
    """ Support that panels are on
    """
    location: Point
    side_of_street: SideOfStreet
    street_id: int
    asset_type: str = None
    _linear_reference: float = field(init=False, default=-1)
    _traffic_dir: int = field(init=False, default=TrafficDir.UNSET)
    _road_geom: LineString = field(init=False, default=None)
    _road_length: float = field(init=False, default=-1)

    def __eq__(self, other):
        return (
            self.location == other.location and
            self.side_of_street == other.side_of_street and
            self.street_id == other.street_id
        )

    def __hash__(self) -> int:
        return hash((self.location, self.side_of_street, self.street_id))

    def to_curblr(self) -> dict[str, object]:
        """Convert Location to CurbLR

        Returns
        -------
        dict[str, object]
        """
        return {
            "shstRefId": self.street_id,
            "shstLocationStart": -1,
            "shstLocationEnd": -1,
            "sideOfStreet": self.side_of_street.name.lower(),
            "objectId": -1,
            "derivedFrom": [],
            "assetType": self.asset_type
        }

    @property
    def linear_reference(self):
        """Return the Linear reference of this location

        Returns
        -------
        float
        """
        return self._linear_reference

    @linear_reference.setter
    def linear_reference(self, lr: float):
        self._linear_reference = lr

    @property
    def traffic_dir(self):
        """ Return the traffic dir on the street of the location

        Returns
        -------
        int
        """
        return self._traffic_dir

    @traffic_dir.setter
    def traffic_dir(self, direction: TrafficDir):
        self._traffic_dir = direction

    @property
    def road_geometry(self):
        """ Return the road geometry of the street of the location

        Returns
        -------
        int
        """
        return self._road_geom

    @road_geometry.setter
    def road_geometry(self, geometry: LineString):
        self._road_geom = geometry

    @property
    def road_length(self):
        """ Return the traffic dir on the street of the location

        Returns
        -------
        int
        """
        return self._road_length

    @road_length.setter
    def road_length(self, length: float):
        self._road_length = length


@dataclass
class Panel():
    """ Caracteristic of a parking panel
    """
    __name__ = 'sign'
    position: int
    arrow: Arrow
    regulation: Regulation
    location: Location
    unique_id: str
    _meta: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_inventory(cls, pan: NamedTuple):
        """ Take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        unique_id = pan.globalid_panneau
        position = pan.ObjetPositionSeq
        arrow = Arrow.NO_ARROW
        if pan.RegFleche == 'vers rue':
            arrow = Arrow.START
        elif pan.RegFleche == 'vers trottoir':
            arrow = Arrow.END

        side_of_street = SideOfStreet.LEFT
        if pan.cote_rue_id % 10 == 1:
            side_of_street = SideOfStreet.RIGHT

        regulation = Regulation.from_inventory(pan)

        location = Location(
            location=pan.geometry,
            side_of_street=side_of_street,
            street_id=-1 if pd.isna(pan.IdTroncon) else int(pan.IdTroncon),
            asset_type=cls.__class__.__name__
        )

        _meta = {
            'nb_period': pan.panneau_nb_periodes
        }

        return Panel(
            unique_id=unique_id,
            position=position,
            arrow=arrow,
            regulation=regulation,
            location=location,
            _meta=_meta
        )

    def extend_regulation(self, reg: Regulation) -> None:
        """_summary_

        Parameters
        ----------
        reg : Regulation
            _description_
        """
        self.regulation.update(reg)

    def merge(self, other: Panel) -> None:
        """_summary_

        Parameters
        ----------
        other : Panel
            _description_
        """
        self.regulation.update(other.regulation)

    def linear_reference_from_geom(self, geometry: LineString):
        """ Create the linear reference of the panel on a
        geometry

        Parameters
        ----------
        geometry : LineString
            Road to compute the linear reference on.
        """
        lr = geometry.project(self.location.location)
        self.location.linear_reference = lr

    def __eq__(self, other):
        return (
            self.position == other.position and
            self.arrow == other.arrow and
            self.location == other.location and
            self.regulation == other.regulation
        )

    def __key(self):
        return (self.position, self.arrow, self.location, self.regulation)

    def __hash__(self):
        return hash(self.__key())


Segment = dict[tuple[int, int],
               list[tuple[Regulation, list[tuple[float, float]], str]]]


@dataclass
class PanCollection():
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
            for (reg, lr_breaks, panels_id, lines) in segments_break:
                regulation = reg.to_curblr()

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
                        location["shstLocationEnd"] = line.length

                    location["derivedFrom"] = pan_id

                    this_feat = {
                        "type": "Feature",
                        "properties": {
                            "location": location,
                            "regulations": regulation,
                        },
                        "geometry": literal_eval(geometry)
                    }
                    features.append(this_feat)

                    i += 1

        return curblr

    def test_start(self):
        """TODO
        """

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
        for _, poteau in data.groupby(['globalid']):
            little_pans = poteau[poteau.ObjetType == 'panonceau'].copy()
            pans = poteau[poteau.ObjetType != 'panonceau'].copy()

            if not little_pans.empty:
                little_pans = little_pans.set_index(['IdObjetRefExt'])

            for pan in pans.itertuples():
                pan_object = Panel.from_inventory(pan)

                # handle little pans
                try:
                    this_little_pans = little_pans.loc[pan.id_rp_panneau]
                    if isinstance(this_little_pans, pd.Series):
                        this_little_pans = this_little_pans.to_frame().T
                    if not this_little_pans.empty:
                        for this_little_pan in this_little_pans.itertuples():
                            little_pan_o = Panel.from_inventory(
                                this_little_pan
                                )
                            pan_object.extend_regulation(
                                little_pan_o.regulation
                            )
                except KeyError:
                    pass

                try:
                    pans_store[pan.globalid_panneau].append(pan_object)
                except KeyError:
                    pans_store[pan.globalid_panneau] = [pan_object]

        collection = PanCollection(pans_store)

        return collection
