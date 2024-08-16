""" Module to load an treat inventory
"""
from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from enum import IntEnum
from itertools import count
from typing import NamedTuple

import pandas as pd
from shapely import Point

from signe.tools.ctime import Ctime


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


@dataclass
class Period():
    """ Table representing the period of a regulation
    """
    is_except: bool
    start_hour: datetime.time
    end_hour: datetime.time
    days: list[int]
    months: list[int]
    start_day_month: list[int]
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
        is_except = pan.RegTmpExcept
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
        start_day_month = pan.panneau_an_jour_debut
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
        is_except = pan.RegVehExcept
        if pd.isna(pan.RegVehType):
            category = []
        else:
            category = pan.RegVehType.split(',')
        if pd.isna(pan.RegVehSRRR):
            permit = []
        else:
            permit = pan.RegVehSRRR.split(',')

        return UserClass(
            is_except=is_except,
            category=category,
            permit=permit
        )

    def __eq__(self, other: UserClass):
        return (
            self.is_except == other.is_except and
            self.category == other.category and
            self.permit == other.permit
        )


@dataclass
class Rule():
    """ Rule
    """
    activity: Nature
    type: str
    prioriy: int
    max_stay: int

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

        type_ = pan.RegTypeImmo if not pd.isna(pan.RegTypeImmo) else None

        priority = (
            pan.ObjetPositionSeq if not
            pd.isna(pan.ObjetPositionSeq)
            else None
        )
        max_stay = pan.RegTmpDuree if not pd.isna(pan.RegTmpDuree) else None

        return Rule(
            activity=activity,
            type=type_,
            prioriy=priority,
            max_stay=max_stay
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
            not self.prioriy and
            not self.max_stay
        )

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
            self.prioriy == other.priority and
            self.max_stay == other.max_stay
        )


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
        if pan.RegHandicap:
            user_class.append(
                UserClass(
                    is_except=True,
                    category=['handicap']
                )
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


@dataclass
class Location():
    """ Support that panels are on
    """
    location: Point
    side_of_street: SideOfStreet
    street_id: int
    identifier: int = field(default_factory=count().__next__)


@dataclass
class Panel():
    """ Caracteristic of a parking panel
    """
    position: int
    arrow: Arrow
    regulation: Regulation
    location: Location
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
            street_id=pan.id_voie
        )

        _meta = {
            'nb_period': pan.panneau_nb_periodes
        }

        return Panel(
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


@dataclass
class PanCollection():
    """Collection of panels
    """
    pans: dict[int, Panel] = field(default_factory=dict)

    def _merge_pannels_after_inventory(self):
        for panel_id, panels in self.pans.items():
            panel = panels[0]
            for other_pan in panels[1:]:
                panel.merge(other_pan)

            self.pans[panel_id] = panel

    def sort_pannels_by_street_and_side(self):
        """ TODO
        """
        pass

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
        collection._merge_pannels_after_inventory()

        return collection
