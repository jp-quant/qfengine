from abc import ABCMeta, abstractmethod
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DataHandler(object):

    __metaclass__ = ABCMeta
    