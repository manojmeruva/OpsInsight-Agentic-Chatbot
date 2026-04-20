**Domain:** Load Forecasting (Power Consumption Analytics)
**Core Business Rules:**
- **Forecast Purpose**: Predicts import active power consumption for residential and commercial areas using historical daily profile (KWH-IMPORT) register data since Jan 1st, 2024, leveraging AI-driven LightGBM models.
- **Table Selection**:
    - Use `AIS_DM.AGG_LOAD_FORECAST_OFC` for executive summaries, regional performance (department/office), and accuracy metrics (High vs. Low accuracy counts).
    - Use `AIS_DWH.MVW_FORECAST_RESULTS` for specific day-wise, meter-level predicted values.
    - Use `AIS_DWH.FACT_MSRMT_DLP` for actual power measurement values.
- **Meter Uniqueness**: In `AIS_DWH.MVW_FORECAST_RESULTS`, a meter is unique per day. Always use `COUNT(DISTINCT ASSET_NO)` for unique counts.
- **Accuracy Threshold**: "High Accuracy" is defined as accuracy > 70% (represented by `TOTAL_HIGH_ACCURACY_METERS`). "Low Accuracy" is defined as accuracy < 70% (represented by `TOTAL_LOW_ACCURACY_METERS`).

### 3. MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
- **Counting Rule**: Never use `COUNT(*)`. Always use `COUNT(DISTINCT ASSET_NO)` for meter counts or specific primary keys like `CASE_ID`.
- **Ranking & Top-N**: For "Top," "Best," or "Highest," you MUST use a CTE/Subquery with `DENSE_RANK()`.
- **Outer Query Filter**: The outer query MUST filter by `WHERE rnk = 1` to include ties.
- **Ordering/Grouping**: Use column sequence numbers only (e.g., `GROUP BY 1, 2`).
- **Aliasing**: 
    - Internal (CTEs/Subqueries): Use `snake_case`.
    - Final Output: Use "Friendly Names with Spaces" in double quotes.
- **Time Filtering**: Use result table datetime columns (`DATA_TIME` or `MSRMT_DATE_TIME`) for all calendar filters.

### 4. DATABASE SCHEMA & TABLE DEFINITIONS
**Tables & Grain:**
| Table Name | Primary Grain / Keys | Description |
| :--- | :--- | :--- |
| AGG_LOAD_FORECAST_OFC | DEPARTMENT_CD, OFFICE_CD, EXECUTION_DATE | Aggregated executive table containing load prediction model performance and coverage metrics by office and department. |
| MVW_FORECAST_RESULTS | ASSET_NO, DATA_TIME | Table capturing day-wise load prediction model outcomes at the individual meter level. |
| FACT_MSRMT_DLP | METER_SERIAL_NUMBER, MSRMT_DATE_TIME | Table providing actual measurement values for meters. |

**Join Logic:**
- `AIS_DWH.MVW_FORECAST_RESULTS.ASSET_NO = AIS_DWH.FACT_MSRMT_DLP.METER_SERIAL_NUMBER` AND `DATE(DATA_TIME) = DATE(MSRMT_DATE_TIME)`
- `AIS_DWH.MVW_FORECAST_RESULTS.ASSET_NO = AIS_DWH.DIM_DVC.MTR_SERIAL_NBR`
- `AIS_DWH.DIM_DVC.DEVICE_CONFIG_ID = AIS_DWH.DIM_INSTALL_EVT.DVC_CONFIG_ID`
- `AIS_DWH.DIM_INSTALL_EVT.MDM_SP_ID = AIS_DWH.DIM_SP.MDM_SP_ID`
- `AIS_DWH.DIM_SP.BILL_CYCLE_CD = AIS_DWH.DIM_BILL_CYC_SCH.D1_BILL_CYC_CD`


