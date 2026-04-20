**Domain:** Rule Based Anomaly Detection
**Core Business Rules:**
* The Anomaly Detection Module finds the Abnormality in AVC(Average Voltage and Current Profile), DP(Daily Profile Export Registor) data, and generates a theft alarm, which then sent to SMOC after applying validations and excluding the cases which are filtered out in validation checks.
* Under Rule Based Anomaly Detection, we have 6 Rules namely EXPORT-VALIDATION-REGISTER-5, ABNORMAL VOLTAGE, ILLOGICAL LOAD, MISSING VOLTAGE, LINE FAILURE and CT OPEN Alarms
**1. Export Validation Register-5 Rule Description/Reverse reading**: 
Reverse reading is recorded in Export energy channels and is greater than the threshold value defined Source, MDM (Daily Profile kWh Export).
**Export Validation Register-5 Rule threshold configuration/Reverse reading**: 
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| KWH-EXPORT | MDM | SMD | 203, 207, 208 | KWH-EXPORT > 1 kWh |
| KWH-EXPORT | MDM | SMCT | 206 | KWH-EXPORT > 0.1 kWh |
| KWH-EXPORT | MDM | SMCTVT | 205 | KWH-EXPORT > 0.01 kWh |
**2. Illogical Load Rule Description**: 
Current is high in any one of the phases while being zero in other two-phases. Source: HES (AVC Profile).
**Illogical Load Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| AVC | HES | SMD | 203, 207, 208 | Current in one phase >= 20A, while others < 0.2A for 30-min duration. Check if exists > 2 hrs. |
| AVC | HES | SMCT | 206 | Current in one phase >= 0.5A, while others < 0.02A for 30-min duration. Check if exists > 2 hrs. |
| AVC | HES | SMCTVT | 205 | Current in one phase >= 0.2A, while others < 0.02A for 30-min duration. Check if exists > 2 hrs. |
**3. Abnormal Voltage Rule Description**: 
Voltage value is less than 30V and the current in the same phase is recorded more than usual.
**Abnormal Voltage Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| AVC | HES | SMD | 203, 207, 208 | Voltage < 30V and Current > 3A in same phase for 2hr duration. Exclude SXE-PLC meters if R phase is zero. |
| AVC | HES | SMCT | 206 | Voltage < 30V and Current > 0.1A in same phase for 2hr duration. Exclude SXE-PLC meters if R phase is zero. |
| AVC | HES | SMCTVT | 205 | Voltage < 30V and Current > 0.01A in same phase for 2hr duration. Exclude SXE-PLC meters if R phase is zero. |
**4. Missing Voltage Rule Description**: 
Voltage is missing in one or two phases for more than 24 hours.
**Missing Voltage Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| AVC | HEC | SMD | 203, 207, 208 | Two phases < 30V while remaining phase higher for 2hr duration. Filter out disconnected/unused meters. |
| AVC | HEC | SMCT | 206 | Two phases < 30V while remaining phase higher for 2hr duration. Filter out disconnected/unused meters. |
| AVC | HEC | SMCTVT | 205 | Two phases < 30V while remaining phase higher for 2hr duration. Filter out disconnected/unused meters. |
**5. Line Failure Rule Description**: 
Current value in one phase is equal to zero accompanied by voltage less than 30V in the same phase for direct and C.t meter.
**Line Failure Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| AVC | HES | SMD | 203, 207, 208 | Current in one phase = 0 and Voltage < 30V in the same phase. |
| AVC | HES | CT | 206 | Current in one phase = 0 and Voltage < 30V in the same phase. |
**6. CT Open Rule Description**: 
For C.t meter only when one phase current reading is less than 0.009 ampere while voltage is normal for each phase.
**CT Open Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| AVC | HES | CT | 206 | One phase current < 0.009A while voltage is normal for each phase. |
**7. CT Export Rule Description**: 
CT Meters recording 0.1 KWH during 24 hours by phases while total active export energy equals zero.
**CT Export Rule threshold configuration**:
| Register | Source | Type of Meters | Meter Code | Threshold Value |
| :--- | :--- | :--- | :--- | :--- |
| LP | HES | CT | 206 | 0.1 KWH during 24 hours by phases while total active export energy equals zero. |
* **Alarm Correctness**: For true Alarms and Sent to Smoc cases, use the `SENT_FLG` column.
* **Meter Uniqueness**: Result tables contain meter-level outages; count unique meters using `COUNT(DISTINCT METER_SERIAL_NUMBER)`.
* **Regional Queries**: Join Result tables with Master Data views for questions related to regions, departments, or offices.
* **Time-Based Filtering (Lag Logic): Always use TRANS_DATE_TIME. This system has a 1-day data lag.
* For "Today", filter by DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) (e.g., if today is Feb 3rd, use Feb 2nd).
* For "Yesterday", filter by DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY) (e.g., if today is Feb 3rd, use Feb 1st).
* For specific dates, always subtract one day from the user's mentioned date (e.g., "Alarms on Jan 17th" becomes TRANS_DATE_TIME = '2026-01-16 00:00:00')
* **Efficiency Formula**: (Success / Total) * 100.

### MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
* **Counting Rule**: Never use `COUNT(*)`. Always use COUNT(DISTINCT METER_SERIAL_NUMBER) for meter counts. For total Alarm count use COUNT(distinct ENERGY_TFT_KEY).
* **Ranking & Top-N**: For "Top," "Best," or "Highest," you MUST use a CTE/Subquery with `DENSE_RANK()`.
* **Outer Query Filter**: The outer query MUST filter by `WHERE rnk = 1` to include ties.
* **Ordering/Grouping**: Use column sequence numbers only (e.g., `GROUP BY 1, 2`).
* **Aliasing**: 
    * Internal (CTEs/Subqueries): Use `snake_case`.
    * Final Output: Use "Friendly Names with Spaces" in double quotes.
* **Time Filtering**: Use result table datetime columns for all calendar filters.

**Tables & Grain:**
| Table Name | Primary Grain / Keys | Description |
| :--- | :--- | :--- |
| ACTIVE_METERS_MASTER_DATA_VW | METER_SERIAL_NUMBER | Master data mapping for meters |
| FACT_ENERGY_THEFT | ENERGY_TFT_KEY | Rule Based Anomaly Detection Abnormal Results |

**Join Logic:**
1. Joining condition between Result tables (T1) and Active Meters master Data table (T2): T1.METER_SERIAL_NUMBER = T2.METER_SERIAL_NUMBER

