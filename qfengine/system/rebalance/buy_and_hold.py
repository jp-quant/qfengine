from qfengine.system.rebalance.rebalance import Rebalance
from qfengine import settings
import pandas as pd



class BuyAndHoldRebalance(Rebalance):
    """
    Generates a single rebalance timestamp at the start date in
    order to create a single set of orders at the beginning of
    a backtest, with no further rebalances carried out.
    Parameters
    ----------
    start_dt : `pd.Timestamp`
        The starting datetime of the buy and hold rebalance.
    """

    def __init__(self, start_dt, end_dt=None, **kwargs):
        self.start_dt = start_dt
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
        rebalance_times = [
            pd.Timestamp(
                "%s %s" % (self.start_dt, self.market_time), tz=settings.TIMEZONE
            )
        ]

        return rebalance_times