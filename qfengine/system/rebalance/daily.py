import pandas as pd
import pytz

from qfengine.system.rebalance.rebalance import Rebalance
from qfengine import settings



class DailyRebalance(Rebalance):
    """
    Generates a list of rebalance timestamps for pre- or post-market,
    for all business days (Monday-Friday) between two dates.
    Does not take into account holiday calendars.
    All timestamps produced are set to EDT.
    Parameters
    ----------
    start_date : `pd.Timestamp`
        The starting timestamp of the rebalance range.
    end_date : `pd.Timestamp`
        The ending timestamp of the rebalance range.
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
        self.market_time = self._set_market_time(**kwargs)
        self.rebalances = self._generate_rebalances(**kwargs)
    
    def output_rebalances(self):
        return self.rebalances

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
        rebalance_dates = pd.bdate_range(
            start=self.start_date, end=self.end_date,
        )

        rebalance_times = [
            pd.Timestamp(
                "%s %s" % (date, self.market_time), tz=settings.TIMEZONE
            )
            for date in rebalance_dates
        ]

        return rebalance_times