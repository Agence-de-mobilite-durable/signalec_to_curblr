""" Panel
"""
from __future__ import annotations

from dataclasses import (
    dataclass,
    field
)
from itertools import groupby
from typing import NamedTuple

import pandas as pd
from shapely import LineString

from cygne.core import (
    Regulation,
    Location,
)
from cygne.core.enum import (
    Arrow,
    SideOfStreet
)


@dataclass
class Panel():
    """ Caracteristic of a parking panel
    """
    __name__ = 'sign'
    position: int
    arrow: Arrow
    regulation: list[Regulation]
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

    def extend_period(self, reg: Regulation) -> None:
        """_summary_

        Parameters
        ----------
        reg : Regulation
            _description_
        """
        if not all(p.empty for p in reg.periods):
            for regulation in self.regulation:
                # no period in the parent regulation
                if not regulation.periods:
                    regulation.periods = reg.periods
                    continue
                # else merge every period with little pan periods
                for period in regulation.periods:
                    for additional_period in reg.periods:
                        new_p = []
                        new_p.extend(period.update(additional_period))
                        regulation.periods = new_p

    def extend_userclass(self, reg: Regulation) -> None:
        """_summary_

        Parameters
        ----------
        reg : Regulation
            _description_
        """
        if not all(uc.empty for uc in reg.user_class):
            for regulation in self.regulation:
                if reg.user_class[0].is_except:
                    new_rules = regulation.rule.exempt()
                    # new regulation needs to be added
                    if len(new_rules) == 2:
                        self.regulation.append(
                            Regulation(
                                rule=new_rules[0],
                                user_class=reg.user_class,
                                periods=regulation.periods,
                                _other_text=reg._other_text
                            )
                        )
                        break
                else:
                    regulation.user_class.extend(reg.user_class)

    def extend_regulation(self, reg: Regulation) -> None:
        """_summary_

        Parameters
        ----------
        reg : Regulation
            _description_
        """
        self.extend_period(reg)
        self.extend_userclass(reg)

    def self_merge(self):
        """ If two rules are the same on the same panel, merge user class
        property and timestamp for this rule.

        """
        if len(self.regulation) > 1:
            self.regulation = sorted(self.regulation, lambda x: hash(x.rule))
            new_regs = []
            for rule, regulations in groupby(self.regulation):
                periods = [reg.periods for reg in regulations]
                userclass = [reg.user_class for reg in regulations]
                other_text = list({reg._other_text for reg in regulations})
                # flatten periods
                periods = [
                    x
                    for xs in periods
                    for x in xs
                ]
                # flatten userclass
                userclass = [
                    x
                    for xs in userclass
                    for x in xs
                ]
                new_regs.append(Regulation(
                    rule=rule,
                    periods=[regulations],
                    user_class=userclass,
                    _other_text=" ; ".join(other_text)
                ))
            self.regulation = new_regs

    def merge(self, other: Panel) -> None:
        """_summary_

        Parameters
        ----------
        other : Panel
            _description_
        """
        self.self_merge()
        other.self_merge()
        hash_other = [hash(reg.rule) for reg in other.regulation]
        for reg in sorted(self.regulation, key=lambda x: hash(x.rule)):
            for ot_reg in sorted(other.regulation, key=lambda x: hash(x.rule)):
                try:
                    reg.merge(ot_reg)
                except ValueError:
                    continue
                else:
                    hash_other.remove(hash(ot_reg.rule))

        for ot_reg in other.regulation:
            if hash(ot_reg.rule) in hash_other:
                self.regulation.append(ot_reg)

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
        return (self.position, self.arrow,
                self.location, tuple(self.regulation))

    def __hash__(self):
        return hash(self.__key())
