from qfengine.portfolio.optimizer.optimizer import PortfolioOptimiser
from typing import List, Union, Dict
import pandas as pd

class FixedWeightPortfolioOptimiser(PortfolioOptimiser):
    """
    Produces a dictionary keyed by Asset with that utilises the weights
    provided directly. This simply 'passes through' the provided weights
    without modification.
    Parameters
    ----------
    data_handler : `DataHandler`, optional
        An optional DataHandler used to preserve interface across
        TargetWeightGenerators.
    """

    def __init__(
        self,
        data_handler=None,
        **kwargs
    ):
        self.data_handler = data_handler

    def __call__(self,
                 alpha_weights:Union[Dict, pd.Series],
                 risk_factors_matrix: pd.DataFrame = None,
                **kwargs
    ):
        """
        Produce the dictionary of target weight
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
        return dict(alpha_weights)