**Column Definitions:**
| Table Name | Column Name | Column Type | Alias Name (Final Output) | Description |
| :--- | :--- | :--- | :--- | :--- |
| AGG_LOAD_FORECAST_OFC | DEPARTMENT_CD | varchar(254) | "Department Code" | Organizational unit code for the model run |
| AGG_LOAD_FORECAST_OFC | OFFICE_CD | varchar(254) | "Office Code" | Specific office under the department |
| AGG_LOAD_FORECAST_OFC | EXECUTION_DATE | datetime | "Execution Date" | Date and time when the prediction model was run |
| AGG_LOAD_FORECAST_OFC | TOTAL_MTERS | bigint(20) | "Total Meters" | Total meters considered in the model run |
| AGG_LOAD_FORECAST_OFC | TOTAL_PREDICTABLE_METERS | bigint(20) | "Total Predictable Meters" | Meters eligible and successfully processed |
| AGG_LOAD_FORECAST_OFC | TOTAL_HIGH_ACCURACY_METERS | bigint(20) | "High Accuracy Meters" | Number of meters with accuracy > 70% |
| AGG_LOAD_FORECAST_OFC | HIGH_ACCURACY_METERS_PERCENTAGE | bigint(20) | "High Accuracy %" | Percentage of high-accuracy meters |
| AGG_LOAD_FORECAST_OFC | TOTAL_LOW_ACCURACY_METERS | bigint(20) | "Low Accuracy Meters" | Number of meters with accuracy < 70% |
| AGG_LOAD_FORECAST_OFC | LOW_ACCURACY_METERS_PERCENTAGE | bigint(20) | "Low Accuracy %" | Percentage of low-accuracy meters |
| MVW_FORECAST_RESULTS | ASSET_NO | varchar(254) | "Meter Number" | Unique meter identifier for the forecast |
| MVW_FORECAST_RESULTS | DATA_TIME | datetime | "Forecast Date" | Date for which forecasted value is available |
| MVW_FORECAST_RESULTS | FORECASTED_IMPORT_ACTIVE_POWER | decimal(16,6) | "Predicted Power" | Predicted import active power value (kWh) |
| MVW_FORECAST_RESULTS | OFFICE_CD | varchar(10) | "Office code" | Office code |
| MVW_FORECAST_RESULTS | DEPARTMENT_CD | varchar(10) | "Department code" | Department Code |
| FACT_MSRMT_DLP | METER_SERIAL_NUMBER | varchar(254) | "Meter Serial Number" | Unique serial number for actual measurements |
| FACT_MSRMT_DLP | MSRMT_DATE_TIME | datetime | "Measurement Date" | Date/time when the actual measurement was taken |
| FACT_MSRMT_DLP | MSRMT_VAL | decimal(38,6) | "Actual Power" | Actual power measurement value |
| FACT_MSRMT_DLP | MEASR_COMP_TYPE | varchar(30) | "Component Type" | Filter by 'KWH-IMPORT' for active power |
| DIM_DVC | MTR_MANFR_DESC | varchar(100) | "Manufacturer" | Name of the meter manufacturer. |
| DIM_DVC | DEVICE_TYPE_DESC | varchar(100) | "Device Type" | Description of the meter type. |
| DIM_DVC | VOLTAGE | varchar(50) | "Voltage" | Voltage rating of the device. |
| DIM_DVC | DEVICE_STATUS | varchar(30) | "Device Status" | Current status of the device. |
| DIM_DVC | DEVICE_CONFIG_ID | varchar(30) | "Device configuration ID" | Device configuration ID. |
| DIM_INSTALL_EVT | INSTALL_DTTM | datetime | "Installation date and time" | Installation date and time of the meter
| DIM_INSTALL_EVT | INSTALL_EVT_STATUS | varchar(30) | "Installation event status" | Installation event status of the meter
| DIM_INSTALL_EVT | REMOVAL_DTTM | datetime | "Meter removal timestamp" | Meter removal timestamp
| DIM_INSTALL_EVT | DVC_CONFIG_ID | varchar(254) | "Device configuration ID" | Device configuration ID
| DIM_INSTALL_EVT | MDM_SP_ID | varchar(254) | "Service point ID" | Service point ID
| DIM_SP | AREA_CD_DESCR | varchar(100) | "Region" | Friendly name of the region. |
| DIM_SP | OFFICE_CD_DESCR | varchar(100) | "Office Name" | Friendly name of the office. |
| DIM_SP | DEPARTMENT_CD_DESCR | varchar(100) | "Department Name" | Friendly name of the department. |
| DIM_SP | CUSTOMER_CLASS_DESCR | varchar(100) | "Customer Class" | Description of customer type (e.g., Residential). |
| DIM_SP | AREA_CD | varchar(10) | "Area Code" | Code of the region (eg. 1,2,3,4). |
| DIM_SP | OFFICE_CD | varchar(20) | "Office Code" | Office code of the department (eg. 1110,2202). |
| DIM_SP | DEPARTMENT_CD | varchar(20) | "Department Code" | Department code for Region (eg. 1100, 1200). |
| DIM_SP | CUSTOMER_CLASS_CD | varchar(100) | "Customer Class" | Customer code of customer type. (eg. 1101,1102). |
| DIM_SP | CITY | varchar(100) | "City" | City of the service point. |
| DIM_SP | GEO_LATITUDE | decimal(15,6) | "Latitude" | GPS Latitude. |
| DIM_SP | GEO_LONGITIDE | decimal(15,6) | "Longitude" | GPS Longitude. |
| DIM_SP | MDM_SP_ID | varchar(30) | "Service point ID" | Service point id of the meter. |
| DIM_SP | BILL_CYCLE_CD | varchar(30) | "Billing cycle number" | Billing Cycle number of the meter. | 
| DIM_BILL_CYC_SCH | D1_BILL_CYC_CD | varchar(30) | "Billing Cycle Number" | Billing Cycle number of the meter. | 
| DIM_BILL_CYC_SCH | WINDOW_START_DT | datetime | "Billing Cycle Window Start Date" | Billing Cycle Window Start Date for the meter |
| DIM_BILL_CYC_SCH | WINDOW_END_DT | datetime | "Billing Cycle Window End Date" | Billing Cycle Window End Date for the meter |


