**Domain:** Load Disaggregation
**Core Business Rules:**
- The Load Disaggregation module disaggregates the load into 5 categories on the weekly basis: HVAC, Cooking, Cleaning, Entertainment and Others. It disaggregates residential meters by using daily profile (KWH-IMPORT) register and Load Profile data, leveraging signature-based AI-driven analytics.
- Signature-based algorithms leverage energy consumption patterns, weather conditions, and dwelling characteristics to uncover real customer behavior.
- **Disaggregation Results**: For Disaggregation Results/Values, refer to the table `AIS_DM.FACT_ED_SUMMARY`.
- **Measurement Data**: For DP and LP Data Values, refer to the table `AIS_DWH.FACT_MSRMT_DLP`.
- **Meter Uniqueness**: Result table `AIS_DM.FACT_ED_SUMMARY` contains meter-level records. The same meter may appear multiple times across different weeks, but it is unique per week. **Mandatory**: Always use `COUNT(DISTINCT MTR_SERIAL_NBR)` for unique meter counts.
- **Regional/Aggregated Level Meter data availability Queries**: Use `AIS_DM.AGG_LOAD_DISAGG_OFC` for total meters, data availability (LP, LPDP, Zero Consumption), and count of how much meters we are able to disaggregate at the aggregate level (office/department/region).
- **Time-Based Filtering**: Always use the datetime column `START_DATE` from the `AIS_DM.FACT_ED_SUMMARY` table for any time-series analysis of meter level results.

**Category and Appliance Mappings:**
- **HVAC**: Air conditioners (window, split, central), Furnaces, Heaters, Ventilation Fans, Thermostats
- **Cooking**: Refrigerators/freezers, Ovens, Microwaves, Cooktops, Dishwashers, Coffee Makers
- **Cleaning**: Washing Machines, Dryers, Vacuum cleaners, Irons
- **Entertainment**: Televisions, Gaming Consoles, Sound Systems, Computers, Printers
- **Others**: Lighting, Pool Pumps, Small kitchen appliances, Alarm systems, Miscellaneous electronics

### 3. MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
- **Counting Rule**: Never use `COUNT(*)`. Always use `COUNT(DISTINCT MTR_SERIAL_NBR)` for meter counts or specific primary keys like `CASE_ID`.
- **Ranking & Top-N**: For "Top," "Best," or "Highest," you MUST use a CTE/Subquery with `DENSE_RANK()`.
- **Outer Query Filter**: The outer query MUST filter by `WHERE rnk = 1` to include ties.
- **Ordering/Grouping**: Use column sequence numbers only (e.g., `GROUP BY 1, 2`).
- **Aliasing**: 
    - Internal (CTEs/Subqueries): Use `snake_case`.
    - Final Output: Use "Friendly Names with Spaces" in double quotes.
- **Time Filtering**: Use result table datetime columns for all calendar filters.

### 4. DATABASE SCHEMA & TABLE DEFINITIONS

**Tables & Grain:**
| Table Name | Primary Grain / Keys | Description |
| :--- | :--- | :--- |
| AIS_DM.FACT_ED_SUMMARY | ED_KEY | Fact table storing appliance-level energy disaggregation results per meter. Grain: 1 record per Meter per Appliance Category per Week. |
| AIS_DM.AGG_LOAD_DISAGG_OFC | DEPARTMENT_CD, OFFICE_CD, START_DATE | Aggregated table providing total meter counts and data health metrics at the office/department level. |
| AIS_DWH.DIM_DVC | MDM_DEVICE_KEY | Device dimension table containing smart meter details (Serial No, Manufacturer, Status). |
| AIS_DWH.DIM_INSTALL_EVT | INSTALL_EVT_KEY | Installation event dimension tracking meter installation/removal history and linking devices to service points. |
| AIS_DWH.DIM_SP | SERVICE_POINT_KEY | Service point (consumer) dimension containing geographical and organizational details. |