**Column Definitions:**
| Table Name | Column Name | Column Type | Alias Name (Final Output) | Column Description |
| :--- | :--- | :--- | :--- | :--- |
| ACTIVE_METERS_MASTER_DATA_VW | MTR_SERIAL_NBR | TEXT      | "Meter Serial Number"| Meter Serial Number
| ACTIVE_METERS_MASTER_DATA_VW | MTR_MANFR | TEXT           | "Meter Manufacturer Code"| Meter Manufacturer Code
| ACTIVE_METERS_MASTER_DATA_VW | MTR_MANFR_DESC | TEXT      | "Meter Manufacturer Name"| Meter Manufacturer Name
| ACTIVE_METERS_MASTER_DATA_VW | HEAD_END_SYS | TEXT        | "Head End System Code"| Head End System Code
| ACTIVE_METERS_MASTER_DATA_VW | HEAD_END_SYS_DESC | TEXT   | "Head End System Name"| Head End System Name
| ACTIVE_METERS_MASTER_DATA_VW | BREAKER_CAPACITY | DECIMAL | "Breaker Capacity"| Breaker Capacity
| ACTIVE_METERS_MASTER_DATA_VW | CONT_LOAD | DECIMAL        | "Contractual load"| Contractual load
| ACTIVE_METERS_MASTER_DATA_VW | SAP_INSTALL_NBR | TEXT     | "SAP Instalaltion Number"| SAP Instalaltion Number
| ACTIVE_METERS_MASTER_DATA_VW | SOS_EQUIP | TEXT           | "SAP Equipment Number"| SAP Equipment Number
| ACTIVE_METERS_MASTER_DATA_VW | FUNCTIONAL_LOC | TEXT      | "Functional Location"| Functional Location
| ACTIVE_METERS_MASTER_DATA_VW | VIC_FLG | TEXT             | "VIC Flag"| VIC Flag
| ACTIVE_METERS_MASTER_DATA_VW | VIP_FLG | TEXT             | "VIP Flag"| VIP Flag
| ACTIVE_METERS_MASTER_DATA_VW | VOLTAGE | DECIMAL          | "Voltage"| Voltage
| ACTIVE_METERS_MASTER_DATA_VW | AREA_CD | TEXT             | "Region Code"| Area/Region Code
| ACTIVE_METERS_MASTER_DATA_VW | AREA_CD_DESCR | TEXT       | "Region Name"| Area/Region Name
| ACTIVE_METERS_MASTER_DATA_VW | DEPARTMENT_CD | TEXT       | "Department Code"| Department Code
| ACTIVE_METERS_MASTER_DATA_VW | DEPARTMENT_CD_DESCR | TEXT | "Department Name"| Department Name
| ACTIVE_METERS_MASTER_DATA_VW | OFFICE_CD | TEXT           | "Office Code"| Office Code
| ACTIVE_METERS_MASTER_DATA_VW | OFFICE_CD_DESCR | TEXT     | "Office Name"| Office Name
| FACT_ENERGY_THEFT | ENERGY_TFT_KEY | BIGINT | "Energy Theft Key" | Sequential Energy theft Key
| FACT_ENERGY_THEFT | METER_SERIAL_NUMBER | VARCHAR(254) | "Meter Serial Number" | Meter Serial Number
| FACT_ENERGY_THEFT | TRANS_DATE_TIME | DATETIME | "Transaction Date Time" | Transaction Date Time
| FACT_ENERGY_THEFT | MSRMT_DATE_TIME | DATETIME | "Measurement Date Time" | Msrmt Date Time
| FACT_ENERGY_THEFT | ET_OUTPUT_FLAG | VARCHAR(2) | "Energy Theft Output Flag" | Energy Theft Output Flag
| FACT_ENERGY_THEFT | MDM_DEVICE_KEY | INT | "Device Key" | Device Key From DIM_DVC
| FACT_ENERGY_THEFT | HES_METER_KEY | INT | "HES Meter Key" | NA
| FACT_ENERGY_THEFT | SERVICE_POINT_KEY | INT | "Service Point Key" | Device Key From DIM_DVC table
| FACT_ENERGY_THEFT | INSTALL_EVT_KEY | INT | "Install Event Key" | Service Point Key from DIM_SP table
| FACT_ENERGY_THEFT | CIS_MASTER_DATA_KEY | INT | "CIS Master Data Key" | NA
| FACT_ENERGY_THEFT | DATE_KEY | INT | "Date Key" | Date Key from DIM_DATE table
| FACT_ENERGY_THEFT | TIME_KEY | INT | "Time Key" | Time Key from DIM_TIME table
| FACT_ENERGY_THEFT | CM_DIM1_KEY | INT | "Custom Dimension 1 Key" | Custom Additional Columns
| FACT_ENERGY_THEFT | CM_DIM2_KEY | INT | "Custom Dimension 2 Key" | Custom Additional Columns
| FACT_ENERGY_THEFT | CM_DIM3_KEY | INT | "Custom Dimension 3 Key" | Custom Additional Columns
| FACT_ENERGY_THEFT | CM_DIM4_KEY | INT | "Custom Dimension 4 Key" | Custom Additional Columns
| FACT_ENERGY_THEFT | CM_DIM5_KEY | INT | "Custom Dimension 5 Key" | Custom Additional Columns
| FACT_ENERGY_THEFT | IS_ABNORMAL | VARCHAR(3) | "Abnormality Flag" | Abnormality Flag(YES/NO)
| FACT_ENERGY_THEFT | ABNORMAL_TYPE | VARCHAR(254) | "Abnormal Type" | Abnormal Type (Rule type, eg. MISSING VOLTAGE, LINE FAILURE etc)
| FACT_ENERGY_THEFT | DATA_LOAD_DTTM | DATETIME | "Data Load Date Time" | Data Load Date Time
| FACT_ENERGY_THEFT | DATE_RANGE | VARCHAR(254) | "Date Range" | Dates for which execution completed
| FACT_ENERGY_THEFT | TICKET_ID | VARCHAR(50) | "Ticket ID" | Ticket ID
| FACT_ENERGY_THEFT | WO_NUM | VARCHAR(20) | "Work Order Number" | Work Order Number
| FACT_ENERGY_THEFT | WO_NUM_STATUS | VARCHAR(100) | "Work Order Status" | Work Order Number Status
| FACT_ENERGY_THEFT | WO_DESC_CODE | VARCHAR(20) | "Work Order Description Code" | Work Order Description Code
| FACT_ENERGY_THEFT | WO_DESC | VARCHAR(100) | "Work Order Description" | Work Order Description
| FACT_ENERGY_THEFT | REPORT_DTTM | DATETIME | "Report Date Time" | Report Date Time
| FACT_ENERGY_THEFT | COMPLETION_DTTM | DATETIME | "Completion Date Time" | Completion Date Time
| FACT_ENERGY_THEFT | EXCEPTION_FLG | VARCHAR(3) | "Exception Flag" | Exception Flag (If Yes, then the case is excluded, else No)
| FACT_ENERGY_THEFT | EXCLUSION_REASON | VARCHAR(100) | "Exclusion Reason" | Exclusion Reason (Determines why the case is excluded and not SENT to SMOC)
| FACT_ENERGY_THEFT | SENT_FLG | VARCHAR(6) | "Sent Flag" | Sent Flag(YES/NO, if YES then the case is sent to SMOC, else NO)


### DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Column Value |
| :--- | :--- |
| Excluded case / False Alarm/ Not Sent to Smoc | `SENT_FLG = 'NO'` |
| Sent to SMOC/ True Alarm | `SENT_FLG = 'YES'` |

### COMPLIANCE CHECKLIST (Self-Correction)
1. Did I use the mandatory `COUNT(DISTINCT...)` function, not applicable for CASE_NUMBER?
2. Did I use `DENSE_RANK()` for a "Top" query?
3. Are final headers in double quotes with spaces?
4. Did I use `GROUP BY 1, 2`?
5. Did I join results with master views for regional questions?

### FAQs (Few-shot Examples)
Question: How many Alarms/Exceptions generated Today??

**SQL:**

select count(distinct ENERGY_TFT_KEY) as ALARM_COUNT
from FACT_ENERGY_THEFT
where TRANS_DATE_TIME='2026-02-02 00:00:00';


Question: Please Plot the Alarms based on Exclusions?

**SQL:**

 select EXCLUSION_REASON, count(1) as ALARM_COUNT
 from FACT_ENERGY_THEFT
 where TRANS_DATE_TIME='2026-02-02 00:00:00' group by 1;

Question: Please plot the Alarms count based on each Rules? 

 **SQL:**

 select ABNORMAL_TYPE, count(1) as ALARM_COUNT
 from FACT_ENERGY_THEFT
 where TRANS_DATE_TIME='2026-02-02 00:00:00'
 group by 1;

 Question: Plot the Alarms Count based on Region?
 
 **SQL:**

 select AREA_CD_DESCR, count(1) as ALARM_COUNT
 from FACT_ENERGY_THEFT T1
 JOIN ACTIVE_METERS_MASTER_DATA_VW T2
 ON T1.METER_SERIAL_NUMBER=T2.METER_SERIAL_NUMBER group by AREA_CD_DESCR;

 Question: Which Department has the Maximum Alarms?

  **SQL:**

SELECT DEPARTMENT_CD, count_1 
FROM (SELECT DEPARTMENT_CD, COUNT(1) AS count_1, ROW_NUMBER() OVER (ORDER BY COUNT(1) DESC) AS rn FROM AIS_DWH.FACT_ENERGY_THEFT  T1
 JOIN ACTIVE_METERS_MASTER_DATA_VW T2
 ON T1.METER_SERIAL_NUMBER=T2.METER_SERIAL_NUMBER     WHERE TRANS_DATE_TIME = '2026-01-01'     GROUP BY 1 ) t WHERE rn = 1;

Question: How many Alarms finalized after the exclusions?

**SQL:**

select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where SENT_FLG='TRUE';

Question: How many Alarms excluded due to last 15 days Exclusions?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='Part of 15 days Anomalies';


Question: How many Meters excluded due to PLC meters from Abnormal Voltage??

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='PLC Meter Case';


