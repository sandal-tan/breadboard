"""API related contants."""

import re

from micropython import const  # pyright: ignore [reportMissingImports]

HTML_BASE_PRE_BODY = const(
    """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BreadBoard: %(route)s</title>
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
)

HTML_BASE_POST_BODY = const(
    """
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js" integrity="sha384-w76AqPfDkMBDXo30jS1Sgez6pr3x5MlQ1ZAGC+nuZB+EYdgRZgiwxhTBTkF7CXvN" crossorigin="anonymous"></script>
    </body>
</html>
"""
)

BASE_ROUTE_ACCORDIAN_HTML = const(
    """
<div class="accordion mb-3" id="%(base_route)sAccordion">
    <div class="accordion-item">
        <p class="accordion-header" id="%(base_route)sHeader">
            <button class="accordion-button bg-dark text-muted" type="button" data-bs-toggle="collapse" data-bs-target="#%(base_route)sDoc" aria-expanded="true" aria-controls="%(base_route)sDoc">
                <b class="h3 me-2">%(base_route)s</b><wbr>%(base_route_description)s
            </button>
        </p>
        <div class="accordion-collapse collapse show mt-2" id="%(base_route)sDoc" aria-labelledby="%(base_route)sHeader"><div class="accordion-body">
"""
)

BASE_ROUTE_ACCORDIAN_HTML_CLOSING = const(
    """
        </div>
        </div>
    </div>
</div>
"""
)

ENDPOINT_ACCORDIAN_HTML = const(
    """
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
)

POST_BOUNDARY_EXPRESSION = re.compile(
    r"Content-Type: multipart/form-data; boundary=(.*)"
)

MULTIPART_DISPOSITION_NAME_EXPRESSION = re.compile(
    r'Content-Disposition: form-data; name="(.*?)"'
)

MULTIPART_DISPOSITION_FILENAME_EXPRESSION = re.compile(
    r'Content-Disposition: form-data; name=".*?"; filename="(.*?)"'
)
