""" Rule
"""
from __future__ import annotations

from dataclasses import (
    dataclass,
    field
)
from copy import deepcopy
from typing import NamedTuple

import pandas as pd

from cygne.core.enum import Nature


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
    payement: bool = False
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

        type_ = pan.RegTypeImmo if not pd.isna(pan.RegTypeImmo) else None
        if type_ is None or type_ == 'stationnement':
            type_ = 'parking'
        if type_ == 'arrêt':
            type_ = 'standing'

        reason = type_
        if not pd.isna(pan.panneau_type):
            reason = pan.panneau_type

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

    @property
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

    def exempt(self) -> list[Rule]:
        """ Apply examption logic on rule
        """
        if self.activity == Nature.PERMISSION:
            other = deepcopy(self)
            other.max_stay = None
            other.payement = not self.payement if self.payement else False

            return [other, self]

        if self.activity == Nature.INTERDICTION:
            self.activity = Nature.PERMISSION

        return [self]

    def update(self, other: Rule) -> Rule:
        """_summary_

        Parameters
        ----------
        other : Rule
            _description_

        Returns
        -------
        Rule
            _description_
        """
        if self.is_empty:
            return other
        if other.is_empty:
            return self

        if (
            self.activity != other.activity or
            self.type != self.type
        ):
            raise ValueError(
                'Rules are different and cannot cohabit on the same sign.'
            )

        if other.max_stay and not self.max_stay:
            self.max_stay = other.max_stay

        return self

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
