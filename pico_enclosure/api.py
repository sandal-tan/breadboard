"""Web API Interface."""
from io import StringIO, BytesIO
import json

import gc

from .base import BaseDevice
from .logging import logger, _exception_to_str

ENDPOINT_DOC = {}

CHUNK_SIZE = 250

HTML_BASE_PRE_BODY = """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BreadBoard: %(route)s</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-GLhlTQ8iRABdZLl6O3oVMWSktQOp6b7In1Zl3/Jr59b6EGGoI1aFkw7cmDA6j6gD" crossorigin="anonymous">
    <style>
html {
    font-size: 0.75rem;
}
    </style>
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
            <button class="accordion-button bg-primary text-muted border border-primary collapsed ps-2" type="button" data-bs-toggle="collapse" data-bs-target="#%(endpoint_name)sDoc" aria-expanded="false" aria-controls="%(endpoint_name)sDoc" style="--bs-bg-opacity: .45; height: 45px;">
                <div class="text-center text-light bg-primary border border-4 border-primary rounded me-3" style="min-width: 75px; font-size: 14px;">
                    <b>GET</b>
                </div>
                <span class="font-monospace text-light me-2" style="font-size: clamp(5px, calc(1vw + 0.75vh), 14px);">%(endpoint)s</span><span style="font-size: clamp(5px, calc(1vw + 0.75vh), 12px);">%(endpoint_description)s</span>
            </button>
        </div>
        <div class="accordion-collapse collapse mt-2" id="%(endpoint_name)sDoc" aria-labelledby="%(endpoint_name)sHeader"><div class="accordion-body">
            <p>%(long_description)s</p>
        </div>
        </div>
    </div>
</div>
"""


class EndpointGroup:
    """A collection of endpoints.

    Allows for bound method documentation.

    """

    def __init__(self, name: str, container_class, api):
        self.name = name
        self.container_class = container_class
        self.api = api
        self.__doc__ = getattr(container_class, "__doc__", "")

    def route(self, path: str, doc: bool = True, navbar: bool = False):
        route = "".join(["/" + self.name, path])

        def _wrap_func(endpoint):
            if endpoint.__class__.__name__ == "bound_method":
                desc = self.api._route_doc.get(
                    getattr(self.container_class.__class__, endpoint.__name__), ""
                )
            else:
                desc = ""

            self.api._routes[route] = endpoint
            if navbar:
                self.api._navbar_items.append(route)

            if doc and self.api._show_docs:
                base_route = route.split("/")[1]
                if base_route not in self.api._doc:
                    self.api._doc[base_route] = []
                self.api._doc[base_route].append((route, desc))
            return endpoint

        return _wrap_func

    @property
    def description(self):
        if self.__doc__ is not None:
            return self.__doc__.split("\n")[0]
        return ""


class HTTP_CONTENT_TYPE:
    HTML = "text/html"
    JSON = "application/json"
    ICON = "image/vnd.microsoft.icon"


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
    """HTTP status codes encapsulation.

    Args:
        code: The code value
        message: The associated message

    """

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __repr__(self):
        return f"{self.code} {self.message}"


class HTTP_STATUS_CODES:
    """Enumeration of HTTP status codes."""

    _200 = _StatusCode(200, "OK")
    _404 = _StatusCode(404, "PAGE NOT FOUND")
    _500 = _StatusCode(500, "INTERNAL SERVER ERROR")


class ActionEndpoint(BaseDevice):
    __doc__ = """Combine devices to perform complex actions."""

    def __init__(self, api):
        super().__init__("action", api)