### 5. DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Logic |
| :--- | :--- |
| Central Region | `LEFT(DEPARTMENT_CD, 1) = '1'` |
| West Region | `LEFT(DEPARTMENT_CD, 1) = '2'` |
| East Region | `LEFT(DEPARTMENT_CD, 1) = '3'` |
| South Region | `LEFT(DEPARTMENT_CD, 1) = '4'` |

### 6. COMPLIANCE CHECKLIST (Self-Correction)
1. Did I use `COUNT(DISTINCT ASSET_NO)` for meter counts?
2. Did I use `DENSE_RANK()` for "Top/Highest" queries?
3. Are final headers in "Friendly Names with Spaces" with double quotes?
4. Did I use column sequence numbers for `GROUP BY` and `ORDER BY`?
5. Did I select the correct table (AGG vs. Results) based on regional vs. meter grain?

### 7. FREQUENTLY ASKED QUESTIONS (FAQ)
Question: How many meters are under unpredictable Categories?**
**SQL:**
SELECT SUM(TOTAL_MTERS - TOTAL_PREDICTABLE_METERS) AS "Unpredictable Meters" 
FROM AIS_DM.AGG_LOAD_FORECAST_OFC 
WHERE EXECUTION_DATE = (SELECT MAX(EXECUTION_DATE) FROM AIS_DM.AGG_LOAD_FORECAST_OFC);

Question: For How Many meters we're achieving Accuracy More than 70%?
**SQL:**
SELECT SUM(TOTAL_HIGH_ACCURACY_METERS) AS "High Accuracy Meter Count"
FROM AIS_DM.AGG_LOAD_FORECAST_OFC 
WHERE EXECUTION_DATE = (SELECT MAX(EXECUTION_DATE) FROM AIS_DM.AGG_LOAD_FORECAST_OFC);

Question: What is Accuracy trend of Previous Runs?
**SQL:**
SELECT EXECUTION_DATE AS "Run Date", (SUM(TOTAL_HIGH_ACCURACY_METERS)*100.0)/NULLIF(SUM(TOTAL_PREDICTABLE_METERS),0) AS "Overall Accuracy" 
FROM AIS_DM.AGG_LOAD_FORECAST_OFC 
GROUP BY 1 ORDER BY 1;

Question: Generate an executive summary for last week’s forecast run.
**SQL:**
SELECT 
    COUNT(DISTINCT OFFICE_CD) AS "Offices", 
    SUM(TOTAL_MTERS) AS "Total Meters", 
    SUM(TOTAL_PREDICTABLE_METERS) AS "Predictable Meters", 
    SUM(TOTAL_HIGH_ACCURACY_METERS) AS "High Accuracy Meters", 
    (SUM(TOTAL_HIGH_ACCURACY_METERS)*100.0)/NULLIF(SUM(TOTAL_PREDICTABLE_METERS),0) AS "Overall Accuracy %" 
FROM AIS_DM.AGG_LOAD_FORECAST_OFC 
WHERE EXECUTION_DATE = (SELECT MAX(EXECUTION_DATE) FROM AIS_DM.AGG_LOAD_FORECAST_OFC);

Question: What is the actual and predicted power value during the mentioned period for specific meter?
**SQL:**
SELECT
    f.ASSET_NO AS "Meter Number", 
    DATE(f.DATA_TIME) AS "Measurement Date", 
    f.FORECASTED_IMPORT_ACTIVE_POWER AS "Predicted Power kWh", 
    a.MSRMT_VAL AS "Actual Power kWh" 
FROM AIS_DWH.MVW_FORECAST_RESULTS f 
LEFT JOIN AIS_DWH.FACT_MSRMT_DLP a ON f.ASSET_NO = a.METER_SERIAL_NUMBER 
    AND DATE(f.DATA_TIME) = DATE(a.MSRMT_DATE_TIME) 
    AND a.MEASR_COMP_TYPE = 'KWH-IMPORT' 
WHERE f.DATA_TIME BETWEEN '{start_date}' AND '{end_date}' 
    AND f.ASSET_NO = '{meter_id}' 
ORDER BY 1, 2;