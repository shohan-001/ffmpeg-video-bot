
import re
import urllib.parse
from base64 import standard_b64encode
from random import choice
from typing import Optional

import cloudscraper
import requests
from bs4 import BeautifulSoup
import logging

LOGGER = logging.getLogger(__name__)

class DirectDownloadLinkException(Exception):
    pass

def direct_link_generator(text_url: str) -> Optional[str]:
    """ 
    Direct links generator 
    Ports logic from reference bot
    """
    if 'youtube.com' in text_url or 'youtu.be' in text_url:
        return None
        
    try:
        if 'yadi.sk' in text_url:
            return yandex_disk(text_url)
        elif 'mediafire.com' in text_url:
            return mediafire(text_url)
        elif 'osdn.net' in text_url:
            return osdn(text_url)
        elif 'github.com' in text_url:
            return github(text_url)
        elif '1drv.ms' in text_url:
            return onedrive(text_url)
        elif 'pixeldrain.com' in text_url:
            return pixeldrain(text_url)
        elif '1fichier.com' in text_url:
            return fichier(text_url)
        elif 'solidfiles.com' in text_url:
            return solidfiles(text_url)
        else:
            return None 
    except Exception as e:
        LOGGER.error(f"DDL Generation failed for {text_url}: {e}")
        return None


def yandex_disk(url: str) -> str:
    try:
        text_url = re.findall(r'\bhttps?://.*yadi\.sk\S+', url)[0]
    except IndexError:
        return None
    api = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}'
    try:
        dl_url = requests.get(api.format(text_url)).json()['href']
        return dl_url
    except KeyError:
        return None

def mediafire(url: str) -> str:
    try:
        text_url = re.findall(r'\bhttps?://.*mediafire\.com\S+', url)[0]
    except IndexError:
        return None
    page = BeautifulSoup(requests.get(text_url).content, 'lxml')
    info = page.find('a', {'aria-label': 'Download file'})
    return info.get('href')

def osdn(url: str) -> str:
    osdn_link = 'https://osdn.net'
    try:
        text_url = re.findall(r'\bhttps?://.*osdn\.net\S+', url)[0]
    except IndexError:
        return None
    page = BeautifulSoup(requests.get(text_url, allow_redirects=True).content, 'lxml')
    info = page.find('a', {'class': 'mirror_link'})
    text_url = urllib.parse.unquote(osdn_link + info['href'])
    mirrors = page.find('form', {'id': 'mirror-select-form'}).findAll('tr')
    urls = []
    for data in mirrors[1:]:
        mirror = data.find('input')['value']
        urls.append(re.sub(r'm=(.*)&f', f'm={mirror}&f', text_url))
    return urls[0]

def github(url: str) -> str:
    try:
        text_url = re.findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        return None
    download = requests.get(text_url, stream=True, allow_redirects=False)
    try:
        return download.headers["location"]
    except KeyError:
        return None

def onedrive(link: str) -> str:
    link_without_query = urllib.parse.urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(standard_b64encode(bytes(link_without_query, "utf-8")), "utf-8")
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    resp = requests.head(direct_link1)
    if resp.status_code != 302:
        return None
    return resp.next.url

def pixeldrain(url: str) -> str:
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
    dl_link = f"https://pixeldrain.com/api/file/{file_id}"
    resp = requests.get(info_link).json()
    if resp.get("success"):
        return dl_link
    return None

def fichier(link: str) -> str:
    # 1Fichier requires more complex handling, simplified check
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    if not re.match(regex, link):
        return None
    # Very basic scraping attempt
    try:
        req = requests.post(link)
        soup = BeautifulSoup(req.content, 'lxml')
        if soup.find("a", {"class": "ok btn-general btn-orange"}) is not None:
             return soup.find("a", {"class": "ok btn-general btn-orange"})["href"]
    except: pass
    return None

def solidfiles(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        pageSource = requests.get(url, headers=headers).text
        mainOptions = str(re.search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
        import json
        dl_url = json.loads(mainOptions)["downloadUrl"]
        return dl_url
    except: return None
