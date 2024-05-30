import pandas as pd
import numpy as np
import logging
from qfengine.data.price.backtest_price_handler import BacktestPriceHandler
from qfengine import settings

logger = logging.getLogger(__name__)


class BacktestDataHandler(BacktestPriceHandler):

    def __init__(
                self,
                price_data_sources:list,
                universe = None,
                    **kwargs


    ):
        super().__init__(universe = universe,
                         price_data_sources = price_data_sources,
                         **kwargs
                         )

    
    def copy(self):
        handler = BacktestPriceHandler(
            universe = self.universe,
            price_data_sources = [d.create_price_source_copy() for d in self.price_data_sources],
                preload_bid_ask_data = False,
                                 )
        handler._assets_bid_ask_frames = self._assets_bid_ask_frames.copy()
        # TODO: Add more renewals once more types of data sources are available
        return handler
    