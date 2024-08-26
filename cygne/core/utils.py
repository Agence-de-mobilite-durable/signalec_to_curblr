from datetime import date, timedelta
from itertools import groupby
from operator import itemgetter


def safe_end_of_month(month: int) -> date:
    """_summary_

    Parameters
    ----------
    month : int
        _description_

    Returns
    -------
    date
        _description_
    """
    # The day 28 exists in every month. 4 days later, it's always next month
    date_safe = date(1970, month, 28) + timedelta(days=4)
    # subtracting the number of the current day brings us back one month
    date_safe = date_safe - timedelta(days=date_safe.day)
    return date_safe


def from_inventory_to_list_date(
    start_day: int = 0,
    end_day: int = 31,
    months: list[int] = None
) -> list[date]:
    """_summary_

    Parameters
    ----------
    start_day : int, optional
        _description_, by default 0
    end_day : int, optional
        _description_, by default 31
    months : list[int], optional
        _description_, by default None

    Returns
    -------
    list[date]
        _description_
    """

    if not months:
        return [], []

    dates_from = []
    dates_to = []
    for k, g in groupby(enumerate(months), lambda i_x: i_x[0] - i_x[1]):
        consec_months = list(map(itemgetter(1), g))
        try:
            dates_from.append(date(
                1970,
                consec_months[0]+1,
                start_day
            ))
        except ValueError:
            dates_to.append(
                safe_end_of_month(consec_months[0] + 1)
            )

        try:
            dates_to.append(date(
                1970,
                consec_months[-1]+1,
                end_day
            ))
        except ValueError:
            dates_to.append(
                safe_end_of_month(consec_months[-1] + 1)
            )

    return dates_from, dates_to


