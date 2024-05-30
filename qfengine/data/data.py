from abc import ABCMeta, abstractmethod
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class TimeSeriesData(object):

    __metaclass__ = ABCMeta

    def __init__(self,
                 dt:pd.Timestamp,
    ):
        self.dt = dt
