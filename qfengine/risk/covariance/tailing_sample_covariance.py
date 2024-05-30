from qfengine.risk.covariance.covariance import CovarianceMatrixRiskModel
import numpy as np
import pandas as pd

class TailingSampleCovarianceRiskModel(CovarianceMatrixRiskModel):

    def __init__(self,
                 universe,
                 data_handler,
                 tailing_time_delta:str,
                    **kwargs
    ):
        try:
            pd.Timedelta(tailing_time_delta)
        except:
            raise
            
        def _ret_filter(ret_df, time_delta = tailing_time_delta):
            return ret_df[
                      ret_df.index >= (
                                ret_df.index[-1] - pd.Timedelta(tailing_time_delta)
                                      )
                         ]
        
        super().__init__(universe = universe,
                         data_handler = data_handler,
                         ret_filter_op = _ret_filter,
                         **kwargs
                        )
        self.tailing_time_delta = tailing_time_delta

    def __repr__(self):
        return self.__class__.__name__ + "(%s)" %str(self.tailing_time_delta)

