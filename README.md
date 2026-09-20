# ro_parties
A simple non-secure and non production FastAPI and utilities to hold current parliamentary configuration in Romania

> **WARNING**: DO NOT RUN IN PRODUCTION!

## Usage

### Install requirements

```shell
pip install -r requirements.txt
```

### Start FastAPI server

```shell
uvicorn main:app
```

### Populate DB

```
./populate_db.py -h
```

### Calculate configurations in the parliament

You can use the FastAPI `/docs` interface (located at `127.0.0.1:8000`).

Or, you can use the client:

```python
import openapi_client
from openapi_client.api.default_api import DefaultApi
api_host = "127.0.0.1:8000"
```

```python
configuration = openapi_client.configuration.Configuration()
configuration.host = api_host
api_client = openapi_client.ApiClient(configuration)
client = DefaultApi(api_client)
```

```python
# fetch majority calculation for parties with ids 1 and 2
client.read_parties_configuration_parties_get([1,2])
```

## License

[Apache-2.0 license](https://github.com/alghe-global/ro_parties/blob/master/LICENSE)
