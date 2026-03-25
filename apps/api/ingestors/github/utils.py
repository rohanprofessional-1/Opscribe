from urllib.parse import urlparse

def _get_auth_url(repo_url: str, access_token: str) -> str:
    """
    Constructs an authenticated GitHub URL using the provided installation token.
    GitHub App installation tokens require 'x-access-token' as the username.
    """
    if not access_token:
        return repo_url
    parsed = urlparse(repo_url)
    return parsed._replace(netloc=f"x-access-token:{access_token}@{parsed.netloc}").geturl()