class API:
    """An async API service."""

    def __init__(self, logger, show_docs: bool = True):
        self.logger = logger

        self._routes = {}

        # Contains the releveant documentation components
        # Removed after documentation is generated
        self._doc = {}

        # An IO buffer for the documentation HTML
        self._doc_io = None

        self._navbar_items = []

        self._favicon = None
        self._show_docs = show_docs
        self._route_doc = {}

        self._endpoint_groups: dict[str, EndpointGroup] = {}

        self._endpoint_groups["action"] = ActionEndpoint(self).group

        self.route("/favicon.ico", doc=False)(self.favicon_ico)

        if self._show_docs:
            self.route("/docs", navbar=True, doc=False)(self.docs)

        if self.logger.file_log:
            self.route("/logs", navbar=True, doc=False)(self.logs)

    def doc(self, doc_str: str):
        """Document an endpoint."""

        def add_doc_to_func(func):
            if self._show_docs:
                self._route_doc[func] = doc_str
            return func

        return add_doc_to_func

    @property
    def favicon(self):
        if self._favicon is None:
            self._favicon = BytesIO()
            with open("favicon.ico", "rb") as fp:
                while data := fp.read(CHUNK_SIZE):
                    self._favicon.write(data)

        return self._favicon

    @property
    def documentation(self):
        if self._doc_io is None and self._show_docs:
            self._doc_io = StringIO()
            self._doc_io.write('<div class="container">')
            for base_route, endpoints in self._doc.items():
                self._doc_io.write(
                    BASE_ROUTE_ACCORDIAN_HTML
                    % {
                        "base_route": base_route,
                        "base_route_description": self._endpoint_groups[
                            base_route
                        ].description,
                    }
                )
                for endpoint, description in endpoints:
                    split = description.split("\n")
                    if split:
                        short_description = split[0]
                        long_description = "\n".join(split[1:]).replace("\n", "<br>")
                    else:
                        short_description = description
                        long_description = ""
                    self._doc_io.write(
                        ENDPOINT_ACCORDIAN_HTML
                        % {
                            "endpoint_name": endpoint.replace("/", "_"),
                            "endpoint": endpoint,
                            "endpoint_description": short_description,
                            "long_description": long_description,
                        }
                    )
                self._doc_io.write(BASE_ROUTE_ACCORDIAN_HTML_CLOSING)
            self._doc_io.write("</div")
            del self._doc

        return self._doc_io

    def register(self, name, cls):
        _group = EndpointGroup(name, cls, self)
        self._endpoint_groups[name] = _group
        return _group

    def route(self, route: str, doc: bool = True, navbar: bool = False):
        """Decorator to manage the attaching functions to routes.

        Args:
            route: The API route to which the decorated function is attached
            doc: Whether or not to include the endpoint in documentation
            navbar: Whether or not to include the endpoint as a navbar item

        """

        if self._show_docs:

            def _wrap_func(endpoint):
                if endpoint.__class__ == "bound_method" and doc:
                    raise RuntimeError(
                        "Cannot create documentation for non-group endpoint belonging to class."
                    )
                else:
                    desc = ""

                self._routes[route] = endpoint
                if navbar:
                    self._navbar_items.append(route)

                if doc and self._show_docs:
                    base_route = route.split("/")[1]
                    if base_route not in self._doc:
                        self._doc[base_route] = []
                    self._doc[base_route].append((route, desc))
                return endpoint

        else:

            def _wrap_func(endpoint):
                return endpoint

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

            content_type = HTTP_CONTENT_TYPE.HTML

            if route == "/favicon.ico":
                content_type = HTTP_CONTENT_TYPE.ICON

            if isinstance(result, (dict, list)):
                result = {
                    "parameters": params or {},
                    "response": result,
                    "status": response_code.code,
                }
                content_type = HTTP_CONTENT_TYPE.JSON
                result = StringIO(json.dumps(result))

            writer.write(
                "HTTP/1.0 %s\r\nContent-type: %s\r\n\r\n"
                % (response_code, content_type)
            )

            if content_type == HTTP_CONTENT_TYPE.HTML:
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

            if content_type == HTTP_CONTENT_TYPE.HTML:
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
        return self.documentation

        """Return the App favicon"""

    async def favicon_ico(self):
        return self.favicon


api = API(logger)
