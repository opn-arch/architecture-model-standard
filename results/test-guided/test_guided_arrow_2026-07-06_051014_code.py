# _version.py
"""Version information for the package."""

# Version tuple for programmatic access
VERSION_INFO = (1, 0, 0)

# Pre-release identifier (e.g., 'alpha', 'beta', 'rc1', or None for stable)
PRE_RELEASE = None

# Build metadata (e.g., commit hash, build number, or None)
BUILD_META = None


def _build_version_string(version_info, pre_release=None, build_meta=None):
    """Build a PEP 440 compliant version string from components.

    Args:
        version_info: Tuple of (major, minor, patch) integers.
        pre_release: Optional pre-release identifier string.
        build_meta: Optional build metadata string.

    Returns:
        A formatted version string.
    """
    version = ".".join(str(v) for v in version_info)

    if pre_release is not None:
        version = f"{version}-{pre_release}"

    if build_meta is not None:
        version = f"{version}+{build_meta}"

    return version


def get_version():
    """Return the full version string for the package.

    Returns:
        The version string (e.g., '1.0.0', '1.0.0-beta', '1.0.0+build123').
    """
    return _build_version_string(VERSION_INFO, PRE_RELEASE, BUILD_META)


def get_version_tuple():
    """Return the version as a tuple of integers (major, minor, patch).

    Returns:
        A tuple of three integers representing the version.
    """
    return VERSION_INFO


def get_major():
    """Return the major version number.

    Returns:
        An integer representing the major version.
    """
    return VERSION_INFO[0]


def get_minor():
    """Return the minor version number.

    Returns:
        An integer representing the minor version.
    """
    return VERSION_INFO[1]


def get_patch():
    """Return the patch version number.

    Returns:
        An integer representing the patch version.
    """
    return VERSION_INFO[2]


def is_pre_release():
    """Check if this version is a pre-release.

    Returns:
        True if this is a pre-release version, False otherwise.
    """
    return PRE_RELEASE is not None


def is_compatible(required_version):
    """Check if the current version is compatible with a required version.

    Compatibility is determined by matching major version and having
    a minor version >= the required minor version (semver compatible).

    Args:
        required_version: A string like '1.0.0' or a tuple of (major, minor, patch).

    Returns:
        True if the current version is compatible, False otherwise.
    """
    if isinstance(required_version, str):
        parts = required_version.strip().split(".")
        required_tuple = tuple(int(p) for p in parts[:3])
    else:
        required_tuple = tuple(required_version)

    # Major version must match
    if VERSION_INFO[0] != required_tuple[0]:
        return False

    # Minor version must be >= required
    if VERSION_INFO[1] < required_tuple[1]:
        return False

    # If minor versions match, patch must be >= required
    if VERSION_INFO[1] == required_tuple[1] and len(required_tuple) > 2:
        if VERSION_INFO[2] < required_tuple[2]:
            return False

    return True
# api.py
"""API module providing factory functions and getter utilities."""

import time
from datetime import datetime, timezone


def factory(cls, *args, **kwargs):
    """Factory function that creates and returns an instance of the given class."""
    return cls(*args, **kwargs)


def get(collection, key, default=None):
    """Get a value from a collection by key with an optional default."""
    if isinstance(collection, dict):
        return collection.get(key, default)
    elif isinstance(collection, (list, tuple)):
        try:
            return collection[key]
        except (IndexError, TypeError):
            return default
    elif hasattr(collection, '__getitem__'):
        try:
            return collection[key]
        except (KeyError, IndexError, TypeError):
            return default
    return default


def get_attr(obj, name, default=None):
    """Get an attribute from an object with an optional default."""
    return getattr(obj, name, default)


