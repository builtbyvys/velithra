from asyncio import create_task, sleep
from dataclasses import dataclass, field
from http.cookies import BaseCookie
from os import getenv, path, makedirs
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
    fullName: str = field(init=False)

    def __post_init__(self):
        self.fullName = self.DLLink.split("/")[-1]
        name, ext = self.fullName.rsplit(".", 1)
        parts = name.split("-")
        # Drop last part if it looks like a hash (8+ hex chars)
        if len(parts[-1]) >= 8 and all(c in "0123456789abcdef" for c in parts[-1].lower()):
            name = "-".join(parts[:-1])
        else:
            name = "-".join(parts)
        self.fName = f"{name}.{ext}"


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

        for target in reversed(targets):
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
        if not path.exists(f"./{filename}"):
            await self.download()

    async def download(self):
        if self.latest is None:
            return
        print(f"Downloading {self.latest.fullName} as {self.latest.fName}")
        async with ClientSession() as s:
            async with s.get(self.latest.DLLink) as res:
                with open(f"./{self.latest.fName}", "wb") as f:
                    while chunk := await res.content.read(1024):
                        f.write(chunk)
        print(f"Downloaded {self.latest.fName}")


# Run the checker
import asyncio

ota_checker = OTAChecker()
asyncio.run(ota_checker.fetch_ota())