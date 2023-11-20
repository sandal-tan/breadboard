"""Web API Interface."""
import asyncio
from io import BytesIO
import json

from micropython import const  # pyright: ignore [reportMissingImports]

from breadboard.logging import logger, _exception_to_str

from .const import (
    POST_BOUNDARY_EXPRESSION,
    MULTIPART_DISPOSITION_NAME_EXPRESSION,
    MULTIPART_DISPOSITION_FILENAME_EXPRESSION,
)

ENDPOINT_DOC = {}

CHUNK_SIZE = const(250)
"""How many bytes to read/write at once."""


class HTTP_CONTENT_TYPE:
    """Supported HTTP content types."""

    HTML = "text/html"
    JSON = "application/json"
    ICON = "image/vnd.microsoft.icon"


class HTTP_METHODS:
    """SUpported HTTP Methods."""

    GET = "GET"
    POST = "POST"


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


class EndpointGroup:
    """A collection of endpoints.

    Allows for bound method documentation.

    """

    def __init__(self, name: str, container_class, api):
        self.name = name
        self.container_class = container_class
        self.api = api

    def route(self, path: str, method: str = HTTP_METHODS.GET):
        """Add an API endpoint under a shared path.

        Args:
            path: The relative path within the group
            method: The HTTP method to associate with the endpoint

        """
        return self.api.route("".join(["/" + self.name, path]), method)


class FileResult:
    """Encapsulation for returning a file via the API.

    path: The local path to the file to return
    content_type: The type of content in the file
    file_mode: The mode in which the file is opened

    """

    def __init__(
        self, path, content_type: str = HTTP_CONTENT_TYPE.JSON, file_mode: str = "rb"
    ):
        self.path = path
        self.content_type = content_type
        self.mode = file_mode


class MultiPartUpload:
    """An encapsulation of a file uploaded via a POST.

    This is just a wrapper around the underlying stream to avoid
    handling the data where it is not needed.

    Args:
        name: A name for the upload
        reader: The stream reader from which the data is read
        boundary: The string representing the end boundary condition
        filename: The filename of the given upload

    """

    def __init__(
        self, name: str, reader: asyncio.StreamReader, boundary: str, filename=None
    ):
        self.name = name
        self.boundary = boundary
        self.filename = filename or ""


async def parse_multipart_formdata(reader: asyncio.StreamReader, boundary, params):
    """Parse a multipart/form-data body.

    Args:
        reader: The stream which contains the multipart body
        boundary: The boundary used to split entries
        params: The dictionary used to store endpoint parameters

    """

    while line := await reader.readline():
        if boundary in line:
            if line[-4:-2] == b"--":
                break

            # Read the Content-Disposition header :
            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition#as_a_header_for_a_multipart_body
            disposition = await reader.readline()

            if match := MULTIPART_DISPOSITION_NAME_EXPRESSION.match(
                disposition.decode()
            ):
                name = match.group(1)
            else:
                raise RuntimeError()

            if match := MULTIPART_DISPOSITION_FILENAME_EXPRESSION.match(
                disposition.decode()
            ):
                filename = match.group(1)
            else:
                filename = None

            while await reader.readline() != b"\r\n":
                # Consumer Content-Type header and the carriage return before the data
                pass

            while await reader.readline() != b"\r\n":
                # Consume the data
                pass

            params[name] = MultiPartUpload(name, reader, boundary, filename=filename)


