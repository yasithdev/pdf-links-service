import re
from typing import Set

import validators

from errors import URLError


class Util:

  def __init__(self) -> None:
    # load blacklisted URLs as regex, for validation
    with open("config/blacklist.txt") as f:
      self.blacklist = re.compile("|".join(sorted(map(str.strip, f.readlines()))), re.I)

  def canonicalize_url(self, url: str) -> str:
    """
    Canonicalize a given URL.
    Returns None for malformed URLs

    :return: Canonical URL (or None)
    """
    # sanitize URL
    url = url.strip(" /\n'\".").replace(" ", "%20")
    # convert url to canonical form
    if url.startswith("https://"):
      pass
    if url.startswith("http://"):
      url = "https://" + url[7:]
    elif url.startswith("://"):
      url = "https://" + url[3:]
    elif url.startswith("www"):
      url = "https://" + url
    # validate url
    self.validate_url(url)
    # return validated url
    return url

  def validate_url(self, url: str):
    """
    Ensure that URL is syntactically valid

    :param url: URL to validate
    :raise InvalidURLException: when URL is invalid
    """
    # validate against blacklist
    if self.blacklist.search(url):
      raise URLError(url)
    # validate if the given string is a public URL
    try:
      return validators.url(url, public=True)
    except validators.ValidationFailure:
      raise URLError(url)

  @staticmethod
  def has_match(x: str, pool: Set[str]):
    """
    Return whether the URL x has sub/super string matches in pool
    :param x: URL to check for uniqueness
    :param pool: pool of URLs to check uniqueness against
    :return: True if url is unique, else False
    """
    return any((x[8:] in y[8:]) or (y[8:] in x[8:]) for y in pool)

  @staticmethod
  def pick_uniq_urls(pool: Set[str], prefer_long=False):
    """
    Return a subset of unique URLs from pool (favors shorter URLs by default)

    :param pool: pool of URLs
    :param prefer_long: Whether to favor short URLs (default) or long URLs
    :return: subset of unique URLs
    """
    uniq_urls = set()
    for url in sorted(pool, key=len, reverse=prefer_long):
      if not Util.has_match(url, uniq_urls):
        uniq_urls.add(url)
    return uniq_urls

  @staticmethod
  def pick_new_urls(pool: Set[str], ignore_list: Set[str]) -> Set[str]:
    """
    Return a subset of URLs from pool that are not in the ignore_list

    :param pool: pool of URLs
    :param ignore_list: list of URLs to ignore
    :return: subset of new URLs
    """
    # return subset of uniq_urls that are not in blacklist
    return set(url for url in pool if not Util.has_match(url, ignore_list))
