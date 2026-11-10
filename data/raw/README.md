# Raw Data Directory

Place the four uncompressed Kaggle CSV files into this directory.

## Source
- Dataset: **Solar Power Generation Data**
- Author: Anik Annal
- URL: [https://www.kaggle.com/datasets/anikannal/solar-power-generation-data](https://www.kaggle.com/datasets/anikannal/solar-power-generation-data)

## Expected Files

1. `Plant_1_Generation_Data.csv`
2. `Plant_1_Weather_Sensor_Data.csv`
3. `Plant_2_Generation_Data.csv`
4. `Plant_2_Weather_Sensor_Data.csv`

## Schema and Notes

### Generation Data Files
- Columns: `DATE_TIME, PLANT_ID, SOURCE_KEY, DC_POWER, AC_POWER, DAILY_YIELD, TOTAL_YIELD`
- `SOURCE_KEY`: Inverter identifier (22 inverters per plant).
- `DC_POWER` and `AC_POWER`: Power in kW. (Note: Plant 1 DC power is reported at ~10x AC power).
- `DAILY_YIELD` and `TOTAL_YIELD`: Cumulative energy in kWh.

### Weather Sensor Data Files
- Columns: `DATE_TIME, PLANT_ID, SOURCE_KEY, AMBIENT_TEMPERATURE, MODULE_TEMPERATURE, IRRADIATION`
- `SOURCE_KEY`: Sensor identifier (1 plant-level sensor shared across all 22 inverters).
- `AMBIENT_TEMPERATURE` and `MODULE_TEMPERATURE`: Degrees Celsius (°C).
- `IRRADIATION`: kW/m² (daily maximum ~1.0 - 1.2 kW/m²).

## Parsing Rules
- **Plant 1 Generation Data** uses day-first formatting (e.g. `15-05-2020 00:00`).
- The remaining files use ISO-style timestamps (e.g. `2020-05-15 00:00:00`).
- Parse explicitly with format strings; assert zero parse discrepancies.
- Never edit raw CSV files directly.