def get_nested(data, *keys, default=None):
    """Get a nested value from a dictionary using a sequence of keys."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[key]
            except (IndexError, TypeError):
                return default
        else:
            return default
        if current is None:
            return default
    return current


def get_first(iterable, predicate=None, default=None):
    """Get the first item from an iterable that matches the predicate."""
    for item in iterable:
        if predicate is None or predicate(item):
            return item
    return default


def get_all(collection, keys, default=None):
    """Get multiple values from a collection by a list of keys."""
    results = []
    for key in keys:
        results.append(get(collection, key, default))
    return results


def get_env(key, default=None):
    """Get an environment variable value with an optional default."""
    import os
    return os.environ.get(key, default)


def now(tz=None, fmt=None):
    """Get the current datetime, optionally formatted as a string.
    
    Args:
        tz: Timezone to use. Defaults to UTC.
        fmt: Optional strftime format string. If provided, returns a formatted string.
    
    Returns:
        A datetime object or formatted string representing the current time.
    """
    if tz is None:
        tz = timezone.utc
    current_time = datetime.now(tz=tz)
    if fmt is not None:
        return current_time.strftime(fmt)
    return current_time

# arrow.py
"""Arrow module containing the Arrow class for date/time manipulation."""

import calendar
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from math import copysign

from dateutil import tz as dateutil_tz
from dateutil.relativedelta import relativedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .constants import MAX_TIMESTAMP, MAX_TIMESTAMP_US, MAX_TIMESTAMP_MS
from .util import normalize_timestamp, iso_to_gregorian


class Arrow:
    """An Arrow object representing a datetime with timezone awareness."""

    _ATTRS = [
        "year", "month", "day", "hour", "minute", "second",
        "microsecond", "tzinfo", "fold"
    ]

    _ATTRS_PLURAL = [
        "years", "months", "weeks", "days", "hours", "minutes",
        "seconds", "microseconds"
    ]

    _MONTHS_PER_QUARTER = 3
    _SECS_PER_MINUTE = 60
    _SECS_PER_HOUR = 3600
    _SECS_PER_DAY = 86400
    _SECS_PER_WEEK = 604800

    min = None
    max = None
    resolution = datetime.resolution

    def __init__(self, year, month, day, hour=0, minute=0, second=0,
                 microsecond=0, tzinfo=None, **kwargs):
        if tzinfo is None:
            tzinfo = dateutil_tz.tzutc()

        if isinstance(tzinfo, str):
            tzinfo = self._get_tzinfo(tzinfo)

        fold = kwargs.get("fold", 0)

        self._datetime = datetime(
            year, month, day, hour, minute, second, microsecond,
            tzinfo=tzinfo, fold=fold
        )

    @staticmethod
    def _get_tzinfo(tz_expr):
        if isinstance(tz_expr, str):
            try:
                return ZoneInfo(tz_expr)
            except (KeyError, Exception):
                dt_tz = dateutil_tz.gettz(tz_expr)
                if dt_tz is None:
                    raise ValueError(f"Could not parse timezone expression: {tz_expr}")
                return dt_tz
        return tz_expr

    # Class methods

    @classmethod
    def now(cls, tzinfo=None):
        if tzinfo is None:
            tzinfo = dateutil_tz.tzlocal()
        if isinstance(tzinfo, str):
            tzinfo = cls._get_tzinfo(tzinfo)
        dt = datetime.now(tzinfo)
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dt.tzinfo, fold=dt.fold
        )

    @classmethod
    def utcnow(cls):
        dt = datetime.now(dateutil_tz.tzutc())
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dateutil_tz.tzutc(), fold=0
        )

    @classmethod
    def fromtimestamp(cls, timestamp, tzinfo=None):
        if tzinfo is None:
            tzinfo = dateutil_tz.tzlocal()
        if isinstance(tzinfo, str):
            tzinfo = cls._get_tzinfo(tzinfo)
        dt = datetime.fromtimestamp(timestamp, tz=tzinfo)
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dt.tzinfo
        )

    @classmethod
    def utcfromtimestamp(cls, timestamp):
        dt = datetime.utcfromtimestamp(timestamp).replace(tzinfo=dateutil_tz.tzutc())
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dateutil_tz.tzutc()
        )

    @classmethod
    def fromdatetime(cls, dt, tzinfo=None):
        if tzinfo is None:
            if dt.tzinfo is None:
                tzinfo = dateutil_tz.tzutc()
            else:
                tzinfo = dt.tzinfo
        elif isinstance(tzinfo, str):
            tzinfo = cls._get_tzinfo(tzinfo)

        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=tzinfo
        )

    @classmethod
    def fromdate(cls, date, tzinfo=None):
        if tzinfo is None:
            tzinfo = dateutil_tz.tzutc()
        elif isinstance(tzinfo, str):
            tzinfo = cls._get_tzinfo(tzinfo)

        return cls(date.year, date.month, date.day, tzinfo=tzinfo)

    @classmethod
    def strptime(cls, date_str, fmt, tzinfo=None):
        dt = datetime.strptime(date_str, fmt)
        if tzinfo is None:
            tzinfo = dt.tzinfo or dateutil_tz.tzutc()
        elif isinstance(tzinfo, str):
            tzinfo = cls._get_tzinfo(tzinfo)
        return cls(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=tzinfo
        )

    @classmethod
    def fromordinal(cls, ordinal):
        dt = datetime.fromordinal(ordinal)
        return cls(dt.year, dt.month, dt.day, tzinfo=dateutil_tz.tzutc())

    @classmethod
    def range(cls, frame, start, end=None, tz=None, limit=None):
        results = []
        current = start if isinstance(start, Arrow) else cls.fromdatetime(start)

        if end is not None:
            end = end if isinstance(end, Arrow) else cls.fromdatetime(end)

        i = 0
        while True:
            if limit is not None and i >= limit:
                break
            if end is not None and current > end:
                break
            results.append(current)
            current = current.shift(**{f"{frame}s": 1})
            i += 1

        return results

    # Properties

    @property
    def datetime(self):
        return self._datetime

    @property
    def naive(self):
        return self._datetime.replace(tzinfo=None)

    @property
    def timestamp(self):
        return self._datetime.timestamp()

    @property
    def int_timestamp(self):
        return int(self._datetime.timestamp())

    @property
    def float_timestamp(self):
        return self._datetime.timestamp()

    @property
    def fold(self):
        return self._datetime.fold

    @property
    def ambiguous(self):
        return dateutil_tz.datetime_ambiguous(self._datetime)

    @property
    def imaginary(self):
        return not dateutil_tz.datetime_exists(self._datetime)

    @property
    def date(self):
        return self._datetime.date

    @property
    def time(self):
        return self._datetime.time

    @property
    def quarter(self):
        return int((self._datetime.month - 1) / self._MONTHS_PER_QUARTER) + 1

    @property
    def week(self):
        return self._datetime.isocalendar()[1]

    # Instance methods

    def astimezone(self, tz):
        if isinstance(tz, str):
            tz = self._get_tzinfo(tz)
        dt = self._datetime.astimezone(tz)
        return self.__class__(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dt.tzinfo, fold=dt.fold
        )

    def to(self, tz):
        return self.astimezone(tz)

    def span(self, frame, count=1, bounds="[)"):
        floor = self.floor(frame)
        ceil = floor.ceil(frame)
        return floor, ceil

    def floor(self, frame):
        if frame == "year":
            return self.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif frame == "quarter":
            quarter_month = ((self._datetime.month - 1) // 3) * 3 + 1
            return self.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif frame == "month":
            return self.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif frame == "week":
            weekday = self._datetime.isoweekday()
            delta = timedelta(days=weekday - 1)
            floored = self._datetime - delta
            return self.__class__(
                floored.year, floored.month, floored.day,
                tzinfo=self._datetime.tzinfo
            )
        elif frame == "day":
            return self.replace(hour=0, minute=0, second=0, microsecond=0)
        elif frame == "hour":
            return self.replace(minute=0, second=0, microsecond=0)
        elif frame == "minute":
            return self.replace(second=0, microsecond=0)
        elif frame == "second":
            return self.replace(microsecond=0)
        return self.clone()

    def ceil(self, frame):
        floor = self.floor(frame)
        if floor == self:
            return floor

        if frame == "year":
            return floor.shift(years=1, microseconds=-1)
        elif frame == "quarter":
            return floor.shift(months=3, microseconds=-1)
        elif frame == "month":
            return floor.shift(months=1, microseconds=-1)
        elif frame == "week":
            return floor.shift(weeks=1, microseconds=-1)
        elif frame == "day":
            return floor.shift(days=1, microseconds=-1)
        elif frame == "hour":
            return floor.shift(hours=1, microseconds=-1)
        elif frame == "minute":
            return floor.shift(minutes=1, microseconds=-1)
        elif frame == "second":
            return floor.shift(seconds=1, microseconds=-1)
        return self.clone()

    def clone(self):
        return self.__class__(
            self._datetime.year, self._datetime.month, self._datetime.day,
            self._datetime.hour, self._datetime.minute, self._datetime.second,
            self._datetime.microsecond, tzinfo=self._datetime.tzinfo,
            fold=self._datetime.fold
        )

    def replace(self, **kwargs):
        absolute_kwargs = {}
        for key in self._ATTRS:
            if key in kwargs:
                absolute_kwargs[key] = kwargs[key]

        fold = kwargs.get("fold", self._datetime.fold)

        current = self._datetime
        new_dt = current.replace(**absolute_kwargs, fold=fold) if absolute_kwargs else current.replace(fold=fold)

        return self.__class__(
            new_dt.year, new_dt.month, new_dt.day,
            new_dt.hour, new_dt.minute, new_dt.second,
            new_dt.microsecond, tzinfo=new_dt.tzinfo, fold=new_dt.fold
        )

    def shift(self, **kwargs):
        relative_kwargs = {}
        for key in ["years", "months", "weeks", "days", "hours", "minutes", "seconds", "microseconds"]:
            if key in kwargs:
                relative_kwargs[key] = kwargs[key]

        if relative_kwargs:
            dt = self._datetime + relativedelta(**relative_kwargs)
        else:
            dt = self._datetime

        return self.__class__(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, tzinfo=dt.tzinfo, fold=dt.fold
        )

    def format(self, fmt=None, locale="en_us"):
        if fmt is None:
            return self._datetime.isoformat()
        if fmt.startswith("%"):
            return self._datetime.strftime(fmt)
        # Simple format token replacement
        return self._format_token(fmt)

    def _format_token(self, fmt):
        result = fmt
        result = result.replace("YYYY", f"{self._datetime.year:04d}")
        result = result.replace("MM", f"{self._datetime.month:02d}")
        result = result.replace("DD", f"{self._datetime.day:02d}")
        result = result.replace("HH", f"{self._datetime.hour:02d}")
        result = result.replace("mm", f"{self._datetime.minute:02d}")
        result = result.replace("ss", f"{self._datetime.second:02d}")
        result = result.replace("ZZ", self._datetime.strftime("%z"))
        return result

    def strftime(self, fmt):
        return self._datetime.strftime(fmt)

    def ctime(self):
        return self._datetime.ctime()

    def toordinal(self):
        return self._datetime.toordinal()

    def isoformat(self, sep="T", timespec="auto"):
        return self._datetime.isoformat(sep=sep, timespec=timespec)

    def isocalendar(self):
        return self._datetime.isocalendar()

    def isoweekday(self):
        return self._datetime.isoweekday()

    def weekday(self):
        return self._datetime.weekday()

    def timetuple(self):
        return self._datetime.timetuple()

    def utctimetuple(self):
        return self._datetime.utctimetuple()

    def dst(self):
        return self._datetime.dst()

    def utcoffset(self):
        return self._datetime.utcoffset()

    def tzname(self):
        return self._datetime.tzname()

    # Humanize

    def humanize(self, other=None, locale="en_us", only_distance=False, granularity="second"):
        if other is None:
            other = self.utcnow()
        if isinstance(other, Arrow):
            delta = other._datetime - self._datetime
        else:
            delta = other - self._datetime
        return str(delta)

    # Dunder methods

    def __repr__(self):
        return f"<Arrow [{self._datetime.isoformat()}]>"

    def __str__(self):
        return self._datetime.isoformat()

    def __format__(self, formatstr):
        if not formatstr:
            return str(self)
        return self.format(formatstr)

    def __hash__(self):
        return self._datetime.__hash__()

    def __eq__(self, other):
        if isinstance(other, Arrow):
            return self._datetime == other._datetime
        if isinstance(other, datetime):
            return self._datetime == other
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, (Arrow, datetime)):
            return not self.__eq__(other)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Arrow):
            return self._datetime > other._datetime
        if isinstance(other, datetime):
            return self._datetime > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Arrow):
            return self._datetime >= other._datetime
        if isinstance(other, datetime):
            return self._datetime >= other
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Arrow):
            return self._datetime < other._datetime
        if isinstance(other, datetime):
            return self._datetime < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Arrow):
            return self._datetime <= other._datetime
        if isinstance(other, datetime):
            return self._datetime <= other
        return NotImplemented

    def __add__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            result = self._datetime + other
            return self.__class__(
                result.year, result.month, result.day, result.hour,
                result.minute, result.second, result.microsecond,
                tzinfo=result.tzinfo
            )
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, (timedelta, relativedelta)):
            result = self._datetime - other
            return self.__class__(
                result.year, result.month, result.day, result.hour,
                result.minute, result.second, result.microsecond,
                tzinfo=result.tzinfo
            )
        if isinstance(other, Arrow):
            return self._datetime - other._datetime
        if isinstance(other, datetime):
            return self._datetime - other
        return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, datetime):
            return other - self._datetime
        return NotImplemented

    def __getattr__(self, name):
        if name in self._ATTRS:
            return getattr(self._datetime, name)
        raise AttributeError(f"'Arrow' object has no attribute '{name}'")

    def __bool__(self):
        return True


Arrow.min = Arrow(1, 1, 1, tzinfo=dateutil_tz.tzutc())
Arrow.max = Arrow(9999, 12, 31, 23, 59, 59, 999999, tzinfo=dateutil_tz.tzutc())

# constants.py
"""
constants.py - Application-wide constants and configuration values.
"""

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# Application Settings
APP_NAME = "application"
APP_VERSION = "1.0.0"
DEFAULT_ENCODING = "utf-8"
DEFAULT_LOCALE = "en_US"

# Pagination
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# Authentication
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days
TOKEN_ALGORITHM = "HS256"
TOKEN_TYPE = "Bearer"
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

# Database
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600
DB_ECHO = False

# Cache
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 1000
CACHE_PREFIX = "app_cache"

# File Upload
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"})
ALLOWED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx"})
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# Date/Time Formats
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT_DISPLAY = "%B %d, %Y %I:%M %p"

# Rate Limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW_SECONDS = 60

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_DEFAULT = "INFO"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# API
API_PREFIX = "/api"
API_VERSION = "v1"
API_BASE_URL = f"{API_PREFIX}/{API_VERSION}"

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
]
CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]
CORS_MAX_AGE = 86400

# Retry Configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

# Timeouts (in seconds)
REQUEST_TIMEOUT = 30
CONNECTION_TIMEOUT = 10
READ_TIMEOUT = 30

# Sorting
SORT_ASC = "asc"
SORT_DESC = "desc"
DEFAULT_SORT_ORDER = SORT_ASC

# Environment Names
ENV_DEVELOPMENT = "development"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"
ENV_TESTING = "testing"

# Content Types
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTIPART = "multipart/form-data"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_PLAIN = "text/plain"

# Regex Patterns
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PHONE_REGEX = r"^\+?1?\d{9,15}$"
UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
# factory.py
# factory.py

from datetime import datetime, date
from typing import Optional, Union

from .arrow import Arrow
from .parser import DateTimeParser
from .util import iso_to_gregorian


class ArrowFactory:
    """A factory class for generating Arrow objects."""

    type = Arrow

    def __init__(self, type: type = Arrow):
        """Initialize the factory with a custom Arrow type if desired.
        
        Args:
            type: The Arrow or Arrow-subclass type to generate.
        """
        self.type = type

    def get(self, *args, **kwargs) -> Arrow:
        """Generate an Arrow object based on the input arguments.
        
        This method is overloaded to handle multiple input signatures:
        - No arguments: returns current UTC time
        - Single Arrow: returns a copy
        - Single datetime: converts to Arrow
        - Single date: converts to Arrow at midnight
        - Single numeric (int/float): treats as timestamp
        - Single string with format string(s): parses the string
        - Two strings: first is date string, second is format
        - String with list of formats: tries each format
        - Multiple numeric args: treated as datetime components (year, month, day, ...)
        
        Returns:
            An Arrow object.
        """
        arg_count = len(args)
        locale = kwargs.get("locale", "en_us")
        tz = kwargs.get("tzinfo", None) or kwargs.get("tz", None)

        # No arguments: current UTC time
        if arg_count == 0:
            if kwargs and not tz and not locale:
                return self.type.now(tz)
            return self.type.utcnow()

        # Single argument cases
        if arg_count == 1:
            arg = args[0]

            # Arrow instance: return a clone
            if isinstance(arg, Arrow):
                return self.type.fromdatetime(arg.datetime, tzinfo=tz or arg.tzinfo)

            # datetime instance
            if isinstance(arg, datetime):
                return self.type.fromdatetime(arg, tzinfo=tz or arg.tzinfo)

            # date instance (not datetime, since datetime is subclass of date)
            if isinstance(arg, date) and not isinstance(arg, datetime):
                return self.type.fromdate(arg, tzinfo=tz)

            # Numeric (timestamp)
            if isinstance(arg, (int, float)):
                return self.type.fromtimestamp(arg, tzinfo=tz)

            # String with no format: try ISO 8601 parsing
            if isinstance(arg, str):
                parser = DateTimeParser(locale=locale)
                try:
                    dt = parser.parse_iso(arg)
                    return self.type.fromdatetime(dt, tzinfo=tz or dt.tzinfo)
                except Exception:
                    raise ValueError(
                        f"Could not parse date string '{arg}' without a format."
                    )

            # Tuple/list of components
            if isinstance(arg, (tuple, list)):
                return self.type(*arg, tzinfo=tz)

        # Two arguments: string + format or string + list of formats
        if arg_count == 2:
            arg_1, arg_2 = args[0], args[1]

            # (str, str) - date string and format string
            if isinstance(arg_1, str) and isinstance(arg_2, str):
                parser = DateTimeParser(locale=locale)
                dt = parser.parse(arg_1, arg_2)
                return self.type.fromdatetime(dt, tzinfo=tz or dt.tzinfo)

            # (str, list) - date string and list of possible formats
            if isinstance(arg_1, str) and isinstance(arg_2, (list, tuple)):
                parser = DateTimeParser(locale=locale)
                last_exception = None
                for fmt in arg_2:
                    try:
                        dt = parser.parse(arg_1, fmt)
                        return self.type.fromdatetime(dt, tzinfo=tz or dt.tzinfo)
                    except Exception as e:
                        last_exception = e
                        continue
                raise ValueError(
                    f"Could not parse '{arg_1}' with any of the given formats."
                ) from last_exception

        # Multiple numeric arguments: datetime components (year, month, day, ...)
        if arg_count >= 3:
            if all(isinstance(a, (int, float)) for a in args):
                int_args = [int(a) for a in args]
                return self.type(*int_args, tzinfo=tz)

        raise TypeError(
            f"Cannot generate Arrow object from arguments: {args}, {kwargs}"
        )

# formatter.py
# formatter.py

from datetime import datetime


class DateTimeFormatter:
    def __init__(self, default_format: str = "%Y-%m-%d %H:%M:%S"):
        """Initialize the formatter with a default format string."""
        self.default_format = default_format
        self.format_presets = {
            "iso": "%Y-%m-%dT%H:%M:%S",
            "date": "%Y-%m-%d",
            "time": "%H:%M:%S",
            "short": "%m/%d/%Y",
            "long": "%B %d, %Y %I:%M %p",
            "compact": "%Y%m%d%H%M%S",
        }

    def format(self, dt: datetime = None, fmt: str = None) -> str:
        """Format a datetime object using the specified or default format.

        Args:
            dt: The datetime to format. Defaults to current datetime if None.
            fmt: Format string or preset name. Defaults to self.default_format if None.

        Returns:
            Formatted datetime string.
        """
        if dt is None:
            dt = datetime.now()

        if fmt is None:
            fmt = self.default_format
        elif fmt in self.format_presets:
            fmt = self.format_presets[fmt]

        return dt.strftime(fmt)

# locales.py
"""Locales module."""


class Locale:
    """Base locale class."""

    def __init__(self, language_code="en", region_code=None):
        self.language_code = language_code
        self.region_code = region_code

    def __str__(self):
        if self.region_code:
            return f"{self.language_code}_{self.region_code}"
        return self.language_code

    def __repr__(self):
        return f"Locale(language_code='{self.language_code}', region_code='{self.region_code}')"

    def __eq__(self, other):
        if not isinstance(other, Locale):
            return NotImplemented
        return (self.language_code == other.language_code and
                self.region_code == other.region_code)

    def __hash__(self):
        return hash((self.language_code, self.region_code))
# locales.py

from .utils import normalize_locale_name


_locale_map = {}


def get_locale(name):
    """Get a locale instance by name."""
    normalized = name.lower().replace("-", "_")
    if normalized not in _locale_map:
        raise ValueError(f"Unsupported locale: {name}")
    return _locale_map[normalized]()


def get_locale_by_class_name(class_name):
    """Get a locale instance by its class name."""
    for key, locale_cls in _locale_map.items():
        if locale_cls.__name__ == class_name:
            return locale_cls()
    raise ValueError(f"Unknown locale class: {class_name}")


class Locale:
    names = []
    
    _day_names = [
        "", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    _day_abbreviations = [
        "", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
    ]
    _month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    _month_abbreviations = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    _meridians = {"am": "am", "pm": "pm", "AM": "AM", "PM": "PM"}

    def __init__(self):
        self._day_name_map = {name.lower(): i for i, name in enumerate(self._day_names) if name}
        self._day_abbr_map = {abbr.lower(): i for i, abbr in enumerate(self._day_abbreviations) if abbr}

    def day_name(self, day_number):
        """Return the full day name for a given day number (1=Monday, 7=Sunday)."""
        if day_number < 1 or day_number > 7:
            raise ValueError(f"Invalid day number: {day_number}")
        return self._day_names[day_number]

    def day_abbreviation(self, day_number):
        """Return the abbreviated day name for a given day number (1=Monday, 7=Sunday)."""
        if day_number < 1 or day_number > 7:
            raise ValueError(f"Invalid day number: {day_number}")
        return self._day_abbreviations[day_number]

    def meridian(self, hour, token):
        """Return the meridian (am/pm) for the given hour."""
        if hour < 12:
            meridian_key = "am" if token.islower() else "AM"
        else:
            meridian_key = "pm" if token.islower() else "PM"
        return self._meridians[meridian_key]

    def describe(self, timeframe, delta=0, only_distance=False):
        """Describe a time delta in human-readable form."""
        humanized = self._format_timeframe(timeframe, delta)
        if only_distance:
            return humanized
        if timeframe == "now":
            return "just now"
        if delta < 0:
            return f"{humanized} ago"
        return f"in {humanized}"

    def describe_multi(self, timeframes, only_distance=False):
        """Describe multiple timeframes in human-readable form."""
        parts = []
        for timeframe, delta in timeframes:
            parts.append(self._format_timeframe(timeframe, abs(delta)))
        humanized = ", ".join(parts)
        if only_distance:
            return humanized
        if timeframes and timeframes[0][1] < 0:
            return f"{humanized} ago"
        return f"in {humanized}"

    def _format_timeframe(self, timeframe, delta):
        """Format a single timeframe with its delta value."""
        abs_delta = abs(delta)
        frames = {
            "now": "just now",
            "second": "a second",
            "seconds": f"{abs_delta} seconds",
            "minute": "a minute",
            "minutes": f"{abs_delta} minutes",
            "hour": "an hour",
            "hours": f"{abs_delta} hours",
            "day": "a day",
            "days": f"{abs_delta} days",
            "week": "a week",
            "weeks": f"{abs_delta} weeks",
            "month": "a month",
            "months": f"{abs_delta} months",
            "year": "a year",
            "years": f"{abs_delta} years",
        }
        return frames.get(timeframe, f"{abs_delta} {timeframe}")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in getattr(cls, "names", []):
            _locale_map[name.lower().replace("-", "_")] = cls


class EnglishLocale(Locale):
    names = ["en", "en_us", "en_gb", "en_au", "en_ca"]

    def describe(self, timeframe, delta=0, only_distance=False):
        """English-specific describe with proper grammar."""
        humanized = self._format_timeframe(timeframe, delta)
        if only_distance:
            return humanized
        if timeframe == "now":
            return "just now"
        if delta < 0:
            return f"{humanized} ago"
        return f"in {humanized}"


class ThaiLocale(Locale):
    names = ["th", "th_th"]
    
    _day_names = [
        "", "วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"
    ]
    _day_abbreviations = [
        "", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."
    ]
    _BE_OFFSET = 543

    def year_full(self, year):
        """Return the full Buddhist Era year."""
        return year + self._BE_OFFSET

    def year_abbreviation(self, year):
        """Return the abbreviated Buddhist Era year (last two digits)."""
        full_year = self.year_full(year)
        return full_year % 100


class LaotianLocale(Locale):
    names = ["lo", "lo_la"]
    
    _day_names = [
        "", "ວັນຈັນ", "ວັນອັງຄານ", "ວັນພຸດ", "ວັນພະຫັດ", "ວັນສຸກ", "ວັນເສົາ", "ວັນອາທິດ"
    ]
    _day_abbreviations = [
        "", "ຈ.", "ອ.", "ພ.", "ພຫ.", "ສ.", "ສ.", "ອາ."
    ]
    _BE_OFFSET = 543

    def year_full(self, year):
        """Return the full Buddhist Era year for Laotian locale."""
        return year + self._BE_OFFSET

    def year_abbreviation(self, year):
        """Return the abbreviated Buddhist Era year (last two digits)."""
        full_year = self.year_full(year)
        return full_year % 100

# parser.py
# parser.py

import re
from datetime import datetime, timedelta, timezone, tzinfo

from .locales import EnglishLocale


class ParserError(ValueError):
    """Base exception for parser errors."""
    pass


class ParserMatchError(ParserError):
    """Exception raised when a date/time string cannot be matched."""
    pass


class DateTimeParser:
    _PATTERN_ISO = re.compile(
        r"(\d{4})"
        r"(?:[-/](\d{1,2}))"
        r"(?:[-/](\d{1,2}))"
        r"(?:[T\s](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?"
        r"(?:\.(\d+))?"
        r"(Z|[+-]\d{2}:?\d{2})?"
        r")?"
    )

    _PATTERN_TIMESTAMP = re.compile(r"^\-?\d+\.?\d*$")

    _FORMAT_TOKENS = re.compile(
        r"YYYY|YY|MM?M?M?|DD?|HH?|hh?|mm?|ss?|A|a|ZZ?Z?|S+"
    )

    _TOKEN_MAP = {
        "YYYY": r"(?P<year>\d{4})",
        "YY": r"(?P<year>\d{2})",
        "MMMM": r"(?P<month_name>\w+)",
        "MMM": r"(?P<month_abbr>\w+)",
        "MM": r"(?P<month>\d{2})",
        "M": r"(?P<month>\d{1,2})",
        "DD": r"(?P<day>\d{2})",
        "D": r"(?P<day>\d{1,2})",
        "HH": r"(?P<hour>\d{2})",
        "H": r"(?P<hour>\d{1,2})",
        "hh": r"(?P<hour>\d{2})",
        "h": r"(?P<hour>\d{1,2})",
        "mm": r"(?P<minute>\d{2})",
        "m": r"(?P<minute>\d{1,2})",
        "ss": r"(?P<second>\d{2})",
        "s": r"(?P<second>\d{1,2})",
        "A": r"(?P<meridiem>AM|PM)",
        "a": r"(?P<meridiem>am|pm)",
        "ZZZ": r"(?P<tzname>[A-Za-z/_]+)",
        "ZZ": r"(?P<tzoffset>[+-]\d{2}:\d{2})",
        "Z": r"(?P<tzoffset>[+-]\d{2}\d{2})",
        "S": r"(?P<microsecond>\d+)",
    }

    def __init__(self, locale=None):
        self._locale = locale or EnglishLocale()

    def parse_iso(self, datetime_string):
        if not isinstance(datetime_string, str):
            raise ParserError("Expected a string, got {!r}".format(type(datetime_string)))

        datetime_string = datetime_string.strip()

        match = self._PATTERN_ISO.fullmatch(datetime_string)
        if match is None:
            match = self._PATTERN_ISO.match(datetime_string)

        if match is None:
            raise ParserMatchError(
                "Could not match ISO format for '{}'".format(datetime_string)
            )

        groups = match.groups()
        year = int(groups[0])
        month = int(groups[1]) if groups[1] else 1
        day = int(groups[2]) if groups[2] else 1
        hour = int(groups[3]) if groups[3] else 0
        minute = int(groups[4]) if groups[4] else 0
        second = int(groups[5]) if groups[5] else 0

        microsecond = 0
        if groups[6]:
            frac = groups[6][:6].ljust(6, "0")
            microsecond = int(frac)

        tz = None
        if groups[7]:
            tz = TzinfoParser.parse(groups[7])

        return datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond,
            tzinfo=tz,
        )

    def parse(self, datetime_string, fmt):
        if not isinstance(datetime_string, str):
            raise ParserError("Expected a string, got {!r}".format(type(datetime_string)))

        if not isinstance(fmt, str):
            raise ParserError("Expected a format string, got {!r}".format(type(fmt)))

        if self._PATTERN_TIMESTAMP.match(datetime_string) and fmt == "X":
            timestamp = float(datetime_string)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)

        fmt_tokens = self._FORMAT_TOKENS.findall(fmt)
        if not fmt_tokens:
            raise ParserError("Could not find any format tokens in '{}'".format(fmt))

        regex_fmt = fmt
        for token in self._FORMAT_TOKENS.finditer(fmt):
            token_str = token.group(0)
            if token_str.startswith("S"):
                replacement = self._TOKEN_MAP["S"]
            elif token_str in self._TOKEN_MAP:
                replacement = self._TOKEN_MAP[token_str]
            else:
                raise ParserError("Unrecognized token '{}'".format(token_str))
            regex_fmt = regex_fmt.replace(token_str, replacement, 1)

        regex_fmt = "^" + regex_fmt + "$"

        try:
            pattern = re.compile(regex_fmt)
        except re.error as e:
            raise ParserError("Failed to compile format regex: {}".format(e))

        match = pattern.match(datetime_string)
        if match is None:
            raise ParserMatchError(
                "Failed to match '{}' when parsing '{}'".format(fmt, datetime_string)
            )

        parts = match.groupdict()

        year = int(parts.get("year", 1))
        if year < 100:
            year += 2000

        month = 1
        if "month" in parts:
            month = int(parts["month"])
        elif "month_name" in parts:
            month = self._locale.month_number(parts["month_name"])
        elif "month_abbr" in parts:
            month = self._locale.month_abbreviation_number(parts["month_abbr"])

        day = int(parts.get("day", 1))
        hour = int(parts.get("hour", 0))
        minute = int(parts.get("minute", 0))
        second = int(parts.get("second", 0))

        microsecond = 0
        if "microsecond" in parts and parts["microsecond"]:
            frac = parts["microsecond"][:6].ljust(6, "0")
            microsecond = int(frac)

        if "meridiem" in parts and parts["meridiem"]:
            meridiem = parts["meridiem"].lower()
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

        tz = None
        if "tzoffset" in parts and parts["tzoffset"]:
            tz = TzinfoParser.parse(parts["tzoffset"])
        elif "tzname" in parts and parts["tzname"]:
            tz = TzinfoParser.parse(parts["tzname"])

        return datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond,
            tzinfo=tz,
        )


class TzinfoParser:
    _OFFSET_PATTERN = re.compile(r"([+-])(\d{2}):?(\d{2})")

    @classmethod
    def parse(cls, tzinfo_string):
        if not isinstance(tzinfo_string, str):
            raise ParserError("Expected a string, got {!r}".format(type(tzinfo_string)))

        tzinfo_string = tzinfo_string.strip()

        if tzinfo_string in ("Z", "z", "UTC", "utc"):
            return timezone.utc

        match = cls._OFFSET_PATTERN.match(tzinfo_string)
        if match:
            sign = match.group(1)
            hours = int(match.group(2))
            minutes = int(match.group(3))

            total_seconds = (hours * 3600 + minutes * 60)
            if sign == "-":
                total_seconds = -total_seconds

            return timezone(timedelta(seconds=total_seconds))

        try:
            import zoneinfo
            return zoneinfo.ZoneInfo(tzinfo_string)
        except (ImportError, KeyError):
            try:
                import dateutil.tz
                tz = dateutil.tz.gettz(tzinfo_string)
                if tz is not None:
                    return tz
            except ImportError:
                pass

        raise ParserError("Could not parse timezone expression '{}'".format(tzinfo_string))

# util.py
"""util.py - Utility functions for date/time operations."""

import datetime
import re


def next_weekday(date, weekday):
    """Find the next occurrence of a given weekday from a date.
    
    Args:
        date: A datetime.date or datetime.datetime object.
        weekday: Integer 0-6 (Monday=0, Sunday=6).
    
    Returns:
        The next date that falls on the specified weekday.
    """
    days_ahead = weekday - date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return date + datetime.timedelta(days=days_ahead)


def is_timestamp(value):
    """Check if a value is a valid Unix timestamp.
    
    Args:
        value: The value to check.
    
    Returns:
        True if the value is a valid numeric timestamp, False otherwise.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        try:
            datetime.datetime.utcfromtimestamp(value)
            return True
        except (OSError, OverflowError, ValueError):
            return False
    if isinstance(value, str):
        try:
            float_val = float(value)
            datetime.datetime.utcfromtimestamp(float_val)
            return True
        except (ValueError, OSError, OverflowError):
            return False
    return False


