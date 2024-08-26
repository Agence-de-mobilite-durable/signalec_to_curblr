"""Location"""

from dataclasses import (
    dataclass,
    field
)
from shapely import (
    Point,
    LineString
)

from cygne.core.enum import (
    SideOfStreet,
    TrafficDir
)


@dataclass
class Location():
    """ Support that panels are on
    """
    location: Point
    side_of_street: SideOfStreet
    street_id: int
    asset_type: str = None
    _linear_reference: float = field(init=False, default=-1)
    _traffic_dir: int = field(init=False, default=TrafficDir.UNSET)
    _road_geom: LineString = field(init=False, default=None)
    _road_length: float = field(init=False, default=-1)

    def __eq__(self, other):
        return (
            self.location == other.location and
            self.side_of_street == other.side_of_street and
            self.street_id == other.street_id
        )

    def __hash__(self) -> int:
        return hash((self.location, self.side_of_street, self.street_id))

    def to_curblr(self) -> dict[str, object]:
        """Convert Location to CurbLR

        Returns
        -------
        dict[str, object]
        """
        return {
            "shstRefId": self.street_id,
            "shstLocationStart": -1,
            "shstLocationEnd": -1,
            "sideOfStreet": self.side_of_street.name.lower(),
            "objectId": -1,
            "derivedFrom": [],
            "assetType": self.asset_type
        }

    @property
    def linear_reference(self):
        """Return the Linear reference of this location

        Returns
        -------
        float
        """
        return self._linear_reference

    @linear_reference.setter
    def linear_reference(self, lr: float):
        self._linear_reference = lr

    @property
    def traffic_dir(self):
        """ Return the traffic dir on the street of the location

        Returns
        -------
        int
        """
        return self._traffic_dir

    @traffic_dir.setter
    def traffic_dir(self, direction: TrafficDir):
        self._traffic_dir = direction

    @property
    def road_geometry(self):
        """ Return the road geometry of the street of the location

        Returns
        -------
        int
        """
        return self._road_geom

    @road_geometry.setter
    def road_geometry(self, geometry: LineString):
        self._road_geom = geometry

    @property
    def road_length(self):
        """ Return the traffic dir on the street of the location

        Returns
        -------
        int
        """
        return self._road_length

    @road_length.setter
    def road_length(self, length: float):
        self._road_length = length
