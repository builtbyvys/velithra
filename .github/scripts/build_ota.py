from asyncio import create_task, sleep
from dataclasses import dataclass, field
from http.cookies import BaseCookie
from os import getenv, path
from re import compile

from aiohttp import ClientSession
from selectolax.lexbor import LexborHTMLParser

deviceCodeName = getenv("DEVICE_CODE_NAME", "cheetah")

regexPattern = compile(
    r"(\d+\.\d+\.\d+)\s\((\w+\.\w+\.\w+)(\.[^,]+)?,\s(\w+\s\w+)(,\s.+)?\)"
)


@dataclass
class OTAInfo:
    androidVer: str
    buildVer: str
    subVer: str | None
    date: str
    user: str | None
    DLLink: str
    fName: str = field(init=False)

    def __post_init__(self):
        self.fName = self.DLLink.split("/")[-1]


class OTAChecker:
    def __init__(self) -> None:
        self.latest: None | OTAInfo = None

    async def fetch_ota(self):
        async with ClientSession() as s:
            cookie = BaseCookie({"devsite_wall_acks": "nexus-ota-tos"})
            s.cookie_jar.update_cookies(cookie)
            async with s.get("https://developers.google.com/android/ota") as res:
                soup = LexborHTMLParser(await res.text())
        targets = soup.css(f'tr[id^="{deviceCodeName}"]')
        if not targets:
            print("error: no OTA targets found.")
            return
        for target in targets[::-1]:
            version = target.css_first("td")
            if not version:
                print("error: version not found.")
                continue
            versionText = version.text()
            match = regexPattern.match(versionText)
            if not match:
                print("error: match failed.")
                continue
            downloadLink = target.css_first("a")
            if not downloadLink:
                print("error: download link not found.")
                continue
            result = [*match.groups(), downloadLink.attributes["href"]]
            info = OTAInfo(*result)
            if info.user is None or "TW" in info.user:
                self.latest = info
                break
        await self.update_ota()
        create_task(self.fetch_ota())

    async def update_ota(self):
        if self.latest is None:
            return
        filename = self.latest.fName
        if not path.exists(f"./ota/{filename}"):
            await self.download()

    async def download(self):
        if self.latest is None:
            return
        print(f"Downloading {self.latest.fName}")
        async with ClientSession() as s:
            async with s.get(self.latest.DLLink) as res:
                with open(f"./ota.zip", "wb") as f:
                    while chunk := await res.content.read(1024):
                        f.write(chunk)
        print(f"Downloaded {self.latest.fName}")


import asyncio

ota_checker = OTAChecker()
asyncio.run(ota_checker.fetch_ota())
