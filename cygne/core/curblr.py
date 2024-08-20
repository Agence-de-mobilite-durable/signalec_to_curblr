""" CurbLR variables
"""
import datetime


MANIFEST = {
    "createdDate": "2024-08-20T13:54:24-04:00",
    "lastUpdatedDate": (
        datetime.datetime.now().astimezone()
                         .replace(microsecond=0)
                         .isoformat()
    ),
    "curblrVersion": "1.1.0",
    "priorityHierarchy": ["no standing", "construction",
                          "temporary restriction", "standing", "no parking",
                          "restricted loading", "loading",
                          "restricted parking", "paid parking",
                          "parking"],
    "timeZone": "America/Montréal",
    "currency": "CAD",
    "authority": {
        "name": "Agence de mobilité durable",
        "url": "https://www.agencemobilitedurable.ca/"
    }
}

DAYS = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']

CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32188"}}
