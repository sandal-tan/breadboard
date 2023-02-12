"""Web API Interface."""
import sys


class API:
    """An async API service."""

    def __init__(self):
        self._routes = {}

    def route(self, route: str):
        """Decorator to manage the attaching functions to routes.

        Args:
            route: The API route to which the decorated function is attached

        """

        def _wrap_func(func):
            self._routes[route] = func
            return func

        return _wrap_func

    async def route_requests(self, reader, writer):
        """Route incoming requests.

        Args:
            reader:
            writer:

        """
        response_code = "200 OK"
        body = ""

        request = str(await reader.readline())
        while await reader.readline() != b"\r\n":  # Ignore headers
            pass

        _, request_path, proto = request.split(
            " "
        )  # Break apart "GET \this\path?arg=1 HTTP/1.1"
        parts = request_path.split("?")
        route = parts[0]

        if len(parts) == 2:
            params = dict(v.split("=") for v in parts[1].split("&"))
        else:
            params = None

        try:
            result = await self._routes[route](**params or {})
            body = str(result)
        except KeyError:
            response_code = "404 PAGE NOT FOUND"
            body = "<h1>404 - Page Not Found</h1>"
        except Exception as e:
            repsonse_code = "500 INTERNAL SERVER ERROR"
            body = "<h1>500 - An Internal error has occured.</h1>"
            sys.print_exception(e)
        finally:
            writer.write(
                "HTTP/1.0 %s\r\nContent-type: text/html\r\n\r\n" % response_code
            )
            writer.write(
                """<!DOCTYPE html>
                <html>
                    <head><title>Pico Print</title></head>
                    <body>
                        %s
                    </body>
                </html>
                """
                % body
            )
            await writer.drain()
            await writer.wait_closed()


api = API()


@api.route("/test")
async def test_route():
    return "Hello, World"
