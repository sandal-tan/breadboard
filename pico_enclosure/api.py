"""Web API Interface."""
import json

import gc

from .logging import logger, _exception_to_str
from io import StringIO

CHUNK_SIZE = 250

HTML_BASE_PRE_BODY = """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BreadBoard: %(route)s</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-GLhlTQ8iRABdZLl6O3oVMWSktQOp6b7In1Zl3/Jr59b6EGGoI1aFkw7cmDA6j6gD" crossorigin="anonymous">
    </head>
    <body>
        <nav class="navbar sticky-top navbar-expand-lg" style="background-color: #8cc04b;">
            <div class="container-fluid">
                <a class="navbar-brand" href="/docs">BreadBoard</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarSupportedContent">
                    <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                        %(navbar_items)s
                    </ul>
                </div>
            </div>
        </nav>
        <div class="container-xxl bd-gutter mt-3 my-md-4 bd-layout">
"""

HTML_BASE_POST_BODY = """
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js" integrity="sha384-w76AqPfDkMBDXo30jS1Sgez6pr3x5MlQ1ZAGC+nuZB+EYdgRZgiwxhTBTkF7CXvN" crossorigin="anonymous"></script>
    </body>
</html>
"""

BASE_ROUTE_ACCORDIAN_HTML = """
<div class="accordion mb-3" id="%(base_route)sAccordion">
    <div class="accordion-item">
        <p class="accordion-header" id="%(base_route)sHeader">
            <button class="accordion-button bg-dark text-muted" type="button" data-bs-toggle="collapse" data-bs-target="#%(base_route)sDoc" aria-expanded="true" aria-controls="%(base_route)sDoc">
                <b class="h3 me-2">%(base_route)s</b><wbr>%(base_route_description)s
            </button>
        </p>
        <div class="accordion-collapse collapse show mt-2" id="%(base_route)sDoc" aria-labelledby="%(base_route)sHeader"><div class="accordion-body">
"""
BASE_ROUTE_ACCORDIAN_HTML_CLOSING = """
        </div>
        </div>
    </div>
</div>
"""

ENDPOINT_ACCORDIAN_HTML = """
<div class="accordion" id="%(endpoint_name)sAccordion">
    <div class="accordion-item mb-3">
        <div class="accordion-header" id="%(endpoint_name)sHeader">
            <button class="accordion-button bg-primary text-muted border border-primary collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#%(endpoint_name)sDoc" aria-expanded="false" aria-controls="%(endpoint_name)sDoc" style="--bs-bg-opacity: .45; height: 50px;">
                <div class="text-center text-light bg-primary border border-4 border-primary rounded me-3" style="min-width: 100px;">
                    <b>GET</b>
                </div>
                <span class="font-monospace text-light me-2">%(endpoint)s</span><wbr>%(endpoint_description)s
            </button>
        </div>
        <div class="accordion-collapse collapse mt-2" id="%(endpoint_name)sDoc" aria-labelledby="%(endpoint_name)sHeader"><div class="accordion-body">
            %(endpoint_description)s
        </div>
        </div>
    </div>
</div>
"""

LOREM_IMPSUM = "Lorem ipsum dolor sit amet"


def define_navbar(route, items):
    return "\n".join(
        f'<li class="nav-item"><a class="nav-link%(additional)s" href="%(link)s">%(text)s</a></li>'
        % {
            "additional": "" if v != route else ' active" aria-current="page"',
            "link": v,
            "text": v.replace("/", ""),
        }
        for v in items
    )


class _StatusCode:
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __repr__(self):
        return f"{self.code} {self.message}"


class HTTP_STATUS_CODES:
    _200 = _StatusCode(200, "OK")
    _404 = _StatusCode(404, "PAGE NOT FOUND")
    _500 = _StatusCode(500, "INTERNAL SERVER ERROR")


