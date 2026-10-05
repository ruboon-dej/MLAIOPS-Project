import os


def get_adapter():
    provider = os.environ.get("CLOUD_PROVIDER", "local")
    if provider == "local":
        from .local import LocalAdapter
        return LocalAdapter()
    elif provider == "gcp":
        from .gcp import GCPAdapter
        return GCPAdapter()
    else:
        raise ValueError(f"Unknown CLOUD_PROVIDER: {provider}")
