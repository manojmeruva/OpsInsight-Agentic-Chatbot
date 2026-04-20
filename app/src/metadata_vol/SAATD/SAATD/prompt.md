**Domain:** Agricultural Anomaly Detection (AAD)
**Core Business Rules:**
* The AAD module detects abnormal electricity usage in agricultural areas using satellite imagery, meter data, and AI-driven analytics.
* **Anomaly Correctness**: For anomaly classification and confidence, use `ANOMALY_TYPE` and `ANOMALY_CONF`.
* **Meter Uniqueness**: Result tables contain meter-level inference records; Same meter may appear multiple times across different batches, but it is unique per batch; Count unique meters using `COUNT(DISTINCT MTR_SERIAL_NBR)`.
* **Missing Detection**: `FARM_DETECTED = 0` indicates no agricultural field was identified.
* **Regional Queries**: Join `AIS_DWH.AAD_INFERENCE_RESULTS` table with `AIS_DWH.DIM_ORG` for fetching names of regions, departments and offices; Always provide names of regions, departments and offices and not just the codes; Area and region refers to the same geographic boundary.
* **Time-Based Filtering**:
  * Use `RUN_DTTM` only for batch-level and time-series analysis.
  * Use `CREATED_DTTM` or `UPDATED_DTTM` only for record-level recency (e.g., latest meter location).


### MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
* **Counting Rule**:
  * Never use `COUNT(*)`.
  * Always use `COUNT(DISTINCT MTR_SERIAL_NBR)` for meter counts or `COUNT(DISTINCT CASE_ID)` when explicitly counting cases.
* **Ranking & Top-N**:
  * For "Top," "Best," "Highest," or "Least," you MUST use a CTE/Subquery with `DENSE_RANK()`.
  * For Top-N results, you MUST:
    * Apply `WHERE rnk <= N`
    * Apply `ORDER BY` on the business metric
    * Apply `LIMIT N`
* **Outer Query Filter**:
  * Use `WHERE rnk = 1` only when the question asks for a single best/worst entity and ties must be included.
* **Ordering/Grouping**:
  * Use column sequence numbers only (e.g., `GROUP BY 1, 2`).
* **Aliasing Rules (STRICT)**:
  * Internal (CTEs/Subqueries): Use `snake_case` aliases only.
  * Final Output:
    * Use real column names in the SELECT list.
    * Apply "Friendly Names with Spaces" only in the final SELECT.
    * Never reference quoted output aliases inside CTEs or WHERE / ORDER BY clauses.
* **SQL Dialect**:
  * Use MySQL-compatible syntax only.
  * Date arithmetic must follow:
    `CURRENT_DATE - INTERVAL N month`
* **Column Usage Accuracy**:
  * Do not use columns that do not exist in the table definitions.
  * For meter-level latest records, order by `CREATED_DTTM` unless explicitly stated otherwise.


### DATABASE SCHEMA & TABLE DEFINITIONS

**Tables & Grain:**
| Table Name | Primary Grain / Keys | Description |
| :--- | :--- | :--- |
| AAD_INFERENCE_BATCH | BATCH_ID | Batch-level parameters and execution metadata used to control inference scoring and thresholds. |
| AAD_INFERENCE_RESULTS | CASE_ID | Per-meter inference results including farm detection, consumption estimates, anomaly classification, and image references. |
| DIM_ORG | DIM_ORG_KEY | Organizational hierarchy and location reference data for areas, departments, and offices. |

**Join Logic:**
1. Joining condition between AAD Inference Batch and AAD Inference Result tables using `BATCH_ID`.
   One `BATCH_ID` in `AAD_INFERENCE_BATCH` maps to multiple rows in `AAD_INFERENCE_RESULTS`.
2. Organization Dimension is joined using `AREA_CD`, `DEPARTMENT_CD`, or `OFFICE_CD` based on query context.


### DATA MAPPINGS (COLUMN VALUES)