**Column Definitions:**
| Table Name | Column Name | Column Type | Alias Name (Final Output) | Column Description |
| :--- | :--- | :--- | :--- | :--- |
| FACT_ED_SUMMARY | MTR_SERIAL_NBR | varchar(254) | "Meter Serial Number" | Unique identifier for the physical meter. |
| FACT_ED_SUMMARY | CATEGORY | varchar(50) | "Appliance Category" | Category (HVAC, Cooking, Cleaning, Entertainment, Others). |
| FACT_ED_SUMMARY | ACTUAL_CONSUMPTION | decimal(16,6) | "Consumption (kWh)" | Total disaggregated energy for the category. |
| FACT_ED_SUMMARY | PER_VALUE | decimal(16,6) | "Consumption (%)" | Percentage contribution of the appliance to total load. |
| FACT_ED_SUMMARY | START_DATE | datetime | "Start Date" | Start of the disaggregation window. |
| FACT_ED_SUMMARY | END_DATE | datetime | "End Date" | End of the disaggregation window. |
| AGG_LOAD_DISAGG_OFC | TOTAL_MTERS | bigint(20) | "Total Residential Meters" | Total meters considered for disaggregation. |
| AGG_LOAD_DISAGG_OFC | TOTAL_METERS_WITH_LP_DATA | bigint(20) | "Meters with LP Data" | Meters with available Load Profile data. |
| AGG_LOAD_DISAGG_OFC | TOTAL_METERS_WITH_DISAGG | bigint(20) | "Successfully Disaggregated" | Count of meters that passed disaggregation. |
| AGG_LOAD_DISAGG_OFC | TOTAL_METERS_WITH_ZERO_CONSMP | bigint(20) | "Zero Consumption Meters" | Meters showing no consumption in the window. |
| AGG_LOAD_DISAGG_OFC | DEPARTMENT_CD | varchar(254) | "Department code" | Department code. |
| AGG_LOAD_DISAGG_OFC | OFFICE_CD | varchar(254) | "Office code of the department" | Office code present in the department. |
| AGG_LOAD_DISAGG_OFC | EXECUTION_DATE| datetime | "Date and time when the disaggregation job was executed" | The time when we start the process started. |
| AGG_LOAD_DISAGG_OFC | START_DATE | datetime | "Disaggregation period start date" | Start date of the disaggregation period. |
| AGG_LOAD_DISAGG_OFC | END_DATE | datetime | "Disaggregation period end date" | End date of the disaggregation period. |
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


**Join Logic:**
- **AIS_DM.FACT_ED_SUMMARY** joins to **AIS_DWH.DIM_DVC** on `MTR_SERIAL_NBR`.
- **AIS_DWH.DIM_DVC** joins to **AIS_DWH.DIM_INSTALL_EVT** on `DEVICE_CONFIG_ID` = `DVC_CONFIG_ID`.
- **AIS_DWH.DIM_INSTALL_EVT** joins to **AIS_DWH.DIM_SP** on `MDM_SP_ID`.
- **AIS_DM.FACT_ED_SUMMARY** joins to **AIS_DM.AGG_LOAD_DISAGG_OFC** via `START_DATE`, `DEPARTMENT_CD`, and `OFFICE_CD` (indirectly via DIM_SP).

### 5. DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Column Value |
| :--- | :--- |
| HVAC | CATEGORY = 'HVAC' |
| Cooking | CATEGORY = 'Cooking' |
| Cleaning | CATEGORY = 'Cleaning' |
| Entertainment | CATEGORY = 'Entertainment' |
| Others | CATEGORY = 'Others' |

### 6. COMPLIANCE CHECKLIST (Self-Correction)
1. Did I use the mandatory `COUNT(DISTINCT...)` function?
2. Did I use `DENSE_RANK()` for a "Top" query?
3. Are final headers in "Double Quotes with Spaces"?
4. Did I use column sequence numbers for `GROUP BY`?
5. Did I include ties using `WHERE rnk = 1`?

