"""Period"""
from __future__ import annotations

from dataclasses import (
    dataclass,
    asdict
)
import datetime
from itertools import repeat
import logging
from typing import NamedTuple

import pandas as pd

from cygne.core.curblr import DAYS as CDAYS
from cygne.tools.ctime import Ctime
from cygne.core.utils import from_inventory_to_list_date

logger = logging.getLogger(__name__)

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

SCHOOL_PERIOD_1 = {
    'days': [0, 1, 2, 3, 4],
    'start_hour': datetime.time(7, 0),
    'end_hour': datetime.time(17, 0),
    'start_date': datetime.date(1970, 1, 1),
    'end_date': datetime.date(1970, 6, 30),
}

SCHOOL_PERIOD_2 = {
    'days': [0, 1, 2, 3, 4],
    'start_hour': datetime.time(7, 0),
    'end_hour': datetime.time(17, 0),
    'start_date': datetime.date(1970, 9, 1),
    'end_date': datetime.date(1970, 12, 31),
    }

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


def reverse_period(
    start_hour: datetime.time,
    end_hour: datetime.time,
    days: list[int],
    start_date: datetime.date,
    end_date: datetime.date
) -> list[Period]:
    """_summary_

    Parameters
    ----------
    start_hour : datetime.time
        _description_
    end_hour : datetime.time
        _description_
    days : list[int]
        _description_
    start_date : datetime.date
        _description_
    end_date : datetime.date
        _description_

    Returns
    -------
    list[Period]
        _description_
    """
    periods = []
    periods.extend([
        Period(
            start_hour=datetime.time(0, 0) if start_hour else None,
            end_hour=start_hour,
            days=[d for d in range(len(DAYS)) if d not in days],
            start_date=datetime.date(1970, 1, 1) if start_date else None,
            end_date=start_date
        ),
        Period(
            start_hour=end_hour,
            end_hour=datetime.time(23, 59) if end_hour else None,
            days=[d for d in range(len(DAYS)) if d not in days],
            start_date=end_date,
            end_date=datetime.date(1970, 12, 31) if end_date else None
        )
    ])

    if hash(periods[0]) == hash(periods[1]):
        return [periods[0]]

    return periods


