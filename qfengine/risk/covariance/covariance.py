from qfengine.risk.risk_model import RiskModel
from abc import ABCMeta
import numpy as np
import pandas as pd


class CovarianceMatrixRiskModel(RiskModel):

    __metaclass__ = ABCMeta

    def __init__(self,
                 universe,
                 data_handler,
                    logarithmic_returns:bool = True,
                    ret_filter_op = None,
                    ret_std_op = None,
                    ret_corr_op = None,
                        **kwargs
    ):
        self.universe = universe
        self.data_handler = data_handler
        self.logarithmic_returns = logarithmic_returns
        
        self.ret_filter_op = ret_filter_op
        self.ret_std_op = ret_std_op
        self.ret_corr_op = ret_corr_op


    #---| Computing Returns TimeSeries Data
    def _closes_to_returns_df(self, closes_df:pd.DataFrame, **kwargs)->pd.DataFrame:
        return (
            np.log(closes_df/closes_df.shift(1)).dropna()
                        if self.logarithmic_returns else
                                    closes_df.pct_change().dropna()
                )
    
    def _get_universe_historical_daily_close_df(self, dt, **kwargs)->pd.DataFrame:
        return self.data_handler.get_assets_historical_closes(
                                                    self.universe.get_assets(dt),
                                                    end_dt = dt)
    
    def _filter_returns_df(self, returns_df:pd.DataFrame, **kwargs)->pd.DataFrame:
        if self.ret_filter_op:
            return self.ret_filter_op(returns_df)
        else:
            return returns_df

    def get_returns_df(self, dt, **kwargs):
        return self._filter_returns_df(
                        self._closes_to_returns_df(
                                closes_df = self._get_universe_historical_daily_close_df(dt, **kwargs),
                                            **kwargs
                                            )
                                      )

    #---| Computing Covariance Matrix
    def _returns_volatility(self, ret):
        if self.ret_std_op is not None:
            assert callable(self.ret_std_op)
            std = self.ret_std_op(ret)
            assert len(std) == ret.shape[1]
            assert set(std.index).issubset(set(ret.columns))
            return std
        else:
            return ret.std()

    def _returns_correlation(self, ret):
        if self.ret_corr_op is not None:
            assert callable(self.ret_corr_op)
            corr = self.ret_corr_op(ret)
            assert corr.shape[0] == corr.shape[1] == ret.shape[1]
            assert set(corr.index).issubset(set(ret.columns))
            assert set(corr.columns).issubset(set(ret.columns))
            return corr
        else:
            return ret.corr()
    
    def _is_symmetric(self, matrix:pd.DataFrame, rtol=1e-05, atol=1e-08):
        return matrix.shape[0] == matrix.shape[1]


        # Covariance = VOL' * CORR * VOL 
    def _compute_covariance_matrix(self, std:pd.Series, corr:pd.DataFrame):
        assert self._is_symmetric(corr)
        assert set(std.index).issubset(set(corr.index))
        assert set(corr.columns).issubset(set(corr.index))
        vol = std.copy().reindex(corr.columns).dropna()
        assert len(vol) == len(std), str([i for i in corr.columns if i not in vol.index])
        vol = np.diag(vol)
        return pd.DataFrame(
                        data = (np.dot(vol,np.dot(corr,vol))),
                        index = corr.index,
                        columns = corr.columns
                        )

    def calculate_returns_covariance_matrix(self, ret):
        std = self._returns_volatility(ret)
        corr = self._returns_correlation(ret)
        return self._compute_covariance_matrix(std = std, corr = corr)


    #---| __call__()
    def __call__(self, dt, **kwargs):
        ret_df = self.get_returns_df(dt, **kwargs)
        return self.calculate_returns_covariance_matrix(ret_df)
    

    
