from qfengine.portfolio.optimizer.asset_allocation.asset_allocation import AssetAllocationOptimizer



class MeanVarianceOptimizer(AssetAllocationOptimizer):
    def __init__(self,
                **kwargs
    ): 
        super().__init__(
            optimizing_function = AssetAllocationOptimizer._mean_variance_optimizing_function,
            **kwargs
                        )

