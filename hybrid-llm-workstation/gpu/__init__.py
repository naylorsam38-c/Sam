"""GPU provider abstraction and implementations (spec section 7).

`gpu.provider_interface.base.GPUProvider` is the contract every cloud GPU
backend implements. `gpu.registry.get_provider()` resolves the configured
provider by name so the rest of the system never imports a provider module
directly.
"""
