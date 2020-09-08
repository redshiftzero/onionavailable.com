from datetime import datetime
import enum
import json
from pshtt.pshtt import inspect_domains
from pshtt.utils import format_domains
from markupsafe import escape
from urllib.parse import urlparse

from typing import Dict, List, Optional, Tuple

SENTINEL = "<!--- CUT -->"


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
    def from_str(cls, url: str):
        url = urlparse(url)

        # Length of netloc includes .onion, so we have 62 chars for V3, 22 for V2
        V3_addr_len = 62
        V2_addr_len = 22

        # urlparse() apparently sometimes parses the onion URL to the netloc OR
        # the path attributes, so we look at both.
        if "www" in url.netloc.split(".")[0]:
            url_without_www = ".".join(url.netloc.split(".")[1:])
        else:
            url_without_www = url.netloc
        if len(url_without_www) == V3_addr_len or len(url.path) == V3_addr_len:
            return cls.V3
        elif len(url_without_www) == V2_addr_len or len(url.path) == V2_addr_len:
            return cls.V2
        else:
            raise ValueError(f"invalid URL: {url.netloc}")


def is_onion_available(pshtt_results) -> Tuple[bool, Optional[str]]:
    """
    For HTTPS sites, we inspect the headers to see if the
    Onion-Location header is present, indicating that the
    site is available as an onion service.
    """
    onion_available = False
    onion_url = None

    for key in ["https", "httpswww"]:
        try:
            headers = pshtt_results["endpoints"][key]["headers"]
            if 'onion-location' in set(k.lower() for k in headers):
                onion_available = True
                onion_url = headers['onion-location']
        except KeyError:
            pass

    return onion_available, onion_url


def has_onion_service(url: str) -> Tuple[Optional[bool], Optional[OnionService], str]:
    try:
        domains = format_domains([url])
        pshtt_results = inspect_domains(domains, {})
        # inspect_domains returns a generator, so we convert to list and access
        # the first element.
        _, onion_url = is_onion_available(list(pshtt_results)[0])
        version = OnionService.from_str(onion_url)
        return True, version, onion_url
    except KeyError:
        return False, None, None
    except Exception as e:
        # Unexpected exceptions we just print the exception for later inspection
        # (if we raise other sites will fail to scan) and return that the site is unscannable.
        print(e)
        return None, None, None


def update_sites(sites: List[str]) -> Dict:
    results = {}
    for site in sites:
        has_onion, version, onion_url = has_onion_service(site)
        results.update(
            {
                site: {
                    "has_onion": has_onion,
                    "version": getattr(version, "value", None),
                    "onion_url": escape(onion_url),
                }
            }
        )

    # Sort results by version/status (v3 at top, then v2, then no onion or unknown status),
    # then alphabetical order.
    results = dict(
        sorted(
            results.items(),
            key=lambda x: (
                float("inf") if x[1]["version"] is None else -1 * x[1]["version"],
                x[0].lower(),
            ),
        )
    )

    return results


def regenerate_site(scan_data: Dict) -> None:
    """Regenerate static site based on latest scan"""
    V3_ONION = '<li class="list-group-item list-group-item-success">③ &nbsp;&nbsp;'
    V2_ONION = '<li class="list-group-item list-group-item-warning">② &nbsp;&nbsp;'
    SVG_NO_ONION = '<svg width="1em" height="1em" viewBox="0 0 16 16" class="bi bi-x" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M11.854 4.146a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708-.708l7-7a.5.5 0 0 1 .708 0z"/><path fill-rule="evenodd" d="M4.146 4.146a.5.5 0 0 0 0 .708l7 7a.5.5 0 0 0 .708-.708l-7-7a.5.5 0 0 0-.708 0z"/></svg>'
    NO_ONION = '<li class="list-group-item list-group-item-danger">{}&nbsp;&nbsp;'.format(SVG_NO_ONION)
    SVG_NO_DATA = '<svg width="1em" height="1em" viewBox="0 0 16 16" class="bi bi-cloud-slash" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M3.112 5.112a3.125 3.125 0 0 0-.17.613C1.266 6.095 0 7.555 0 9.318 0 11.366 1.708 13 3.781 13H11l-1-1H3.781C2.231 12 1 10.785 1 9.318c0-1.365 1.064-2.513 2.46-2.666l.446-.05v-.447c0-.075.006-.152.018-.231l-.812-.812zm2.55-1.45l-.725-.725A5.512 5.512 0 0 1 8 2c2.69 0 4.923 2 5.166 4.579C14.758 6.804 16 8.137 16 9.773a3.2 3.2 0 0 1-1.516 2.711l-.733-.733C14.498 11.378 15 10.626 15 9.773c0-1.216-1.02-2.228-2.313-2.228h-.5v-.5C12.188 4.825 10.328 3 8 3c-.875 0-1.678.26-2.339.661zm7.984 10.692l-12-12 .708-.708 12 12-.707.707z"/></svg>'
    NO_DATA = '<li class="list-group-item list-group-item-secondary"> {}&nbsp;&nbsp;'.format(SVG_NO_DATA)
    TERMINATOR = '</li>'

    with open("docs/index.html", "r") as f:
        site_before = f.read()

    prefix, _, postfix = site_before.split(SENTINEL)
    site_after = prefix + "\n" + SENTINEL + "\n"

    for site_netloc, site_data in scan_data.items():
        site_link = f'<a href="http://{site_netloc}/">{site_netloc}</a>'
        if site_data["has_onion"] and site_data["version"] == 3:
            site_after += V3_ONION + site_link + TERMINATOR + "\n"
        elif site_data["has_onion"] and site_data["version"] == 2:
            site_after += V2_ONION + site_link + TERMINATOR + "\n"
        elif site_data["has_onion"] is False:
            site_after += NO_ONION + site_link + TERMINATOR + "\n"
        else:
            site_after += NO_DATA + site_link + TERMINATOR + "\n"

    now = datetime.now()
    last_updated_timestamp = (
        '<li class="list-last-updated">Last updated: {}</li>'.format(
            now.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    site_after += last_updated_timestamp + "\n"

    site_after += "\n" + SENTINEL + "\n" + postfix

    with open("docs/index.html", "w") as f:
        f.write(site_after)


if __name__ == "__main__":
    with open("watched.txt", "r") as f:
        sites = f.read().splitlines()
    results = update_sites(sites)
    print(results)
    with open("scan.json", "w") as f:
        f.write(json.dumps(results))
    regenerate_site(results)
