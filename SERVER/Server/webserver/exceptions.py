from werkzeug.exceptions import HTTPException


class NotModified(HTTPException):
    code = 304
    description = "Not Modified"
