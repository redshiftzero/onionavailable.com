import enum
import json
from markupsafe import escape
import requests
from urllib.parse import urlparse

from typing import Dict, Optional, Tuple


class OnionService(enum.Enum):
    """
    >>> OnionService.from_str("l5satjgud6gucryazcyvyvhuxhr74u6ygigiuyixe3a6ysis67ororad.onion")
    <OnionService.V3: 3>
    >>> OnionService.from_str("unlikelynamefora.onion")
    <OnionService.V2: 2>
    """
    V2 = 2
    V3 = 3

    @classmethod
    def from_str(
        cls, url: str
    ):
        url = urlparse(url)

        # Length of netloc includes .onion, so we have 62 chars for V3, 22 for V2
        V3_addr_len = 62
        V2_addr_len = 22

        # urlparse() apparently sometimes parses the onion URL to the netloc OR
        # the path attributes, so we look at both.
        url_without_subdomain = '.'.join(url.netloc.split('.')[-2:])
        if len(url_without_subdomain) == V3_addr_len or len(url.path) == V3_addr_len:
            return cls.V3
        elif len(url_without_subdomain) == V2_addr_len or len(url.path) == V2_addr_len:
            return cls.V2
        else:
            raise ValueError(f"invalid URL: {url.netloc}")


def has_onion_service(url: str) -> Tuple[bool, Optional[OnionService], str]:
    try:
        r = requests.get('http://' + url)
        onion_url = r.headers['Onion-Location']
        version = OnionService.from_str(onion_url)
        return True, version, onion_url
    except KeyError:
        return False, None, None


def update_sites() -> Dict:
    with open('watched.txt', 'r') as f:
        sites = f.read().splitlines()

    results = {}
    for site in sites:
        has_onion, version, onion_url = has_onion_service(site)
        results.update({site: {'has_onion': has_onion, 'version': version.value, 'onion_url': escape(onion_url)}})

    return results


if __name__ == "__main__":
    print(update_sites())
    with open('scan.json', 'w') as f:
        f.write(json.dumps(results))
