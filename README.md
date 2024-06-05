# veggie_tracking

Right now the data is coming from CSV files and being used to fill an SQLite database that will be transfered to the webhost for the flask app -- no interaction with the data, just reading at the moment.

The table names are:

- Beds
- Crops
- Plantings
- SoilImprovements

Create conda env:

```
conda env create --name farmapp --file=environment.yaml
```
... and then activate it:

```
conda activate farmapp
```

To initiate and fill an SQLite database:

```
python db_init.py
```

To run the flask app in debug mode locally:

```
flask --app farmapp run --debug
```