"""
General utility for http requests.
"""
import aiohttp
from aiohttp import ClientResponseError
from tenacity import retry, stop_after_attempt, wait_random_exponential

from curvesim.exceptions import HttpClientError

stop_rule = stop_after_attempt(10)
wait_rule = wait_random_exponential(multiplier=1, min=2, max=20)


class HTTP:
    @staticmethod
    @retry(stop=stop_rule, wait=wait_rule)
    async def get(url, params=None):

        kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

        if params is not None:
            kwargs.update({"params": params})

        try:
            async with aiohttp.request("GET", **kwargs) as resp:
                resp.raise_for_status()
                json_data = await resp.json()
        except ClientResponseError as e:
            message = e.message
            status = e.status
            url = e.request_info.url
            # pylint: disable-next=raise-missing-from
            raise HttpClientError(status, message, url)

        return json_data

    @staticmethod
    @retry(stop=stop_rule, wait=wait_rule)
    async def post(url, json=None):
        kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

        if json is not None:
            kwargs.update({"json": json})

        try:
            async with aiohttp.request("POST", **kwargs) as resp:
                resp.raise_for_status()
                json_data = await resp.json()
        except ClientResponseError as e:
            message = e.message
            status = e.status
            url = e.request_info.url
            # pylint: disable-next=raise-missing-from
            raise HttpClientError(status, message, url)

        return json_data
