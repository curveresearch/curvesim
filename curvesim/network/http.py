"""
General utility for http requests.
"""
from aiohttp import ClientSession
from tenacity import retry, stop_after_attempt, wait_random

stop_rule = stop_after_attempt(5)
wait_rule = wait_random(min=0.5, max=1.5)


class HTTP:
    @staticmethod
    @retry(stop=stop_rule, wait=wait_rule)
    async def get(url, params=None):

        kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

        if params is not None:
            kwargs.update({"params": params})

        async with ClientSession() as session:
            async with session.get(**kwargs) as resp:
                r = await resp.json()

        return r

    @staticmethod
    @retry(stop=stop_rule, wait=wait_rule)
    async def post(url, json=None):
        kwargs = {"url": url, "headers": {"Accept-Encoding": "gzip"}}

        if json is not None:
            kwargs.update({"json": json})

        async with ClientSession() as session:
            async with session.post(**kwargs) as resp:
                r = await resp.json()

        return r
