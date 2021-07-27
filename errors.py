class URLError(Exception):

  def __init__(self, url: str, *args: object) -> None:
    super().__init__(*args)
    self.url = url

  def __str__(self) -> str:
    return f"Invalid URL: {self.url}"