### 7. FINALIZED FAQS
Questions: Plot the % of Meter for which we're able to Disaggregate Region Wise?
**SQL**
SELECT 
    SUBSTR(DEPARTMENT_CD, 1, 1) AS "Region", 
    SUM(TOTAL_METERS_WITH_DISAGG) AS "Disaggregated Meters", 
    SUM(TOTAL_METERS_WITH_LP_DATA) AS "Total Meters with LP Data", 
    ROUND((SUM(TOTAL_METERS_WITH_DISAGG) * 100.0) / NULLIF(SUM(TOTAL_METERS_WITH_LP_DATA), 0), 2) AS "Disaggregation Percentage" 
FROM AIS_DM.AGG_LOAD_DISAGG_OFC 
WHERE EXECUTION_DATE = (SELECT MAX(EXECUTION_DATE) FROM AIS_DM.AGG_LOAD_DISAGG_OFC) 
GROUP BY 1 
ORDER BY 4 DESC;

Questions: Which department has the highest HVAC consumption?
**SQL**
WITH dept_consumption AS (
    SELECT 
        s.DEPARTMENT_CD, 
        SUM(a.ACTUAL_CONSUMPTION) AS total_hvac_cons,
        DENSE_RANK() OVER (ORDER BY SUM(a.ACTUAL_CONSUMPTION) DESC) as rnk
    FROM AIS_DM.FACT_ED_SUMMARY a
    JOIN AIS_DWH.DIM_DVC b ON a.MTR_SERIAL_NBR = b.MTR_SERIAL_NBR
    JOIN AIS_DWH.DIM_INSTALL_EVT i ON b.DEVICE_CONFIG_ID = i.DVC_CONFIG_ID
    JOIN AIS_DWH.DIM_SP s ON s.MDM_SP_ID = i.MDM_SP_ID
    WHERE a.CATEGORY = 'HVAC'
    GROUP BY 1
)
SELECT 
    DEPARTMENT_CD AS "Department Code", 
    total_hvac_cons AS "Total HVAC Consumption" 
FROM dept_consumption 
WHERE rnk = 1;

Questions: What is the Disaggregation of KFM2020560003989 meter for the latest run?
**SQL**
SELECT 
    CATEGORY AS "Appliance Category", 
    SUM(ACTUAL_CONSUMPTION) AS "Consumption" 
FROM AIS_DM.FACT_ED_SUMMARY 
WHERE MTR_SERIAL_NBR = 'KFM2020560003989' 
  AND START_DATE = (SELECT MAX(START_DATE) FROM AIS_DM.FACT_ED_SUMMARY) 
GROUP BY 1 
ORDER BY 2 DESC;

Questions: What is the Disaggregation for METER_ID KFM2020560003989 for Period 1st Dec to 31st Dec?
**SQL**
SELECT 
    CATEGORY AS "Appliance Category", 
    SUM(ACTUAL_CONSUMPTION) AS "Consumption" 
FROM AIS_DM.FACT_ED_SUMMARY 
WHERE MTR_SERIAL_NBR = 'KFM2020560003989' 
  AND START_DATE >= '2025-12-01' 
  AND START_DATE < '2026-01-01' 
GROUP BY 1 
ORDER BY 2 DESC;

Questions: What is Category wise Proportion in % of the METER_ID?
**SQL**
SELECT 
    CATEGORY AS "Appliance Category", 
    (SUM(ACTUAL_CONSUMPTION) * 100.0) / SUM(SUM(ACTUAL_CONSUMPTION)) OVER () AS "Percentage" 
FROM AIS_DM.FACT_ED_SUMMARY 
WHERE MTR_SERIAL_NBR = 'KFM2020560003989' 
GROUP BY 1;

Questions: Assuming Electricity rate is 0.18 SAR/kWh, what is the Category level Consumption in SAR?
**SQL**
SELECT 
    CATEGORY AS "Appliance Category", 
    SUM(ACTUAL_CONSUMPTION) AS "Consumption KWH", 
    SUM(ACTUAL_CONSUMPTION) * 0.18 AS "Consumption SAR" 
FROM AIS_DM.FACT_ED_SUMMARY 
GROUP BY 1 
ORDER BY 3 DESC;