**Domain:** Guarantee Standard Process (GSP)
**Core Business Rules:**
* The GSP module monitors service interruptions, restoration, and reconnection efficiency to track customer compensation eligibility.
* **Outage Correctness**: For outages and compensation eligibility, use the `ELIGIBILITY` column.
* **Meter Uniqueness**: Result tables contain meter-level outages; count unique meters using `COUNT(DISTINCT METER_SERIAL_NUMBER)`.
* **Regional Queries**: Join Result tables with Master Data views for questions related to regions, departments, or offices.
* **Time-Based Filtering**: Always use the datetime column CUT_DTTM from the result tables for any time-series analysis.
* **Efficiency Formula**: (Success / Total) * 100.
* **Unplanned Outage Definition**: When a query asks for "Unplanned Outages," you MUST combine results from both GS_UNPLANNED_OUTAGE_RESULT_VW and GS_PLC_METER_RESULT using a UNION ALL or by performing calculations across both tables.

### MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
* **Counting Rule**: Never use `COUNT(*)`. Always use COUNT(DISTINCT METER_SERIAL_NUMBER) for meter counts. For unique keys like CASE_NUMBER, use COUNT(CASE_NUMBER).
* **Conditional Outage Filter (Mandatory):** For ANY query targeting GS_PLANNED_OUTAGE_RESULT, GS_UNPLANNED_OUTAGE_RESULT_VW, you MUST include EXCLUSION_REASON != 'No Outage Identified'. Do NOT apply this filter to GS_BLACKOUT_METER_RESULT or GS_PLC_METER_RESULT
* **Ranking & Top-N**: For "Top," "Best," or "Highest," you MUST use a CTE/Subquery with `DENSE_RANK()`.
* **Outer Query Filter**: The outer query MUST filter by `WHERE rnk = 1` to include ties.
* **Ordering/Grouping**: Use column sequence numbers only (e.g., `GROUP BY 1, 2`).
* **Aliasing**: 
    * Internal (CTEs/Subqueries): Use `snake_case`.
    * Final Output: Use "Friendly Names with Spaces" in double quotes.
* **Time Filtering**: Use result table datetime columns for all calendar filters.

### DATABASE SCHEMA & TABLE DEFINITIONS

