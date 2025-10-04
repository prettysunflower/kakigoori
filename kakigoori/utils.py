import os


def get_env_boolean(key: str, default: str = "false") -> bool:
    return bool(os.getenv(key, default).lower() in ("yes", "y", "1", "true"))


def get_env_or_raise(env_var):
    var = os.getenv(env_var)
    if var is None:
        raise EnvironmentError(f"Environment variable {env_var} not set")
    return var