class API:
    """An async API service."""

    def __init__(self, logger):
        self.logger = logger
        self._routes = {}
        self._doc = {}
        self._doc_io = None
        self._navbar_items = []

        self.route("/docs", navbar=True, doc=False)(self.docs)
        if self.logger.file_log:
            self.route("/logs", navbar=True, doc=False)(self.logs)

    @property
    def doc(self):
        if self._doc_io is None:
            self._doc_io = StringIO()
            self._doc_io.write('<div class="container">')
            for base_route, endpoints in self._doc.items():
                self._doc_io.write(
                    BASE_ROUTE_ACCORDIAN_HTML
                    % {
                        "base_route": base_route,
                        "base_route_description": LOREM_IMPSUM,
                    }
                )
                for endpoint in endpoints:
                    self._doc_io.write(
                        ENDPOINT_ACCORDIAN_HTML
                        % {
                            "endpoint_name": endpoint.replace("/", "_"),
                            "endpoint": endpoint,
                            "endpoint_description": LOREM_IMPSUM,
                        }
                    )
                self._doc_io.write(BASE_ROUTE_ACCORDIAN_HTML_CLOSING)
            self._doc_io.write("</div")

        return self._doc_io

    def route(self, route: str, doc: bool = True, navbar: bool = False):
        """Decorator to manage the attaching functions to routes.

        Args:
            route: The API route to which the decorated function is attached
            doc: Whether or not to include the endpoint in documentation
            navbar: Whether or not to include the endpoint as a navbar item

        """

        def _wrap_func(func):
            self._routes[route] = func
            if navbar:
                self._navbar_items.append(route)

            if doc:
                base_route = route.split("/")[1]
                if base_route not in self._doc:
                    self._doc[base_route] = []
                self._doc[base_route].append(route)
            return func

        return _wrap_func

    async def route_requests(self, reader, writer):
        """Route incoming requests.

        Args:
            reader: An IO containing the input request
            writer: The output IO for the response

        """

        request = str(await reader.readline())
        while await reader.readline() != b"\r\n":  # Ignore headers
            pass

        # method, path, protocol
        _, request_path, _ = request.split(
            " "
        )  # Break apart "GET \this\path?arg=1 HTTP/1.1"
        parts = request_path.split("?")
        route = parts[0]

        if len(parts) == 2:
            params = dict(v.split("=") for v in parts[1].split("&"))
        else:
            params = None

        response_code = HTTP_STATUS_CODES._200
        log_method = self.logger.info

        result = None
        log_message = str(params) if params else ""
        try:
            result = await self._routes[route](**params or {})
        except KeyError:
            response_code = HTTP_STATUS_CODES._404
            log_method = self.logger.error
        except Exception as e:
            response_code = HTTP_STATUS_CODES._500
            log_method = self.logger.error
            log_message = _exception_to_str(e)
        finally:
            if result is None:
                raise Exception()

            log_method(
                log_message or "",
                route=route,
                status_code=response_code.code,
                source=":".join(str(v) for v in reader.get_extra_info("peername")),
            )

            writer.write(
                "HTTP/1.0 %s\r\nContent-type: text/html\r\n\r\n" % response_code
            )

            writer.write(
                HTML_BASE_PRE_BODY
                % {
                    "route": route,
                    "navbar_items": define_navbar(route, self._navbar_items),
                }
            )
            await writer.drain()

            result.seek(0)
            body_chunk = result.read(CHUNK_SIZE)
            while body_chunk:
                writer.write(body_chunk)
                await writer.drain()
                body_chunk = result.read(CHUNK_SIZE)

            writer.write(HTML_BASE_POST_BODY)
            await writer.drain()
            await writer.wait_closed()

    async def logs(self):
        # TODO truncate logs
        return (
            '<div class="container">'
            + "".join(self.logger.log_buffer.getvalue().split("\n")[:-20:-1])
            + "</div>"
        )

    async def docs(self):
        """Autogenerated documentation for available endpoints."""
        return self.doc


api = API(logger)
