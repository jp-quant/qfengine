from qfengine.risk.covariance.covariance import CovarianceMatrixRiskModel
import numpy as np
import pandas as pd

class SampleCovarianceRiskModel(CovarianceMatrixRiskModel):

    def __init__(self,
                 universe,
                 data_handler,
                    **kwargs
    ):
        super().__init__(universe = universe,
                         data_handler = data_handler,
                         **kwargs
                        )