**Tables & Grain:**
| Table Name | Primary Grain / Keys | Description |
| :--- | :--- | :--- |
| ACTIVE_METERS_MASTER_DATA_VW | METER_SERIAL_NUMBER | Master data mapping for blackout meters |
| GS_BLACKOUT_METER_RESULT | METER_SERIAL_NUMBER, CUT_DTTM | Blackout meter outage results |
| GS_PLANNED_OUTAGE_RESULT | TICKET_ID, CASE_NUMBER, METER_SERIAL_NUMBER, PLANNED_OUTAGE_START_DATETIME | Planned outage results with ticket information |
| GS_PLC_METER_RESULT | METER_SERIAL_NUMBER, CUT_DTTM | Power Line Communication meter outage results |
| GS_UNPLANNED_OUTAGE_RESULT_VW | METER_SERIAL_NUMBER, CUT_DTTM, DATA_SOURCE_IND, TICKET_NUMBER | Unplanned outage results with ticket and meter info |

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
| ACTIVE_METERS_MASTER_DATA_VW | VIC_FLG | TEXT             | "VIC Flag"| VIC Flag (Y= Yes, N=No)
| ACTIVE_METERS_MASTER_DATA_VW | VIP_FLG | TEXT             | "VIP Flag"| VIP Flag (Y= Yes, N=No)
| ACTIVE_METERS_MASTER_DATA_VW | VOLTAGE | DECIMAL          | "Voltage"| Voltage
| ACTIVE_METERS_MASTER_DATA_VW | AREA_CD | TEXT             | "Region Code"| Area/Region Code
| ACTIVE_METERS_MASTER_DATA_VW | AREA_CD_DESCR | TEXT       | "Region Name"| Area/Region Name
| ACTIVE_METERS_MASTER_DATA_VW | DEPARTMENT_CD | TEXT       | "Department Code"| Department Code
| ACTIVE_METERS_MASTER_DATA_VW | DEPARTMENT_CD_DESCR | TEXT | "Department Name"| Department Name
| ACTIVE_METERS_MASTER_DATA_VW | OFFICE_CD | TEXT           | "Office Code"| Office Code
| ACTIVE_METERS_MASTER_DATA_VW | OFFICE_CD_DESCR | TEXT     | "Office Name"| Office Name
| GS_BLACKOUT_METER_RESULT | CASE_NUMBER | VARCHAR(50) | "Case Number" | Sequential case number |
| GS_BLACKOUT_METER_RESULT | CUT_DTTM | DATETIME | "Outage Start Date & Time" | Outage start time |
| GS_BLACKOUT_METER_RESULT | CUT_DURATION | DECIMAL(10,2) | "Outage Duration (Hours)" | Outage Duration in hours |
| GS_BLACKOUT_METER_RESULT | ELIGIBLITY | VARCHAR(5) | "Eligibility Status" | Eligibility for compensation |
| GS_BLACKOUT_METER_RESULT | EXCEPTION_FLG | VARCHAR(5) | "Exception Flag" | YES / NO |
| GS_BLACKOUT_METER_RESULT | EXCEPTION_REF_NO | VARCHAR(50) | "Exception Reference Number" | SEC reference |
| GS_BLACKOUT_METER_RESULT | EXCLUSION_REASON | TEXT | "Exclusion Reason" | Reason for exclusion |
| GS_BLACKOUT_METER_RESULT | METER_SERIAL_NUMBER | VARCHAR(50) | "Meter Serial Number" | Meter serial number |
| GS_BLACKOUT_METER_RESULT | PREMISE_ID | VARCHAR(50) | "Premise ID" | Premise |
| GS_BLACKOUT_METER_RESULT | PROCESS_FLG | VARCHAR(10) | "Process Type" | UPL / PLN / PLC / BLK |
| GS_BLACKOUT_METER_RESULT | RESTORE_DTTM | DATETIME | "Restore Date & Time" | Restore time |
| GS_BLACKOUT_METER_RESULT | SAP_INSTALL_NBR | VARCHAR(50) | "SAP Installation Number" | SAP installation |
| GS_PLANNED_OUTAGE_RESULT | ACTUAL_CUT_DURATION | DECIMAL(10,2) | "Actual Outage Duration (Hours)" | Actual duration |
| GS_PLANNED_OUTAGE_RESULT | CASE_NUMBER | VARCHAR(50) | "Case Number" | Sequential case number |
| GS_PLANNED_OUTAGE_RESULT | CUT_DTTM | DATETIME | "Actual Outage Start Date & Time" | Actual cut time |
| GS_PLANNED_OUTAGE_RESULT | DL_DTTM | DATETIME | "Load Date & Time" | Load timestamp |
| GS_PLANNED_OUTAGE_RESULT | ELIGIBLITY | VARCHAR(5) | "Eligibility Status" | YES / NO |
| GS_PLANNED_OUTAGE_RESULT | EXCEPTION_FLG | VARCHAR(5) | "Exception Flag" | YES / NO |
| GS_PLANNED_OUTAGE_RESULT | EXCEPTION_REF_NO | VARCHAR(50) | "Exception Reference Number" | SEC reference |
| GS_PLANNED_OUTAGE_RESULT | EXCLUSION_REASON | TEXT | "Exclusion Reason" | Reason |
| GS_PLANNED_OUTAGE_RESULT | METER_SERIAL_NUMBER | VARCHAR(50) | "Meter Serial Number" | Meter serial number |
| GS_PLANNED_OUTAGE_RESULT | PLANNED_CUT_DURATION | DECIMAL(10,2) | "Planned Outage Duration (Hours)" | Planned duration |
| GS_PLANNED_OUTAGE_RESULT | PLANNED_OUTAGE_END_DATETIME | DATETIME | "Planned Outage End Date & Time" | Planned end |
| GS_PLANNED_OUTAGE_RESULT | PLANNED_OUTAGE_START_DATETIME | DATETIME | "Planned Outage Start Date & Time" | Planned start |
| GS_PLANNED_OUTAGE_RESULT | PREMISE_ID | VARCHAR(50) | "Premise ID" | Premise |
| GS_PLANNED_OUTAGE_RESULT | PROCESS_FLG | VARCHAR(10) | "Process Type" | UPL / PLN / PLC / BLK |
| GS_PLANNED_OUTAGE_RESULT | RESTORE_DTTM | DATETIME | "Restore Date & Time" | Restore time |
| GS_PLANNED_OUTAGE_RESULT | SAP_INSTALL_NBR | VARCHAR(50) | "SAP Installation Number" | SAP installation |
| GS_PLANNED_OUTAGE_RESULT | TICKET_ID | VARCHAR(50) | "Ticket ID" | Ticket identifier |
| GS_PLC_METER_RESULT | CASE_NUMBER | VARCHAR(50) | "Case Number" | Sequential case number |
| GS_PLC_METER_RESULT | CUT_DTTM | DATETIME | "Outage Start Date & Time" | Outage start timestamp |
| GS_PLC_METER_RESULT | CUT_DURATION | DECIMAL(10,2) | "Outage Duration (Hours)" | Outage duration in hours |
| GS_PLC_METER_RESULT | DL_DTTM | DATETIME | "Load Date & Time" | Load timestamp |
| GS_PLC_METER_RESULT | ELIGIBLITY | VARCHAR(5) | "Eligibility Status" | YES / NO |
| GS_PLC_METER_RESULT | EXCEPTION_FLG | VARCHAR(5) | "Exception Flag" | YES / NO |
| GS_PLC_METER_RESULT | EXCEPTION_REF_NO | VARCHAR(50) | "Exception Reference Number" | SEC reference |
| GS_PLC_METER_RESULT | EXCLUSION_REASON | TEXT | "Exclusion Reason" | Reason for exclusion |
| GS_PLC_METER_RESULT | METER_SERIAL_NUMBER | VARCHAR(50) | "Meter Serial Number" | Serial number of meter |
| GS_PLC_METER_RESULT | PREMISE_ID | VARCHAR(50) | "Premise ID" | Premise identifier |
| GS_PLC_METER_RESULT | PROCESS_FLG | VARCHAR(10) | "Process Type" | UPL / PLN / PLC / BLK |
| GS_PLC_METER_RESULT | RESTORE_DTTM | DATETIME | "Restore Date & Time" | Restore timestamp |
| GS_PLC_METER_RESULT | SAP_INSTALL_NBR | VARCHAR(50) | "SAP Installation Number" | SAP installation |
| GS_UNPLANNED_OUTAGE_RESULT_VW | CASE_NUMBER | VARCHAR(50) | "Case Number" | Sequential case number |
| GS_UNPLANNED_OUTAGE_RESULT_VW | CUT_DTTM | DATETIME | "Outage Start Date & Time" | Outage start timestamp |
| GS_UNPLANNED_OUTAGE_RESULT_VW | CUT_DURATION | DECIMAL(10,2) | "Outage Duration (Hours)" | Total duration |
| GS_UNPLANNED_OUTAGE_RESULT_VW | DATA_SOURCE_IND | VARCHAR(10) | "Data Source" | SMOC / IFS / PLN(SAP-PM) |
| GS_UNPLANNED_OUTAGE_RESULT_VW | DL_DTTM | DATETIME | "Load Date & Time" | Load timestamp |
| GS_UNPLANNED_OUTAGE_RESULT_VW | ELIGIBLITY | VARCHAR(5) | "Eligibility Status" | YES = eligible, NO = excluded |
| GS_UNPLANNED_OUTAGE_RESULT_VW | EXCEPTION_FLG | VARCHAR(5) | "Exception Flag" | YES if excluded |
| GS_UNPLANNED_OUTAGE_RESULT_VW | EXCEPTION_REF_NO | VARCHAR(50) | "Exception Reference Number" | SEC reference |
| GS_UNPLANNED_OUTAGE_RESULT_VW | EXCLUSION_REASON | TEXT | "Exclusion Reason" | Reason for exclusion |
| GS_UNPLANNED_OUTAGE_RESULT_VW | FUNC_LOC_ID | VARCHAR(50) | "Functional Location ID" | Functional location |
| GS_UNPLANNED_OUTAGE_RESULT_VW | METER_SERIAL_NUMBER | VARCHAR(50) | "Meter Serial Number" | Serial number of meter |
| GS_UNPLANNED_OUTAGE_RESULT_VW | OUTAGE_TYPE | VARCHAR(20) | "Outage Type" | Type of outage |
| GS_UNPLANNED_OUTAGE_RESULT_VW | PROCESS_FLG | VARCHAR(10) | "Process Type" | UPL / PLN / PLC / BLK |
| GS_UNPLANNED_OUTAGE_RESULT_VW | RESTORE_DTTM | DATETIME | "Restore Date & Time" | Power restored timestamp |
| GS_UNPLANNED_OUTAGE_RESULT_VW | TICKET_NUMBER | BIGINT | "Ticket Number" | Missing ticket id has 'INS' |
| GS_UNPLANNED_OUTAGE_RESULT_VW | TICKET_TYPE | VARCHAR(20) | "Ticket Type" | MASTER or SINGLE |
| GS_UNPLANNED_OUTAGE_RESULT_VW | WO_ORDER_NBR | VARCHAR(50) | "Work Order Number" | Work order number |

### DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Column Value |
| :--- | :--- |
| Excluded from Compensation / False Alert | `ELIGIBLITY = 'NO'` |
| Eligible for Compensation | `ELIGIBLITY = 'YES'` |
| Missing Ticket | `TICKET_NUMBER LIKE '%INS%'` |
| No Identified Outage | `EXCLUSION_REASON = 'No Outage Identified'` |
| IFS Remarks | `EXCLUSION_REASON LIKE 'IFS_REMARKS%'` |
| Head End System (HES)| NARI, SCH (Schneider)|



### COMPLIANCE CHECKLIST (Self-Correction)
1. Did I use the mandatory `COUNT(DISTINCT...)` function?
2. Did I use `DENSE_RANK()` for a "Top" query?
3. Are final headers in double quotes with spaces?
4. Did I use `GROUP BY 1, 2`?
5. Did I join results with master views for regional questions?

### FAQs (Few-shot Examples)
Question: How many planned outages were recorded in January 2025?

**SQL:**

SELECT COUNT(CASE_NUMBER) AS "Planned Outage Count"
FROM GS_PLANNED_OUTAGE_RESULT
WHERE CUT_DTTM >= '2025-01-01' AND CUT_DTTM < '2025-02-01'
AND EXCLUSION_REASON != 'No Outage Identified';


