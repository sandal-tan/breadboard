"""Web API Interface."""


class API:
    def __init__(self):
        self._routes = {}

    def route(self, route: str):
        def _wrap_func(func):
            self._routes[route] = func
            return func

        return _wrap_func

    async def route_requests(self, reader, writer):
        request = str(await reader.readline())
        while await reader.readline() != b"\r\n":  # Ignore headers
            pass

        method, request_path, proto = request.split(" ")
        parts = request_path.split("?")
        route = parts[0]
        if len(parts) == 2:
            params = dict(v.split("=") for v in parts[0].split("&"))
        else:
            params = None

        try:
            result = await self._routes[route](*params or [])
            print(result)

            writer.write("HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n")
            writer.write(
                """<!DOCTYPE html>
        <html>
            <head><title>Pico Print</title></head>
            <body>
                <h1>%s</h1>
            </body>
        </html>
        """
                % result
            )
            await writer.drain()
            await writer.wait_closed()
        except KeyError:
            writer.write(
                "HTTP/1.0 404 PAGE NOT FOUND\r\nContent-type: text/html\r\n\r\n"
            )
            writer.write(
                """<!DOCTYPE html>
        <html>
            <head><title>Pico Print</title></head>
            <body>
                <h1>404 - Page Not Found</h1>
            </body>
        </html>
        """
            )
            pass  # TODO Raise  404


api = API()


@api.route("/test")
async def test_route():
    return "Hello, World"