def validate_ordinal(ordinal):
    """Validate that a value is a valid date ordinal.
    
    Args:
        ordinal: An integer representing a date ordinal.
    
    Returns:
        The validated ordinal as an integer.
    
    Raises:
        TypeError: If ordinal is not an integer.
        ValueError: If ordinal is out of valid range.
    """
    if not isinstance(ordinal, int):
        raise TypeError(f"Expected int, got {type(ordinal).__name__}")
    if ordinal < 1:
        raise ValueError(f"Ordinal must be >= 1, got {ordinal}")
    max_ordinal = datetime.date.max.toordinal()
    if ordinal > max_ordinal:
        raise ValueError(f"Ordinal must be <= {max_ordinal}, got {ordinal}")
    return ordinal


def normalize_timestamp(timestamp):
    """Normalize a timestamp to a float value in seconds.
    
    Args:
        timestamp: A numeric timestamp (int, float, or string representation).
    
    Returns:
        The timestamp as a float in seconds.
    
    Raises:
        ValueError: If the timestamp cannot be normalized.
        TypeError: If the input type is not supported.
    """
    if isinstance(timestamp, bool):
        raise TypeError("Boolean values are not valid timestamps")
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    if isinstance(timestamp, str):
        timestamp = timestamp.strip()
        try:
            return float(timestamp)
        except ValueError:
            raise ValueError(f"Cannot normalize timestamp from string: '{timestamp}'")
    if isinstance(timestamp, datetime.datetime):
        return timestamp.timestamp()
    if isinstance(timestamp, datetime.date):
        return datetime.datetime(timestamp.year, timestamp.month, timestamp.day).timestamp()
    raise TypeError(f"Unsupported type for timestamp normalization: {type(timestamp).__name__}")


