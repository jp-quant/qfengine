import datetime

import pandas as pd
from pandas.tseries.offsets import BDay
from qfengine import settings

from qfengine.simulation.simulation_engine import SimulationEngine
from qfengine.simulation.simulation_event import SimulationEvent


class DailyBusinessDaySimulationEngine(SimulationEngine):
    """
    A SimulationEngine subclass that generates events on a daily
    frequency defaulting to typical business days, that is
    Monday-Friday.
    In particular it does not take into account any specific
    regional holidays, such as Federal Holidays in the USA or
    Bank Holidays in the UK.
    It produces a pre-market event, a market open event,
    a market closing event and a post-market event for every day
    between the starting and ending dates.
    Parameters
    ----------
    starting_day : `pd.Timestamp`
        The starting day of the simulation.
    ending_day : `pd.Timestamp`
        The ending day of the simulation.
    pre_market : `Boolean`, optional
        Whether to include a pre-market event
    post_market : `Boolean`, optional
        Whether to include a post-market event
    """

    def __init__(self,
                 starting_day,
                 ending_day,
                 pre_market=True,
                 post_market=True,
                 **kwargs
    ):
        if ending_day < starting_day:
            raise ValueError(
                "Ending date time %s is earlier than starting date time %s. "
                "Cannot create DailyBusinessDaySimulationEngine "
                "instance." % (ending_day, starting_day)
            )

        self.starting_day = starting_day
        self.ending_day = ending_day
        self.pre_market = pre_market
        self.post_market = post_market
        self.business_days = self._generate_business_days()

    def _generate_business_days(self):
        """
        Generate the list of business days using midnight EDT as
        the timestamp.
        Returns
        -------
        `list[pd.Timestamp]`
            The business day range list.
        """
        days = pd.date_range(
            self.starting_day, self.ending_day, freq=BDay()
        )
        return days

    def __iter__(self):
        """
        Generate the daily timestamps and event information
        for pre-market, market open, market close and post-market.
        Yields
        ------
        `SimulationEvent`
            Market time simulation event to yield
        """
        for index, bday in enumerate(self.business_days):
            year = bday.year
            month = bday.month
            day = bday.day

            if self.pre_market:
                yield SimulationEvent(
                    pd.Timestamp(
                        datetime.datetime(year, month, day), tz=settings.TIMEZONE
                    ), event_type="pre_market"
                )

            yield SimulationEvent(
                pd.Timestamp(
                    datetime.datetime(year, month, day, 9, 30),
                    tz=settings.TIMEZONE
                ), event_type="market_open"
            )

            yield SimulationEvent(
                pd.Timestamp(
                    datetime.datetime(year, month, day, 16, 00),
                    tz=settings.TIMEZONE
                ), event_type="market_close"
            )

            if self.post_market:
                yield SimulationEvent(
                    pd.Timestamp(
                        datetime.datetime(year, month, day, 23, 59), tz=settings.TIMEZONE
                    ), event_type="post_market"
                )