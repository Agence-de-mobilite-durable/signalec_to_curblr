""" UserClass
"""
from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    asdict,
)
import logging
from typing import NamedTuple

import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class UserClass():
    """ Type of vehicule allowed in a regulation
    """
    is_except: bool
    category: list[str] = field(default=None)
    permit: list[int] = field(default=None)

    dict = asdict

    @classmethod
    def from_inventory(cls, pan: NamedTuple) -> list[UserClass]:
        """ take a NamedTuple instance of this scheme :
        https://dbdiagram.io/d/inventaire-lapi-664e2a63f84ecd1d22e246f8
        and populate the structure.

        parameters
        ----------
        data : NamedTuple
            the flat inventory data
        """
        is_except = pan.RegVehExcept == 'oui'
        if pd.isna(pan.RegVehType) or not pan.RegVehType:
            category = []
        else:
            category = pan.RegVehType.split(',')
        if pd.isna(pan.RegVehSRRR) or not pan.RegVehSRRR:
            permit = []
        else:
            permit = pan.RegVehSRRR.split(',')
            # is_except = pan.RegNature == 'interdiction'

        if permit == ['']:
            permit = []

        uc_list = [UserClass(
            is_except=is_except,
            category=category,
            permit=permit
        )]
        # handicap special case
        if pan.RegHandicap == 'oui':
            uc_list.append(
                UserClass(
                    is_except=True,
                    category=['handicap']
                )
            )

        return uc_list

    @property
    def empty(self) -> bool:
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
        if self.empty:
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

    def update(self, other: UserClass) -> UserClass | tuple[UserClass]:
        """Update a UserClass with information of another Userclass.

        Parameters
        ----------
        other : UserClass
            Update with

        Returns
        -------
        UserClass | tuple[UserClass]
            Updated userclass or a list of two userclass if they're not
            conciliable
        """
        if self.is_except == other.is_except:
            self.category.append(other.category)
            self.permit.append(other.permit)

            return self

        return self, other