def iso_to_gregorian(iso_year, iso_week, iso_day):
    """Convert an ISO year, week, and day to a Gregorian date.
    
    Args:
        iso_year: The ISO year.
        iso_week: The ISO week number (1-53).
        iso_day: The ISO day of the week (1=Monday, 7=Sunday).
    
    Returns:
        A datetime.date object representing the Gregorian date.
    
    Raises:
        ValueError: If the ISO week or day is out of range.
    """
    if not (1 <= iso_day <= 7):
        raise ValueError(f"ISO day must be between 1 and 7, got {iso_day}")
    if not (1 <= iso_week <= 53):
        raise ValueError(f"ISO week must be between 1 and 53, got {iso_week}")

    jan4 = datetime.date(iso_year, 1, 4)
    start = jan4 - datetime.timedelta(days=jan4.isoweekday() - 1)
    result = start + datetime.timedelta(weeks=iso_week - 1, days=iso_day - 1)

    if result.isocalendar()[1] != iso_week and iso_week == 53:
        raise ValueError(f"ISO year {iso_year} does not have 53 weeks")

    return result


def validate_bounds(value, lower=None, upper=None, inclusive_lower=True, inclusive_upper=True):
    """Validate that a value is within specified bounds.
    
    Args:
        value: The value to validate.
        lower: The lower bound (None for no lower bound).
        upper: The upper bound (None for no upper bound).
        inclusive_lower: Whether the lower bound is inclusive.
        inclusive_upper: Whether the upper bound is inclusive.
    
    Returns:
        The validated value.
    
    Raises:
        ValueError: If the value is out of bounds.
    """
    if lower is not None:
        if inclusive_lower:
            if value < lower:
                raise ValueError(f"Value {value} is below lower bound {lower}")
        else:
            if value <= lower:
                raise ValueError(f"Value {value} must be greater than {lower}")

    if upper is not None:
        if inclusive_upper:
            if value > upper:
                raise ValueError(f"Value {value} is above upper bound {upper}")
        else:
            if value >= upper:
                raise ValueError(f"Value {value} must be less than {upper}")

    return value

