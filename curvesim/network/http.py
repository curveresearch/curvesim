"""
General utility for http requests.
"""
import aiohttp
from aiohttp import ClientResponseError
from tenacity import retry, stop_after_attempt, wait_exponential

from curvesim.exceptions import HttpClientError

stop_rule = stop_after_attempt(8)
wait_rule = wait_exponential(multiplier=1.5, min=2, max=60)


@retry(stop=stop_rule, wait=wait_rule)
async def get(url, params=None):
    kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

    if params is not None:
        kwargs.update({"params": params})

    json_data = await _call("GET", kwargs)
    return json_data


@retry(stop=stop_rule, wait=wait_rule)
async def post(url, json=None):
    kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

    if json is not None:
        kwargs.update({"json": json})

    json_data = await _call("POST", kwargs)
    return json_data


async def _call(method_name: str, kwargs):
    try:
        async with aiohttp.request(method_name, **kwargs) as resp:
            resp.raise_for_status()
            json_data = await resp.json()
    except ClientResponseError as e:
        message = e.message
        status = e.status
        url = e.request_info.url
        raise HttpClientError(status, message, url) from e

    return json_data
