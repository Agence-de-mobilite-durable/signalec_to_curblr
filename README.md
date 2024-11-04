# MTL Street Sign to CurbLR

Transform Montreal parking sign data into CurbLR data format. For the CurbLR specification, take a tour of the [CurbLR Specification](https://github.com/curblr/curblr-spec).

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.10
- conda (Python package installer)
- Internet access for fetching the data from [Montreal Open Data](https://donnees.montreal.ca/dataset).

## Getting Started

1. **Install Dependencies**

   Install the required Python libraries:

   ```bash
   conda env create -f environment.yml
   ```

## Usage

The script is run by `inventory_transformation.py`. The file `signalec.py` is a version of the code made to convert SIGNALEC data into CurbLR.

## Example

Ensure you have an active internet connection to fetch the data from Montreal's Open Data portal. Here’s an example of how to run the script to preprocess the data and convert it to CurbLR:

```bash
python3 inventory_transformation.py 
```

This command will first preprocess the data and then start the processing to convert the Montreal parking sign data into the CurbLR format.

[//]: # (## License)

[//]: # ()
[//]: # (This project is licensed under the ----- License—see the [LICENSE]&#40;LICENSE&#41; file for details.)