Question: How many planned outages exceeded their scheduled time this quarter?

**SQL:**

SELECT COUNT(CASE_NUMBER) AS "Outage Count"
FROM GS_PLANNED_OUTAGE_RESULT
WHERE ACTUAL_CUT_DURATION > PLANNED_CUT_DURATION
AND CUT_DTTM >= '2025-01-01' AND CUT_DTTM < '2025-04-01'
AND EXCLUSION_REASON != 'No Outage Identified';


Question: What is the compliance summary for planned outages in 2025 year in dammam?

**SQL:**

SELECT ELIGIBLITY AS "Eligibility Status",
       COUNT(CASE_NUMBER) AS "Planned Outage Count"
FROM GS_PLANNED_OUTAGE_RESULT GPOR
JOIN ACTIVE_METERS_MASTER_DATA_VW GMPV ON GPOR.METER_SERIAL_NUMBER = GMPV.METER_SERIAL_NUMBER
WHERE YEAR(GPOR.CUT_DTTM) = 2025
AND TRIM(UPPER(GMPV.DEPARTMENT_CD_DESCR)) LIKE '%DAMMAM%'
AND EXCLUSION_REASON != 'No Outage Identified'
GROUP BY 1;



Question: How many unplanned outages occurred yesterday in Jeddah
**SQL:**
SELECT COUNT(CASE_NUMBER) AS "Unplanned Outage Count"
FROM (
    SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, EXCLUSION_REASON
    FROM GS_UNPLANNED_OUTAGE_RESULT_VW
    WHERE EXCLUSION_REASON != 'No Outage Identified'
    UNION ALL
    SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, EXCLUSION_REASON
    FROM GS_PLC_METER_RESULT
) AS combined_unplanned
JOIN ACTIVE_METERS_MASTER_DATA_VW AS master_data 
    ON combined_unplanned.METER_SERIAL_NUMBER = master_data.METER_SERIAL_NUMBER
WHERE DATE(combined_unplanned.CUT_DTTM) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
AND TRIM(UPPER(master_data.DEPARTMENT_CD_DESCR)) LIKE '%JEDDAH%';

