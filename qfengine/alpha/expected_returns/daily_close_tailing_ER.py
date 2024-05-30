from qfengine.alpha.expected_returns.daily_close_ER import DailyCloseExpectedReturnsAlpha
import numpy as np
import pandas as pd



class DailyCloseTailingExpectedReturnsAlpha(DailyCloseExpectedReturnsAlpha):
    """
    AlphaModel that returns weights of all assets in given universe, base on their
    daily close returns calculated from historical price data grabbed from data_handler given.
    Parameters
    ----------
    signal_weights : `dict{str: float}`
        The signal weights per asset symbol.
    universe : `Universe`, optional
        The Assets to make signal forecasts for.
    data_handler : `DataHandler`, optional
        An optional DataHandler used to preserve interface across AlphaModels.
    """

    def __init__(
        self,
        universe,
        data_handler,
        tailing_time_delta:str,
            logarithmic_returns:bool = True,
                **kwargs
    ):
        try:
            pd.Timedelta(tailing_time_delta)
        except:
            raise
            
        def _ret_filter(ret_df, time_delta = tailing_time_delta):
            start_dt = ret_df.index[-1] - pd.Timedelta(tailing_time_delta)
            return ret_df[ret_df.index >= start_dt]
        
        super().__init__(universe = universe,
                         data_handler = data_handler,
                         logarithmic_returns = logarithmic_returns,
                         ret_filter_op = _ret_filter
                         )
        self.tailing_time_delta = tailing_time_delta
        
    def __repr__(self):
        return self.__class__.__name__ + "(%s)" %str(self.tailing_time_delta)

        
