import pandas as pd
import pytz

from qfengine.system.rebalance.rebalance import Rebalance
from qfengine import settings


class WeeklyRebalance(Rebalance):
    """
    Generates a list of rebalance timestamps for pre- or post-market,
    for a particular trading day of the week between the starting and
    ending dates provided.
    All timestamps produced are set to EDT.
    Parameters
    ----------
    start_date : `pd.Timestamp`
        The starting timestamp of the rebalance range.
    end_date : `pd.Timestamp`
        The ending timestamp of the rebalance range.
    weekday : `str`
        The three-letter string representation of the weekday
        to rebalance on once per week.
    pre_market : `Boolean`, optional
        Whether to carry out the rebalance at market open/close.
    """

    def __init__(
        self,
        start_dt,
        end_dt,
        **kwargs
    ):
        self.start_date = start_dt
        self.end_date = end_dt
        self.weekday = self._set_weekday(**kwargs)
        self.pre_market_time = self._set_market_time(**kwargs)
        self.rebalances = self._generate_rebalances(**kwargs)

    def output_rebalances(self):
        return self.rebalances

    def _set_weekday(self, **kwargs):
        """
        Checks that the weekday string corresponds to
        a business weekday.
        Parameters
        ----------
        weekday : `str`
            The three-letter string representation of the weekday
            to rebalance on once per week.
        Returns
        -------
        `str`
            The uppercase three-letter string representation of the
            weekday to rebalance on once per week.
        """
        weekday = None
        for wd in ['weekday','rebalance_weekday']:
            try:
                weekday = kwargs['weekday']
                break
            except:
                pass
        weekdays = ("MON", "TUE", "WED", "THU", "FRI")
        if weekday.upper() not in weekdays:
            raise ValueError(
                "Provided weekday keyword '%s' is not recognised "
                "or not a valid weekday. Enter one of ('MON', 'TUE', 'WED', 'THU', 'FRI')." % weekday
            )
        else:
            return weekday.upper()

    def _set_market_time(self, **kwargs):
        """
        Determines whether to use market open or market close
        as the rebalance time.
        Parameters
        ----------
        pre_market : `Boolean`
            Whether to use market open or market close
            as the rebalance time.
        Returns
        -------
        `str`
            The string representation of the market time.
        """
        pre_market = False if 'pre_market' not in kwargs else kwargs['pre_market']
        return "9:30:00" if pre_market else "16:00:00"

    def _generate_rebalances(self, **kwargs):
        """
        Output the rebalance timestamp list.
        Returns
        -------
        `list[pd.Timestamp]`
            The list of rebalance timestamps.
        """
        rebalance_dates = pd.date_range(
            start=self.start_date,
            end=self.end_date,
            freq='W-%s' % self.weekday
        )

        rebalance_times = [
            pd.Timestamp(
                "%s %s" % (date, self.pre_market_time), tz=settings.TIMEZONE
            )
            for date in rebalance_dates
        ]

        return rebalance_times
