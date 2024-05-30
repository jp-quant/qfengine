from qfengine.system.rebalance.buy_and_hold import BuyAndHoldRebalance
from qfengine.system.rebalance.daily import DailyRebalance
from qfengine.system.rebalance.end_of_month import EndOfMonthRebalance
from qfengine.system.rebalance.weekly import WeeklyRebalance
import pandas as pd
from qfengine import settings

class RebalanceHandler(object):

    def __init__(self,
                 rebalance:str,
                 start_dt = None,
                 end_dt = None,
                 **kwargs,
    ):
        if start_dt is None:
            if settings.PRINT_EVENTS:
                print("No specified rebalancing 'start_dt'. Defaulting rebalancing to today.")
            start_dt = pd.Timestamp(pd.Timestamp.now().date(), tz=settings.TIMEZONE)
        if end_dt is None:
            if settings.PRINT_EVENTS:
                print("No specified rebalancing 'end_dt'. Defaulting rebalancing to 1 year from 'start_dt'.")
            end_dt = (start_dt + pd.Timedelta('1y'))
        if rebalance == 'buy_and_hold':
            rebalancer = BuyAndHoldRebalance(
                start_dt, end_dt, **kwargs
            )
        elif rebalance == 'daily':
            rebalancer = DailyRebalance(
                start_dt, end_dt, **kwargs
            )
        elif rebalance == 'weekly':
            rebalancer = WeeklyRebalance(
                start_dt, end_dt, **kwargs
            )
        elif rebalance == 'end_of_month':
            rebalancer = EndOfMonthRebalance(
                start_dt, end_dt, **kwargs
            )
        else:
            raise ValueError(
                'Unknown rebalance frequency "%s" provided.' % rebalance
            )
        self.rebalancer = rebalancer
    
    def output_rebalances(self):
        return self.rebalancer.output_rebalances()
    