# conf.py
"""Configuration module for application settings management."""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


# Default configuration values
DEFAULTS: Dict[str, Any] = {
    "debug": False,
    "log_level": "INFO",
    "host": "127.0.0.1",
    "port": 8000,
    "database_url": "sqlite:///app.db",
    "secret_key": "change-me-in-production",
    "allowed_hosts": ["localhost", "127.0.0.1"],
    "max_connections": 100,
    "timeout": 30,
    "retry_attempts": 3,
    "cache_ttl": 300,
    "static_dir": "static",
    "template_dir": "templates",
}


class ConfigError(Exception):
    """Raised when a configuration error occurs."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class Config:
    """Application configuration manager."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None, env_prefix: str = "APP"):
        self._data: Dict[str, Any] = dict(DEFAULTS)
        self._env_prefix = env_prefix
        self._config_path = Path(config_path) if config_path else None
        self._loaded = False

        if self._config_path:
            self.load_from_file(self._config_path)

        self.load_from_env()
        self._loaded = True

    def load_from_file(self, path: Union[str, Path]) -> None:
        """Load configuration from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            self._data.update(file_data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {e}")
        except IOError as e:
            raise ConfigError(f"Error reading configuration file: {e}")

    def load_from_env(self) -> None:
        """Load configuration from environment variables with the configured prefix."""
        prefix = f"{self._env_prefix}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._data[config_key] = self._parse_env_value(value)

    def _parse_env_value(self, value: str) -> Any:
        """Parse an environment variable value into an appropriate Python type."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.startswith("[") and value.endswith("]"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        if value.startswith("{") and value.endswith("}"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by key, supporting dot notation."""
        keys = key.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to configuration values."""
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Configuration key '{name}' not found")

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access to configuration values."""
        value = self.get(key)
        if value is None and key not in self._data:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting of configuration values."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key) is not None

    def to_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return dict(self._data)

    def save_to_file(self, path: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to a JSON file."""
        save_path = Path(path) if path else self._config_path
        if save_path is None:
            raise ConfigError("No file path specified for saving configuration")

        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
        except IOError as e:
            raise ConfigError(f"Error writing configuration file: {e}")

    def validate(self, required_keys: Optional[list] = None) -> bool:
        """Validate that all required configuration keys are present and non-None."""
        if required_keys is None:
            required_keys = ["secret_key", "database_url"]

        missing = [key for key in required_keys if self.get(key) is None]
        if missing:
            raise ConfigError(f"Missing required configuration keys: {', '.join(missing)}")
        return True

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._data = dict(DEFAULTS)

    def merge(self, other: Dict[str, Any]) -> None:
        """Deep merge another dictionary into the current configuration."""
        self._deep_merge(self._data, other)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def __repr__(self) -> str:
        """Return a string representation of the Config object."""
        return f"Config(keys={list(self._data.keys())}, loaded={self._loaded})"


# Module-level singleton instance
_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None, env_prefix: str = "APP") -> Config:
    """Get or create the singleton Config instance."""
    global _instance
    if _instance is None:
        _instance = Config(config_path=config_path, env_prefix=env_prefix)
    return _instance


def reset_config() -> None:
    """Reset the singleton Config instance."""
    global _instance
    _instance = None

# utils.py
"""utils.py - Utility functions for timezone and datetime testing/comparison."""

import pytz
from datetime import datetime, timezone, timedelta


def make_full_tz_list():
    """Generate a complete list of all available timezone strings from pytz.

    Returns:
        list: A sorted list of all available timezone names including
              common timezones and all pytz timezones.
    """
    all_timezones = set(pytz.all_timezones)
    all_timezones.update(pytz.common_timezones)
    return sorted(all_timezones)


def assert_datetime_equality(dt1, dt2, tolerance_seconds=0):
    """Assert that two datetime objects are equal within an optional tolerance.

    Args:
        dt1 (datetime): First datetime to compare.
        dt2 (datetime): Second datetime to compare.
        tolerance_seconds (int|float): Maximum allowed difference in seconds.
            Defaults to 0 for exact equality.

    Raises:
        AssertionError: If the datetimes differ by more than the tolerance,
            with a descriptive message showing both values and the difference.
    """
    if dt1.tzinfo is None and dt2.tzinfo is not None:
        raise AssertionError(
            f"Cannot compare naive and aware datetimes: {dt1} vs {dt2}"
        )
    if dt1.tzinfo is not None and dt2.tzinfo is None:
        raise AssertionError(
            f"Cannot compare aware and naive datetimes: {dt1} vs {dt2}"
        )

    if dt1.tzinfo is not None and dt2.tzinfo is not None:
        dt1_utc = dt1.astimezone(timezone.utc)
        dt2_utc = dt2.astimezone(timezone.utc)
        diff = abs((dt1_utc - dt2_utc).total_seconds())
    else:
        diff = abs((dt1 - dt2).total_seconds())

    if diff > tolerance_seconds:
        raise AssertionError(
            f"Datetimes differ by {diff}s (tolerance: {tolerance_seconds}s). "
            f"dt1={dt1}, dt2={dt2}"
        )


def assert_timezone_equivalence(tz1, tz2, reference_dt=None):
    """Assert that two timezones produce the same UTC offset for a given datetime.

    Args:
        tz1: First timezone (string name or tzinfo object).
        tz2: Second timezone (string name or tzinfo object).
        reference_dt (datetime, optional): The datetime at which to compare offsets.
            Defaults to the current UTC time if not provided.

    Raises:
        AssertionError: If the two timezones have different UTC offsets at the
            reference datetime, with a message showing both offsets.
    """
    if reference_dt is None:
        reference_dt = datetime.now(timezone.utc)

    if isinstance(tz1, str):
        tz1 = pytz.timezone(tz1)
    if isinstance(tz2, str):
        tz2 = pytz.timezone(tz2)

    if reference_dt.tzinfo is None:
        ref_aware = pytz.utc.localize(reference_dt)
    else:
        ref_aware = reference_dt.astimezone(pytz.utc)

    dt_in_tz1 = ref_aware.astimezone(tz1)
    dt_in_tz2 = ref_aware.astimezone(tz2)

    offset1 = dt_in_tz1.utcoffset()
    offset2 = dt_in_tz2.utcoffset()

    if offset1 != offset2:
        raise AssertionError(
            f"Timezones are not equivalent at {reference_dt}. "
            f"tz1 ({tz1}) offset: {offset1}, tz2 ({tz2}) offset: {offset2}"
        )