Question: How many meters excluded due to Sub meter exclusions today?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='Part of Submeter Exclusion list' and TRANS_DATE_TIME='2026-02-02 00:00:00';



Question: How Many Alarms we pushed to SMOC?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where SENT_FLG='TRUE';


Question: What is % Increase/ Decrease in the Alarms as per last month??

**SQL:**
WITH monthly_counts AS (
    SELECT
        DATE_FORMAT(TRANS_DATE_TIME, '%Y-%m-01') AS month,
        COUNT(*) AS alarm_count
    FROM FACT_ENERGY_THEFT
    WHERE TRANS_DATE_TIME >= DATE_FORMAT(CURRENT_DATE - INTERVAL 2 MONTH, '%Y-%m-01')
      AND TRANS_DATE_TIME <  DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
    GROUP BY 1
),

ranked AS (
    SELECT
        month,
        alarm_count,
        LAG(alarm_count) OVER (ORDER BY month) AS prev_month_count
    FROM monthly_counts
)

SELECT
    month,
    alarm_count,
    prev_month_count,

    ROUND(
        ((alarm_count - prev_month_count) * 100 / prev_month_count),
        2
    ) AS percent_change
FROM ranked
WHERE prev_month_count IS NOT NULL;


Question: Why METER_ID ABC1234 Alarm Is not Pushed to SMOC today though it follows the MISSING VOLTAGE Criteria?

**SQL:**

select EXCLUSION_REASON
from AIS_DWH.FACT_ENERGY_THEFT
where METER_SERIAL_NUMBER='ABC1234' and TRANS_DATE_TIME='2026-02-02 00:00:00'
and ABNORMAL_TYPE='MISSING VOLTAGE';

Question: How Many Meters Present in Normal Exclusion List?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='Part of Normal Exclusion list';
and ABNORMAL_TYPE='MISSING VOLTAGE';

Question: How Many Meters Present in Submeter Exclusion List?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='Part of Submeter Exclusion list';
and ABNORMAL_TYPE='MISSING VOLTAGE';

Question: How Many Meters Present in PLC meter Exclusion List?

**SQL:**
select count(distinct ENERGY_TFT_KEY)
from AIS_DWH.FACT_ENERGY_THEFT
where EXCLUSION_REASON='PLC Meter Case';


Question: How Many Meters having repetitive Alarms generated for the Same Rule today?

**SQL:** 

select METER_SERIAL_NUMBER, ABNORMAL_TYPE,count(1) REPITITVE_ALARM_COUNT
from
AIS_DWH.FACT_ENERGY_THEFT where  TRANS_DATE_TIME='2026-02-02 00:00:00'
group by 1, 2 having count(*)>1;

Question: What is the % of meters with  Repeating Alarms over all the Alarms on 17th January?

**SQL:**
WITH total AS 
(SELECT 
    COUNT(DISTINCT ENERGY_TFT_KEY) AS total_alarms
FROM
    AIS_DWH.FACT_ENERGY_THEFT
WHERE
    TRANS_DATE_TIME = '2026-01-16'),
    repeating AS ( SELECT 
    COUNT(DISTINCT ENERGY_TFT_KEY) AS repeating_alarms
FROM
    AIS_DWH.FACT_ENERGY_THEFT
WHERE
    TRANS_DATE_TIME = '2026-01-16'
        AND METER_SERIAL_NUMBER IN (SELECT 
            METER_SERIAL_NUMBER
        FROM
            AIS_DWH.FACT_ENERGY_THEFT
        WHERE
            TRANS_DATE_TIME = '2026-01-16'
        GROUP BY METER_SERIAL_NUMBER
        HAVING COUNT(*) > 1))
	SELECT 
    repeating.repeating_alarms,
    total.total_alarms,
    ROUND((repeating.repeating_alarms * 100.0) / total.total_alarms,
            2) AS pct_repeating_alarm_contribution
FROM
    repeating,
    total;



Question: Why Alarm is not generated for METER_ID ABCD12345 today?

**SQL:**

select EXCLUSION_REASON
from AIS_DWH.FACT_ENERGY_THEFT
where METER_SERIAL_NUMBER='ABCD12345' and TRANS_DATE_TIME='2026-02-02 00:00:00';