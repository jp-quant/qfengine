from qfengine.portfolio.optimizer.optimizer import PortfolioOptimiser
from typing import List, Union, Dict
import pandas as pd

class EqualWeightPortfolioOptimiser(PortfolioOptimiser):
    """
    Produces a dictionary keyed by Asset with (optionally) scaled
    equal weights. Without scaling this is normalised to ensure vector
    sums to unity. This overrides the weights provided in the initial_weights
    dictionary.
    Parameters
    ----------
    scale : `float`, optional
        An optional scale factor to adjust the weights by. Otherwise vector
        is set to sum to unity.
    data_handler : `DataHandler`, optional
        An optional DataHandler used to preserve interface across
        PortfolioOptimisers.
    """

    def __init__(
        self,
        data_handler=None,
        scale = 1.0,
        **kwargs

    ):
        self.scale = scale
        self.data_handler = data_handler

    def __call__(self,
                 alpha_weights:Union[Dict, pd.Series],
                 risk_factors_matrix: pd.DataFrame = None,
                **kwargs
    ):
        """
        Produce the dictionary of single fixed scalar target weight
        values for each of the Asset instances provided.
        Parameters
        ----------
        dt : `pd.Timestamp`
            The time 'now' used to obtain appropriate data for the
            target weights.
        initial_weights : `dict{str: float}`
            The initial weights prior to optimisation.
        Returns
        -------
        `dict{str: float}`
            The Asset symbol keyed scalar-valued target weights.
        """
        assets = dict(alpha_weights).keys()
        num_assets = len(assets)
        equal_weight = 1.0 / float(num_assets)
        scaled_equal_weight = self.scale * equal_weight
        return {asset: scaled_equal_weight for asset in assets}