class API:
    """An async API service."""

    def __init__(self):
        self._routes = {}
        self._endpoint_groups: dict[str, EndpointGroup] = {}

    def register(self, name, cls):
        """Register an endpoint group  with the API.

        Args:
            name: A name (used as a path prefix) for the group
            cls: The device instance to be registered with the group

        """
        _group = EndpointGroup(name, cls, self)
        self._endpoint_groups[name] = _group
        return _group

    def route(
        self,
        route: str,
        method: str = HTTP_METHODS.GET,
    ):
        """Decorator to manage the attaching functions to routes.

        Args:
            route: The API route to which the decorated function is attached
            method: The HTTP method to associate with the endpoint

        Notes:
            This can be used as a decorator or a function

        Returns:
            A callable to add a route as configured by this function call

        """

        def _wrap_func(endpoint):
            if route not in self._routes:
                self._routes[route] = {}
            self._routes[route][method] = endpoint

            return endpoint

        return _wrap_func

    def unquote(self, string):
        """unquote('abc%20def') -> b'abc def'.

        Note: if the input is a str instance it is encoded as UTF-8.
        This is only an issue if it contains unescaped non-ASCII characters,
        which URIs should not.

        Source:
            https://forum.micropython.org/viewtopic.php?t=3076#p54352
        """

        if not string:
            return ""

        if isinstance(string, str):
            string = string.encode("utf-8")

        bits = string.split(b"%")
        if len(bits) == 1:
            return string.decode()

        res = bytearray(bits[0])

        for item in bits[1:]:
            try:
                res.append(int(item[:2], 16))
                res.extend(item[2:])
            except KeyError:
                res.append(b"%")
                res.extend(item)

        return bytes(res).decode()

    async def call_endpoint(self, endpoint, params):
        """Call an endpoint.

        Args:
            endpoint: The endpoint to call
            params: The parameters passed as keyword arguments to ``endpoint``

        Returns:
            The result of the underlying endpoint logic.

        """

        result = await endpoint(**params)
        if isinstance(result, (dict, list)) or result is None:
            result = {
                "parameters": params or {},
                "response": result or {},
            }
        return result

    async def end_communication(
        self,
        result,
        route: str,
        source: str,
        writer: asyncio.StreamWriter,
        response_code=HTTP_STATUS_CODES._200,
        log_method=logger.info,
        log_message="",
    ):
        """The end of communication logic handle responding to the connector and terminating the connection.

        Args:
            result: The IO to write back to the client
            route: The client's requested route
            source: The source of the client
            writer: The StreamWriter for the client
            response_code: The HTTP response with which to end the communication

        """
        log_method(
            log_message,
            route=route,
            status_code=response_code.code,
            source=source,
        )

        if isinstance(result, dict):
            result["status"] = response_code.code
            content_type = HTTP_CONTENT_TYPE.JSON
            result = BytesIO(json.dumps(result).encode())
        elif isinstance(result, FileResult):
            content_type = result.content_type
            result = open(result.path, result.mode)
        else:
            raise RuntimeError("Unsupported result type: %s", type(result))

        writer.write(
            b"HTTP/1.0 %s\r\nContent-type: %s\r\n\r\n" % (response_code, content_type)
        )

        result.seek(0)
        while body_chunk := result.read(CHUNK_SIZE):
            writer.write(body_chunk)
            await writer.drain()

        await writer.wait_closed()

    async def route_requests(self, reader, writer):
        """Route incoming requests.

        Args:
            reader: An IO containing the input request
            writer: The output IO for the response

        """

        # --- Set up handling state ---
        params = {}
        source = ":".join(str(v) for v in reader.get_extra_info("peername"))
        # ---

        # --- Breakdown request ---
        request = (await reader.readline()).decode()

        # method, path, protocol
        method, request_path, _ = request.split(
            " "
        )  # Break apart "GET \this\path?arg=1 HTTP/1.1"
        parts = self.unquote(request_path).split("?")
        route = parts[0]

        try:
            endpoint = self._routes[route][method]
        except KeyError:
            return await self.end_communication(
                writer=writer,
                result={"error": f"Not found: {route}"},
                route=route,
                source=source,
                response_code=HTTP_STATUS_CODES._404,
                log_method=logger.error,
            )

        if len(parts) == 2:
            params = dict(v.split("=") for v in parts[1].split("&"))

        if method != HTTP_METHODS.POST:
            while await reader.readline() != b"\r\n":  # Ignore headers
                pass
        else:
            # Consumer headers until we get to the Content-Type header which defines the boundary key
            while (line := await reader.readline()) and line != b"\r\n":
                if match := POST_BOUNDARY_EXPRESSION.match(line):
                    boundary = match.group(1).strip()
                    params = await parse_multipart_formdata(reader, boundary, params)
                    break
        # ---

        # --- Dispatch to defined route, handling errors.
        try:
            result = await self.call_endpoint(endpoint, params)
            await self.end_communication(
                result, route, source, writer, log_message=str(params) if params else ""
            )
        except Exception as e:
            await self.end_communication(
                route=route,
                source=source,
                writer=writer,
                result={"error": "Unexpected server error"},
                response_code=HTTP_STATUS_CODES._500,
                log_method=logger.error,
                log_message=_exception_to_str(e),
            )

    async def logs(self):
        # TODO truncate logs
        return (
            '<div class="container">'
            + "".join(logger.log_buffer.getvalue().split("\n")[:-20:-1])
            + "</div>"
        )


api = API()
