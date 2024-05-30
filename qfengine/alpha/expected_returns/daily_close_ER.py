from qfengine.alpha.expected_returns.expected_returns_weights import ExpectedReturnsAlpha
import numpy as np
import pandas as pd



class DailyCloseExpectedReturnsAlpha(ExpectedReturnsAlpha):
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
            logarithmic_returns:bool = True,
            ret_filter_op = None,
                **kwargs
    ):
        super().__init__(universe = universe, data_handler = data_handler)
        self.logarithmic_returns = logarithmic_returns
        self.ret_filter_op = ret_filter_op

    def _closes_to_returns_df(self, closes_df:pd.DataFrame)->pd.DataFrame:
        return (
            np.log(closes_df/closes_df.shift(1)).dropna()
                        if self.logarithmic_returns else
                                    closes_df.pct_change().dropna()
                )
    
    def _get_universe_historical_daily_close_df(self, dt, **kwargs)->pd.DataFrame:
        return self.data_handler.get_assets_historical_closes(
                                                    self.universe.get_assets(dt),
                                                    end_dt = dt)
    
    def _filter_returns_df(self, returns_df:pd.DataFrame)->pd.DataFrame:
        if self.ret_filter_op:
            return self.ret_filter_op(returns_df)
        else:
            return returns_df

    def get_returns_df(self, dt, **kwargs):
        return self._filter_returns_df(
                        self._closes_to_returns_df(
                                self._get_universe_historical_daily_close_df(dt, **kwargs),
                                            **kwargs
                                            )
                                      )

    # TODO: Redesign architecture for forecasting implementations
    def calculate_assets_expected_returns(self, dt, **kwargs):
        ret_df = self.get_returns_df(dt, **kwargs)
        return dict(ret_df.mean())
        