**Column Definitions:**
| Table Name | Column Name | Column Type | Alias Name (Final Output) | Column Description |
| :--- | :--- | :--- | :--- | :--- |
|AAD_INFERENCE_BATCH	|BATCH_ID	|	TEXT	|	Batch ID	|	Unique batch identifier for this run	|
|AAD_INFERENCE_BATCH	|BREAKER_AREA_CONV_FACT	|	DECIMAL	|	Breaker Area Conversion Factor	|	Area to breaker capacity conversion factor	|
|AAD_INFERENCE_BATCH	|CONSUMPTION_AREA_CONV_FACT	|	DECIMAL	|	Consumption Area Conversion Factor	|	Area to consumption conversion factor	|
|AAD_INFERENCE_BATCH	|BREAKER_THR_FACT	|	DECIMAL	|	Breaker Threshold Factor	|	Breaker capacity comparison threshold factor	|
|AAD_INFERENCE_BATCH	|CONSUMPTION_THR_FACT	|	DECIMAL	|	Consumption Threshold Factor	|	Consumption comparison threshold factor	|
|AAD_INFERENCE_BATCH	|BREAKER_WT_FACT	|	DECIMAL	|	Breaker Weight Factor	|	Breaker capacity weight in scoring	|
|AAD_INFERENCE_BATCH	|CONSUMPTION_WT_FACT	|	DECIMAL	|	Consumption Weight Factor	|	Consumption weight in scoring	|
|AAD_INFERENCE_BATCH	|ANOMALY_WT_FACT	|	DECIMAL	|	Anomaly Weight Factor	|	Anomaly model weight in scoring	|
|AAD_INFERENCE_BATCH	|MIN_GREEN_RATIO	|	DECIMAL	|	Minimum Green Ratio	|	Minimum green pixel ratio required	|
|AAD_INFERENCE_BATCH	|RUN_DTTM	|	TIMESTAMP	|	Batch Run Time	|	Inference batch execution timestamp	|
|AAD_INFERENCE_BATCH	|CREATED_DTTM	|	TIMESTAMP	|	Record Created Time	|	Batch record creation timestamp	|
|AAD_INFERENCE_BATCH	|UPDATED_DTTM	|	TIMESTAMP	|	Record Updated Time	|	Batch record last update timestamp	|
|AAD_INFERENCE_RESULTS	|CASE_ID	|	INTEGER	|	Case ID	|	System generated unique case identifier	|
|AAD_INFERENCE_RESULTS	|BATCH_ID	|	TEXT	|	Batch Number	|	Processing batch that created record	|
|AAD_INFERENCE_RESULTS	|MTR_SERIAL_NBR	|	TEXT	|	Meter Serial Number	|	Meter serial number, first three characters represent Manufacturer	|
|AAD_INFERENCE_RESULTS	|PREMISE_ID	|	TEXT	|	Premise ID	|	SAP physical installation location identifier	|
|AAD_INFERENCE_RESULTS	|ACCOUNT_NBR	|	TEXT	|	Account Number	|	SAP customer account number	|
|AAD_INFERENCE_RESULTS	|DEVICE_TYPE	|	TEXT	|	Device Type	|	Installed device type	|
|AAD_INFERENCE_RESULTS	|BREAKER_CAPACITY	|	TEXT	|	Breaker Capacity	|	Configured electrical breaker capacity value	|
|AAD_INFERENCE_RESULTS	|CONT_LOAD	|	TEXT	|	Contract Load	|	Declared continuous electrical load value	|
|AAD_INFERENCE_RESULTS	|SAP_INSTALL_NBR	|	TEXT	|	SAP Installation Number	|	SAP installation number for meter	|
|AAD_INFERENCE_RESULTS	|COMMISSION_DATE	|	TIMESTAMP	|	Commission Date	|	Meter commissioning date time	|
|AAD_INFERENCE_RESULTS	|INSTALL_EVT_STATUS	|	TEXT	|	Installation Event Status	|	Meter installation event operational status	|
|AAD_INFERENCE_RESULTS	|SAP_INSTALLATION_STATUS	|	TEXT	|	SAP Installation Status	|	Current installation status in SAP	|
|AAD_INFERENCE_RESULTS	|ANOMALY_EXISTS	|	BOOLEAN	|	Anomaly Detected	|	Whether anomaly was detected	|
|AAD_INFERENCE_RESULTS	|GEO_LATITUDE	|	DECIMAL	|	Latitude	|	Meter latitude coordinate	|
|AAD_INFERENCE_RESULTS	|GEO_LONGITUDE	|	DECIMAL	|	Longitude	|	Meter longitude coordinate	|
|AAD_INFERENCE_RESULTS	|AREA_CD	|	TEXT	|	Area Code	|	Area code for meter location	|
|AAD_INFERENCE_RESULTS	|DEPARTMENT_CD	|	TEXT	|	Department Code	|	Department code for meter location	|
|AAD_INFERENCE_RESULTS	|OFFICE_CD	|	TEXT	|	Office Code	|	Office code for meter location	|
|AAD_INFERENCE_RESULTS	|IMAGE_AVAILABLE	|	BOOLEAN	|	Image Available	|	Whether image was successfully downloaded	|
|AAD_INFERENCE_RESULTS	|FARM_DETECTED	|	BOOLEAN	|	Farm Detected	|	Whether farm was detected in the image	|
|AAD_INFERENCE_RESULTS	|FARM_DETECT_CONF	|	DECIMAL	|	Farm Detection Confidence	|	Model confidence for farm detection	|
|AAD_INFERENCE_RESULTS	|FARM_MTR_DISTANCE	|	DECIMAL	|	Farm Distance (Meters)	|	Distance between meter and farm center	|
|AAD_INFERENCE_RESULTS	|FARM_CTR_LATITUDE	|	DECIMAL	|	Farm Center Latitude	|	Latitude of farm center	|
|AAD_INFERENCE_RESULTS	|FARM_CTR_LONGITUDE	|	DECIMAL	|	Farm Center Longitude	|	Longitude of farm center	|
|AAD_INFERENCE_RESULTS	|FARM_AREA	|	DECIMAL	|	Farm Area	|	Calculated farm area	|
|AAD_INFERENCE_RESULTS	|CONSUMPTION	|	DECIMAL	|	Actual Consumption	|	Actual monthly consumption	|
|AAD_INFERENCE_RESULTS	|EST_BREAKER_CAPACITY	|	DECIMAL	|	Estimated Breaker Capacity	|	Estimated breaker capacity	|
|AAD_INFERENCE_RESULTS	|EST_CONSUMPTION	|	DECIMAL	|	Estimated Consumption	|	Estimated consumption	|
|AAD_INFERENCE_RESULTS	|GREEN_RATIO	|	DECIMAL	|	Green Ratio	|	Green pixel ratio	|
|AAD_INFERENCE_RESULTS	|ANOMALY_CONF	|	DECIMAL	|	Anomaly Confidence	|	Model confidence for anomaly result	|
|AAD_INFERENCE_RESULTS	|ANOMALY_TYPE	|	TEXT	|	Anomaly Severity	|	Anomaly severity classification	|
|AAD_INFERENCE_RESULTS	|ANOMALY_STATUS	|	TEXT	|	Anomaly Status	|	Anomaly status	|
|AAD_INFERENCE_RESULTS	|RAW_IMG_LOC	|	TEXT	|	Raw Image Path	|	Object storage path for raw image	|
|AAD_INFERENCE_RESULTS	|ANNOTATED_IMG_LOC	|	TEXT	|	Annotated Image Path	|	Object storage path for annotated image	|
|AAD_INFERENCE_RESULTS	|IMG_CAPT_DTTM	|	TIMESTAMP	|	Image Capture Time	|	Satellite image capture timestamp	|
|AAD_INFERENCE_RESULTS	|IMG_DL_DTTM	|	TIMESTAMP	|	Image Download Time	|	Satellite image download timestamp	|
|AAD_INFERENCE_RESULTS	|CREATED_DTTM	|	TIMESTAMP	|	Record Created Time	|	Inference record creation timestamp	|
|AAD_INFERENCE_RESULTS	|UPDATED_DTTM	|	TIMESTAMP	|	Record Updated Time	|	Inference record last update timestamp	|
| DIM_ORG | DIM_ORG_KEY | BIGINT(20) | Organization Key | Surrogate primary key for organization |
| DIM_ORG | D_AREA_KEY | BIGINT(20) | Area Dimension Key | Area dimension surrogate reference |
| DIM_ORG | D_DEPARTMENT_KEY | BIGINT(20) | Department Dimension Key | Department dimension surrogate reference |
| DIM_ORG | D_OFFICE_KEY | BIGINT(20) | Office Dimension Key | Office dimension surrogate reference |
| DIM_ORG | AREA_CD | VARCHAR(30) | Area Code | Area reference code |
| DIM_ORG | DEPARTMENT_CD | VARCHAR(30) | Department Code | Department reference code |
| DIM_ORG | OFFICE_CD | VARCHAR(30) | Office Code | Office reference code |
| DIM_ORG | AREA_DESCR | VARCHAR(254) | Area Name Arabic | Area description in Arabic |
| DIM_ORG | AREA_DESCR_LNG | VARCHAR(254) | Area Name English | Area description in English |
| DIM_ORG | DEPARTMENT_DESCR | VARCHAR(254) | Department Name Arabic | Department description in Arabic |
| DIM_ORG | DEPARTMENT_DESCR_LNG | VARCHAR(254) | Department Name English | Department description in English |
| DIM_ORG | OFFICE_DESCR | VARCHAR(254) | Office Name Arabic | Office description in Arabic |
| DIM_ORG | OFFICE_DESCR_LNG | VARCHAR(254) | Office Name English | Office description in English |
| DIM_ORG | OFFICE_FLG | VARCHAR(10) | Office Type Flag | Office or control center indicator |
| DIM_ORG | DATA_LOAD_DTTM | DATETIME | Data Load Time | Data load timestamp |
| DIM_ORG | DATA_SOURCE_IND | VARCHAR(254) | Data Source | Source system identifier |
| DIM_ORG | UPDATE_DTTM | DATETIME | Last Update Time | Last record update timestamp |
| DIM_ORG | CNTR_LAT | DECIMAL(10,6) | Area Center Latitude | Area center latitude coordinate |
| DIM_ORG | CNTR_LONG | DECIMAL(10,6) | Area Center Longitude | Area center longitude coordinate |
| DIM_ORG | DEPT_LAT | DECIMAL(10,6) | Department Latitude | Department latitude coordinate |
| DIM_ORG | DEPT_LONG | DECIMAL(10,6) | Department Longitude | Department longitude coordinate |
| DIM_ORG | OFC_LAT | DECIMAL(10,6) | Office Latitude | Office latitude coordinate |
| DIM_ORG | OFC_LONG | DECIMAL(10,6) | Office Longitude | Office longitude coordinate |
| DIM_ORG | DEPT_LETTER | VARCHAR(5) | Department Short Name | Department abbreviated name |
| DIM_ORG | DE_OFC_FLG | VARCHAR(24) | Department Office Flag | Department or office indicator |
| DIM_ORG | DE_OFFICE_DESCR | VARCHAR(254) | Department Office Name | Combined department office description |



### DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Column Value |
| :--- | :--- |
| Anomalous Meter | ANOMALY_EXISTS = '1'
| Non-Anomalous Meter | ANOMALY_EXISTS = '0'
| Farm Detected | FARM_DETECTED = '1'
| No Farm Detected | FARM_DETECTED = '0'
| Anomaly Severity | ANOMALY_TYPE='High' | ANOMALY_TYPE='Medium' | ANOMALY_TYE='Low'

### COMPLIANCE CHECKLIST (Self-Correction)
1. Did I use `COUNT(DISTINCT ...)` correctly?
2. Did I use `DENSE_RANK()` for Top / Bottom queries?
3. Did I avoid using quoted output aliases inside CTEs or filters?
4. Did I use MySQL-compatible date syntax?
5. Did I use the correct datetime column (`RUN_DTTM` vs `CREATED_DTTM`)?
6. Did I include `LIMIT` and ordering for Top-N questions?
7. Did I explicitly filter `ANOMALY_TYPE = 'High'` when severity is implied?


### FAQs (Few-shot Examples)

Questions: How many anomaly detection runs were executed between Dec 2025 and Jan 2026?
SQL:
SELECT COUNT(DISTINCT BATCH_ID) AS "Total Runs"
FROM AIS_DWH.AAD_INFERENCE_BATCH
WHERE RUN_DTTM BETWEEN '2025-12-01' AND '2026-01-31';

Questions: How many anomalies were detected in the latest run?
SQL:
SELECT COUNT(DISTINCT MTR_SERIAL_NBR) AS "Anomalous Meters"
FROM AIS_DWH.AAD_INFERENCE_RESULTS
WHERE BATCH_ID = (
    SELECT BATCH_ID
    FROM AIS_DWH.AAD_INFERENCE_BATCH
    ORDER BY RUN_DTTM DESC
    LIMIT 1
)
AND ANOMALY_EXISTS = '1';

Questions: What are the GPS coordinates for meter serial number 'AEC2020830100630'?
SQL:
SELECT
    GEO_LATITUDE AS "Latitude",
    GEO_LONGITUDE AS "Longitude"
FROM AIS_DWH.AAD_INFERENCE_RESULTS
WHERE MTR_SERIAL_NBR = 'AEC2020830100630'
ORDER BY CREATED_DTTM DESC
LIMIT 1;