Question: Which 3 departments had the highest number of unplanned outages in 2025
**SQL:**
WITH dept_counts AS (
    SELECT T2.DEPARTMENT_CD_DESCR,
           COUNT(T1.CASE_NUMBER) AS total_outages,
           DENSE_RANK() OVER (ORDER BY COUNT(T1.CASE_NUMBER) DESC) AS rnk
    FROM (
        SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, EXCLUSION_REASON FROM GS_UNPLANNED_OUTAGE_RESULT_VW WHERE EXCLUSION_REASON != 'No Outage Identified'
        UNION ALL
        SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, EXCLUSION_REASON FROM GS_PLC_METER_RESULT
    ) T1
    JOIN ACTIVE_METERS_MASTER_DATA_VW T2 ON T1.METER_SERIAL_NUMBER = T2.METER_SERIAL_NUMBER
    WHERE T1.CUT_DTTM >= '2025-01-01' AND T1.CUT_DTTM < '2026-01-01'    
    GROUP BY 1
)
SELECT DEPARTMENT_CD_DESCR AS "Department Name",
       total_outages AS "Outage Count"
FROM dept_counts
WHERE rnk <= 3;

Question: What is the success rate of unplanned outage restorations in the Central region for October 2025
**SQL:**
SELECT (SUM(CASE WHEN ELIGIBLITY = 'YES' THEN 1 ELSE 0 END) * 100.0) / COUNT(CASE_NUMBER) AS "Success Rate Percentage"
FROM (
    SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, ELIGIBLITY, EXCLUSION_REASON FROM GS_UNPLANNED_OUTAGE_RESULT_VW WHERE EXCLUSION_REASON != 'No Outage Identified'
    UNION ALL
    SELECT CASE_NUMBER, METER_SERIAL_NUMBER, CUT_DTTM, ELIGIBLITY, EXCLUSION_REASON FROM GS_PLC_METER_RESULT
) T1
JOIN ACTIVE_METERS_MASTER_DATA_VW T2 ON T1.METER_SERIAL_NUMBER = T2.METER_SERIAL_NUMBER
WHERE T1.CUT_DTTM >= '2025-10-01' AND T1.CUT_DTTM < '2025-11-01'
AND TRIM(UPPER(T2.AREA_CD_DESCR)) LIKE '%CENTRAL%';


Question: How many cases are having repetitive outages last week of august 2025?

**SQL:**

SELECT COUNT(DISTINCT METER_SERIAL_NUMBER) AS "Repetitive Outage Meter Count"
FROM (
    SELECT METER_SERIAL_NUMBER
    FROM GS_UNPLANNED_OUTAGE_RESULT_VW
    WHERE CUT_DTTM >= '2025-08-25' AND CUT_DTTM < '2025-09-01'
    AND EXCLUSION_REASON != 'No Outage Identified'
    GROUP BY 1
    HAVING COUNT(CASE_NUMBER) > 1
) a;




Question: How many PLC meters are eligible for compensation this week?

**SQL:**

SELECT COUNT(DISTINCT METER_SERIAL_NUMBER) AS "Eligible Meter Count"
FROM GS_PLC_METER_RESULT
WHERE CUT_DTTM >= '2025-04-01' AND CUT_DTTM < '2025-04-08'
AND TRIM(ELIGIBLITY) = 'YES';


Question: How many cases are having IFS remarks in last week of august 2025?

**SQL:**

SELECT COUNT(CASE_NUMBER) AS "IFS Remarks Count"
FROM GS_UNPLANNED_OUTAGE_RESULT_VW
WHERE TRIM(EXCLUSION_REASON) LIKE 'IFS_REMARKS%'
AND CUT_DTTM >= '2025-08-25' AND CUT_DTTM < '2025-09-01';



Question: How many blackout outages occurred in Riyadh during February 2025
**SQL:**
SELECT COUNT(CASE_NUMBER) AS "Blackout Outage Count"
FROM GS_BLACKOUT_METER_RESULT T1
	JOIN ACTIVE_METERS_MASTER_DATA_VW T2 ON T1.METER_SERIAL_NUMBER = T2.METER_SERIAL_NUMBER
WHERE T1.CUT_DTTM >= '2025-02-01' AND T1.CUT_DTTM < '2025-03-01'
	AND TRIM(UPPER(T2.DEPARTMENT_CD_DESCR)) LIKE '%RIYADH%'
GROUP BY 1;