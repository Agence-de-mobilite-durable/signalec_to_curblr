from cygne.preprocessing.signalec.signalec_preprocessing import (
    transform_signalec as process_signalec
)
from cygne.preprocessing.paid_parking_preprocessing import (
    main as process_mtl_paid_parking
)
from cygne.preprocessing.catalogue_preprocessing import (
    main as process_catalog
)
from cygne.preprocessing.fire_hydrants import process_fire_hydrants


__all__ = ['process_signalec', 'process_mtl_paid_parking', 'process_catalog',
           'process_fire_hydrants']
