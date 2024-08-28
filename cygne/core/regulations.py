""" Regulation
"""
from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
import inspect
from itertools import repeat
import logging
from typing import NamedTuple

from cygne.core import (
    Rule,
    UserClass,
    Period
)
from cygne.core.periods import period2curblr

logger = logging.getLogger(__name__)


@dataclass
class Regulation():
    """ Regulation class
    """
    rule: Rule
    user_class: list[UserClass] = field(default_factory=list)
    periods: list[Period] = field(default_factory=list)
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
        user_class = UserClass.from_inventory(pan)
        period = Period.from_inventory(pan)
        other_text = pan.AutreTexte

        # all userclass should be the same except value
        except_uc = [uc.is_except for uc in user_class]
        if sum(except_uc) > 0 and sum(except_uc) < len(except_uc):
            raise ValueError(
                'All userclass should either be expect=True or except=False'
            )

        if except_uc[0]:
            rules = rule.exempt()
            return list(map(
                Regulation,
                rules,
                repeat(user_class),
                repeat(period),
                repeat(other_text)
            ))

        return [Regulation(
            rule=rule,
            user_class=user_class,
            periods=period,
            _other_text=other_text
        )]

    def __eq__(self, other: Regulation) -> bool:
        return (
            self.rule == other.rule and
            self.user_class == other.user_class and
            self.periods == other.periods
        )

    def __hash__(self) -> int:
        return hash((
            self.rule,
            tuple(self.user_class),
            tuple(self.periods),
            self._other_text
        ))

    def merge(self, other: Regulation) -> None:
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

        if self.periods != other.periods:
            # should precise each period already computed.
            self.periods.extend(other.periods)

        if self.user_class != other.user_class:
            self.user_class.extend(other.user_class)

    def clean_periods(self) -> None:
        """ Clean the representation of periods.
        """

    # def update(self, other: Regulation) -> None:
    #     """_summary_

    #     Parameters
    #     ----------
    #     other : Regulation
    #         _description_

    #     Raises
    #     ------
    #     ValueError
    #         _description_
    #     """
    #     if self == other:
    #         raise RuntimeWarning(
    #             'Trying to update two of the same regulation.'
    #         )

    #     new_periods = []
    #     for other_period in other.periods:
    #         for period in self.periods:
    #             new_periods.extend(period.update(other_period))

    #     new_periods = list(set(new_periods))
    #     self.periods = new_periods

    #     for other_uc in other.user_class:
    #         for uc in self.user_class:
    #             ucu = uc.update(other_uc)
    #             if isinstance(ucu, tuple):
    #                 self.user_class.append(other_uc)
    #                 break
        # if self.user_class != other.user_class:
        #     self.user_class.extend(other.user_class)

    def to_curblr(self) -> dict:
        """ Create a CurbLR representation of the Regulation

        Return
        ------
        dict
            CurbLR representation of the regulation
        """

        curblr = {}
        # user_class_exception = any(uc.is_except for uc in self.user_class)
        curblr['rule'] = self.rule.to_curblr()  # reverse=user_class_exception)
        if not all(uc.empty for uc in self.user_class):
            curblr['userClasses'] = [uc.to_curblr() for uc in self.user_class]
        if not all(p.empty for p in self.periods):
            curblr['timeSpans'] = period2curblr(self.periods)

        return curblr


def get_class_name():
    """Get previous class caller name"""
    prev_frame = inspect.currentframe().f_back
    try:
        class_name = prev_frame.f_locals['self'].__class__.__name__
    except KeyError:
        class_name = None

    return class_name