@dataclass
class Period():
    """ Table representing the period of a regulation
    """
    start_hour: datetime.time
    end_hour: datetime.time
    days: list[int]
    start_date: datetime.date
    end_date: datetime.date

    @classmethod
    def from_inventory(cls, pan: NamedTuple) -> list[Period]:
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        periods = []
        is_except = pan.RegTmpExcept == 'oui'

        if (
            pd.isna(pan.RegTmpHeureDebut) or
            not pan.RegTmpHeureDebut
        ):
            start_hour = None
        else:
            start_hour = Ctime.from_string(
                time=pan.RegTmpHeureDebut,
                hour_format="HH:MM:SS"
            ).as_datetime()
        if (
            pd.isna(pan.RegTmpHeureFin) or
            not pan.RegTmpHeureFin
        ):
            end_hour = None
        else:
            end_hour = Ctime.from_string(
                time=pan.RegTmpHeureFin,
                hour_format="HH:MM:SS"
            ).as_datetime()
        if (
            pd.isna(pan.RegTmpJours) or
            not pan.RegTmpJours
        ):
            days = []
        else:
            days = parse_days(pan.RegTmpJours.replace(',', '-'))
        if (
            pd.isna(pan.panneau_mois) or
            not pan.panneau_mois
        ):
            months = []
        else:
            months = [*map(MONTHS_MAP.get, pan.panneau_mois.split(','))]
        if (
            pd.isna(pan.panneau_an_jour_debut) or
            not pan.panneau_an_jour_debut
        ):
            start_day_month = None
        else:
            start_day_month = int(pan.panneau_an_jour_debut)
        if (
            pd.isna(pan.panneau_an_jour_fin) or
            not pan.panneau_an_jour_fin
        ):
            end_day_month = None
        else:
            end_day_month = int(pan.panneau_an_jour_fin)

        if months and not (start_day_month or end_day_month):
            raise ValueError('Months refered without start/end.')
        if (start_day_month or end_day_month) and not months:
            raise ValueError('Start/End days refered without start/end.')

        months = sorted(months)
        dates_from, dates_to = from_inventory_to_list_date(
                start_day_month,
                end_day_month,
                months
            )
        if not dates_from:
            dates_from = [None]
            dates_to = [None]
        periods += list(map(Period,
                            repeat(start_hour),
                            repeat(end_hour),
                            repeat(days),
                            dates_from,
                            dates_to
                            ))

        if is_except:
            p = []
            for period in periods:
                p.extend(reverse_period(**period.to_dict()))
            periods = p

        # school periods
        if (
            pan.RegTmpEcole and
            not pd.isna(pan.RegTmpEcole)
        ):
            periods.append(
                Period(**SCHOOL_PERIOD_1)
            )
            periods.append(
                Period(**SCHOOL_PERIOD_2)
            )

        return periods

    @property
    def empty(self) -> bool:
        """Is empty ?

        Returns
        -------
        bool
        """
        return not (
            self.start_hour or
            self.end_hour or
            self.days or
            self.start_date or
            self.end_date
        )

    def _effective_dates(self):
        if (
            self.start_date is None or
            self.end_date is None
        ):
            return {}
        return {
            "effectiveDates": [{
                "from": self.start_date.strftime('%m-%d'),
                "to": self.end_date.strftime('%m-%d')
            }]
        }

    def _days_of_week(self):
        if self.days is None:
            return {}
        return {
            "daysOfWeek": {
                "days": [CDAYS[i] for i in self.days]
            }
        }

    def _times_of_day(self):
        if self.start_hour is None or self.end_hour is None:
            return {}
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
        if self.empty:
            return {}

        curb = {}
        curb.update(self._effective_dates())
        curb.update(self._days_of_week())
        curb.update(self._times_of_day())

        return curb

    def __eq__(self, other: Period) -> bool:
        return (
            self.start_hour == other.start_hour and
            self.end_hour == other.end_hour and
            self.days == other.days and
            self.start_date == other.start_date and
            self.end_date == other.end_date
        )

    def __hash__(self) -> int:
        return hash((
            self.start_hour,
            self.end_hour,
            tuple(self.days),
            self.start_date,
            self.end_date
        ))

    def to_dict(self):
        """ To dict
        """
        return asdict(self)

    def hour_empty(self):
        return not (self.start_hour and self.end_hour)

    def days_empty(self):
        return not self.days

    def dates_empty(self):
        return not (self.start_date and self.end_date)

    def can_merge(self, other: Period) -> bool:
        """ Period are compatible or not

        Parameters
        ----------
        key : str
            attribute
        other : Period
            other period

        Returns
        -------
        bool
        """

        # FIXME: need a proper check to see if we can merge
        # brains if fried toonigh
        return False

        if other.empty or self.empty:
            return True

        if self == other:
            return True

        if self.hour_empty():
            return True
        # can only merge fully specified period on dates
        if (
            self.start_hour and self.end_hour and self.days
        ):
            return (
                self.start_hour == other.start_hour and
                self.end_hour == other.end_hour and
                self.days == other.days
            ) or not (
                other.start_hour or
                other.end_hour or
                other.days
            )

        # can't merge if hour differ
        if not (
            self.start_hour != other.start_hour and
            self.end_hour != other.end_hour
        ):
            return False

        # can't merge if days differs
        if other.days != self.days:
            return False

        # we have already check if dates can merge,
        # only option is is one of them is null
        return (
            not (other.start_date and other.end_date) or
            not (self.start_date and self.end_date)
        )

        return True

    def update(self, other: Period) -> Period:
        """Update a period with information of another period. Information
        should not overlap.

        Parameters
        ----------
        other : Period
            Update with

        Returns
        -------
        Period
            Updated period
        """
        ot_dict = other.to_dict()
        if self.empty:
            for k, v in ot_dict.items():
                setattr(self, k, v)

        if self.can_merge(other):
            self_dict = asdict(self)
            for k, _ in self_dict.items():
                if k in ('start_date', 'end_date'):
                    try:
                        setattr(
                            self,
                            k,
                            self_dict[k].extend(ot_dict[k])
                        )
                    except AttributeError:
                        setattr(self, k, ot_dict[k])
                    continue
                # always replace if there is no conflict
                if ot_dict[k]:
                    setattr(self, k, ot_dict[k])
            return [self]

        return [other, self]


def period2curblr(periods: list[Period]) -> dict:
    """_summary_

    Parameters
    ----------
    periods : list[Period]
        _description_

    Returns
    -------
    dict
        _description_
    """
