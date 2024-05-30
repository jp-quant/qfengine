from qfengine.portfolio.optimizer.asset_allocation.asset_allocation import AssetAllocationOptimizer



class MinimumVarianceOptimizer(AssetAllocationOptimizer):
    def __init__(self,
                **kwargs
    ): 
        super().__init__(
            optimizing_function = AssetAllocationOptimizer._volatility_optimizing_function,
            **kwargs
                        )

