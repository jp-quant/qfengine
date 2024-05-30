import pandas as pd
import pytz

from qfengine.system.rebalance.rebalance import Rebalance
from qfengine import settings




class EndOfMonthRebalance(Rebalance):
    """
    Generates a list of rebalance timestamps for pre- or post-market,
    for the final calendar day of the month between the starting and
    ending dates provided.
    All timestamps produced are set to EDT.
    Parameters
    ----------
    start_dt : `pd.Timestamp`
        The starting datetime of the rebalance range.
    end_dt : `pd.Timestamp`
        The ending datetime of the rebalance range.
    pre_market : `Boolean`, optional
        Whether to carry out the rebalance at market open/close on
        the final day of the month. Defaults to False, i.e at
        market close.
    """

    def __init__(
        self,
        start_dt,
        end_dt,
        **kwargs
    ):
        self.start_dt = start_dt
        self.end_dt = end_dt
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
        Utilise the Pandas date_range method to create the appropriate
        list of rebalance timestamps.
        Returns
        -------
        `List[pd.Timestamp]`
            The list of rebalance timestamps.
        """
        rebalance_dates = pd.date_range(
            start=self.start_dt,
            end=self.end_dt,
            freq='BM'
        )

        rebalance_times = [
            pd.Timestamp(
                "%s %s" % (date, self.market_time), tz=settings.TIMEZONE
            )
            for date in rebalance_dates
        ]
        return rebalance_times