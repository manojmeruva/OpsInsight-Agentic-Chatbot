DOMAIN LOGIC & CONTEXT
Domain: Field Team Efficiency Monitoring System (FTEMS)

Core Business Rules:

The FTEMS module track ticket for there resolution outcomes, identify high-risk and delayed cases, and highlight workload imbalances. By combining SLA compliance, first-time resolution, repeat visit patterns, and technician workload.

Task Types Filtering: For filtering of TICKETS always use TASK_TYPE.

Regional Queries: Use the AREA_CD, DEPARTMENT_CD, and OFFICE_CD columns from the result table to identify the region. When generating descriptions, use AREA_DESCR and AREA_DESCR_LNG for area names (English and Arabic), DEPARTMENT_DESCR for department details, and OFFICE_DESCR and OFFICE_DESCR_LNG for office-level descriptions (English and Arabic).

Time-Based Filtering: Always use the datetime column CAL_DT from the result tables for any time-series analysis.

###FIELD EFFICIENCY SCORE CALCULATION FORMULA

**Metric Components:

    **SLA Compliance: Derived from the SLA_COMPLIANCE_CHECK column where the value is "YES".

    **SLA Violation: Counted when SLA_COMPLIANCE_CHECK is "NO".

    **SLA Not Available: Noted when SLA_COMPLIANCE_CHECK is "SLA NOT AVAILABLE".

**Repeat Visits: Counted using the REPEAT_VISIT_FLAG column when the value is 1 and make sure METER_SERIAL_NUMBER and AREA_CD and DEPARTMENT_CD and OFFICE_CD columns are NOT NULL and TASK_STATUS column in CLOSED or COMPLETED while only calculating repeat visit count.

**Formula:

    (100*(SLA_COMPLIANCE_CHECK / COUNT OF TICKETS WHERE TASK_STATUS is CLOSED or COMPLETED) + (100 - 100*(REPEAT_VISIT_FLAG where value is 1 and METER_SERIAL_NUMBER and AREA_CD and DEPARTMENT_CD and OFFICE_CD columns are NOT NULL and TASK_STATUS column is CLOSED or COMPLETED / COUNT OF TICKETS WHERE TASK_STATUS is CLOSED or COMPLETED)) / 2) * (TASK_STATUS (COMPLETED or CLOSED) / TOTAL NUMBER OF TICKETS).
###TASK TIME CALCULATIONS

**Definition: Applies to queries regarding "Resolution Time," "Completion Time," "Task Resolution Time," or "Task Completion Time".
**Logic: Calculate the difference between the COMPLETE_TIME and ASSIGNED_TIME timestamp columns and filter tickets where TASK_STATUS column in CLOSED or COMPLETED.

**Output: The result is an integer representing the time difference, which can be displayed in hours, minutes, or days based on the specific question.

MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
Ranking & Top-N: For "Top," "Best," or "Highest," you MUST use a CTE/Subquery with DENSE_RANK().

Outer Query Filter: The outer query MUST filter by WHERE rnk = 1 to include ties.

Ordering/Grouping: Use column sequence numbers only (e.g., GROUP BY 1, 2).

Aliasing:

Internal (CTEs/Subqueries): Use snake_case.

Final Output: Use "Friendly Names with Spaces" in double quotes.

DATABASE SCHEMA & TABLE DEFINITIONS
Tables & Grain:

| Table Name | View Uniqueness Grain / Keys | Description |

| FTEMS_TICKETS_VW | TICKET_ID, REGISTRATION_TIME, AFFECTED_SM_LIST | This view contains ticket data for customer-reported issues linked to specific METER_SERIAL_NUMBERs.|

Join Logic:

Column Definitions:

| Table Name | Column Name | Column Type | Alias Name (Final Output) | Column Description |

| :--- | :--- | :--- | :--- | :--- |

|FTEMS_TICKETS_VW |AREA_CD | TEXT | Area code | Area code for the ticket was raised |

|FTEMS_TICKETS_VW |DEPARTMENT_CD | TEXT | Area code | department code for the ticket was raised |

|FTEMS_TICKETS_VW |OFFICE_CD | TEXT | Area code | office code for the ticket was raised |

|FTEMS_TICKETS_VW |AREA_DESCR | TEXT | area description | name of area for the ticket was raised |

|FTEMS_TICKETS_VW |AREA_DESCR_LNG | TEXT | arabic area description | arabic name of area for the ticket was raised |

|FTEMS_TICKETS_VW |DEPARTMENT_DESCR | TEXT | department/dept description | name of department for the ticket was raised |

|FTEMS_TICKETS_VW |DEPARTMENT_DESCR_LNG | TEXT | arabic department/dept description | arabic name of department for the ticket was raised |

|FTEMS_TICKETS_VW |OFFICE_DESCR | TEXT | office code description | name of office for the ticket was raised |

|FTEMS_TICKETS_VW |OFFICE_DESCR_LNG | TEXT | arabic office code description | arabic name of office for the ticket was raised |

|FTEMS_TICKETS_VW |CNTR_LAT | DECIMAL | lattitude of office | office location's lattitude |

|FTEMS_TICKETS_VW |CNTR_LONG | DECIMAL | longitude of office | office location's longitude |

|FTEMS_TICKETS_VW |NOTICE_CD | TEXT | notice code | Batch record last update timestamp |

|FTEMS_TICKETS_VW |CIM_CODE | TEXT | cim code | helps in creating category of ticket |

|FTEMS_TICKETS_VW |TICKET_ID | BIGINT | ticket id | unique id of ticket creation |

|FTEMS_TICKETS_VW |TICKET_TYPE | TEXT | ticket type | tells what kind of ticket category |

|FTEMS_TICKETS_VW |METER_SERIAL_NUMBER | TEXT | meter no/number | ticket raised on which meter serial number |

|FTEMS_TICKETS_VW |REGISTRATION_TIME | TIMESTAMP | ticket creation date time | tells when ticket is created |

|FTEMS_TICKETS_VW |ASSIGNED_TIME | TIMESTAMP | ticket assigned date time | when ticket is assigned to technician by dispatcher |

|FTEMS_TICKETS_VW |ACCEPT_TIME | TIMESTAMP | ticket accepted date time | when ticket is accepted by technician |

|FTEMS_TICKETS_VW |ARRIVE_TIME | TIMESTAMP | ticket arrive date time | when technician arrived at the location |

|FTEMS_TICKETS_VW |INPROCESS_TIME | TIMESTAMP | ticket inprocess/ongoing work date time | when technician started his work |

|FTEMS_TICKETS_VW |COMPLETE_TIME | TIMESTAMP | ticket completion by technician date time | when technician completed his work at the location |

|FTEMS_TICKETS_VW |REQ_CLOSING_TIME | TIMESTAMP | ticket closing request date time | when request closing at technician/dispatcher is closed |

|FTEMS_TICKETS_VW |CLOSED_TIME | TIMESTAMP | ticket closed date time at ifs | when ticket completely closed |

|FTEMS_TICKETS_VW |ACTUAL_START | TIMESTAMP | actual start | when was the work actually started |

|FTEMS_TICKETS_VW |ACTUAL_END | TIMESTAMP | actual start | when was the work actually ended |

|FTEMS_TICKETS_VW |PLAN_START | TIMESTAMP | actual end | when was the work planned started |

|FTEMS_TICKETS_VW |PLAN_END | TIMESTAMP | Area Code | when was the work planned ended |

|FTEMS_TICKETS_VW |VIP_STATUS | BOOLEAN | very imp person | is the ticket raised by VIP customer |

|FTEMS_TICKETS_VW |VIC_STATUS | BOOLEAN | Very Important Client | is the ticket raised by VIC customer |

|FTEMS_TICKETS_VW |VVSC_STATUS | BOOLEAN | Very Very Special Customer | is the ticket raised by VVSC customer |

|FTEMS_TICKETS_VW |REQ_TYPE | TEXT | Request Type | ticket belongs to which request type |

|FTEMS_TICKETS_VW |TASK_TYPE | TEXT | Task type | ticket belongs to which task type |

|FTEMS_TICKETS_VW |TECHNICIAN_ID | BIGINT | technician id | ticket assigned to which technician's id |

|FTEMS_TICKETS_VW |TECH_NAME_EN | TEXT | technician name | ticket assigned to which technician's name |

|FTEMS_TICKETS_VW |TECH_FLG | TEXT | technician flag | it gives description about role of the person working on ticket technician/dispatcher |

|FTEMS_TICKETS_VW |PRIORITY | TEXT | priority | it gives what is the tickets priority |

|FTEMS_TICKETS_VW |SLA | INT | service level agreement | it describes how much time that task type should completed within |

|FTEMS_TICKETS_VW |TASK_STATUS | TEXT | Task status | gives the status of the given ticket id |

|FTEMS_TICKETS_VW |ARABIC_REQ_TYPE | TEXT | arabic Request type | provides arabic version ticket belongs to which request type |

|FTEMS_TICKETS_VW |ARABIC_TASK_TYPE | TEXT | arabic Task type | provides arabic version ticket belongs to which task type |

|FTEMS_TICKETS_VW |MDM_INSTALL_EVT_ID | TEXT | mdm install event id | an id of mdm |

|FTEMS_TICKETS_VW |PREMISE_ID | TEXT | premise id | service point's premise id |

|FTEMS_TICKETS_VW |BILL_CYCLE_CD | TEXT | bill cycle code | provides bill cycle code |

|FTEMS_TICKETS_VW |ACCOUNT_NBR | account number | account number | account number of service point |

|FTEMS_TICKETS_VW |GEO_LATITUDE | DECIMAL | service point latitude | service points latitude |

|FTEMS_TICKETS_VW |GEO_LONGITIDE | DECIMAL | service point longitude | service points longitude |

|FTEMS_TICKETS_VW |CAL_DT | TIMESTAMP | calender date | provides as a pivot for time series events |

|FTEMS_TICKETS_VW |OPEN_TICKETS | BOOLEAN | open tickets | provides a flag what all are open tickets |

|FTEMS_TICKETS_VW |DEPARTMENT_OFFICE_CODE | TEXT | department and office code | provides a concatenation of department and office code |

|FTEMS_TICKETS_VW |HIGH_PRIORITY_FLAG | BOOLEAN | high priority flag | provides whether a given ticket is priority or not |

|FTEMS_TICKETS_VW |SLA_COMPLIANCE_CHECK | TEXT | sla compliance check | provides a flag when task complete <= SLA as a flag and other scenario where task status is not in completed stage |

|FTEMS_TICKETS_VW |REPEAT_VISIT_FLAG | BOOLEAN | repeat visit flag | provides a flag whether the ticket raised of the same meter serial number and task type within 30 days or not|

|FTEMS_TICKETS_VW |DATA_LOAD_DTTM | TIMESTAMP | data load time | provides at what time ticket got loaded or updated |

DATA MAPPINGS (COLUMN VALUES)
| Concept | SQL Filter / Column Value |

| :--- | :--- |

| SLA compliance | SLA_COMPLIANCE_CHECK = 'YES'

| SLA violation | SLA_COMPLIANCE_CHECK = 'NO'

| SLA not available | SLA_COMPLIANCE_CHECK = 'SLA NOT AVAILABLE'

| supervisor | TECH_FLG = 'SV'

| technician | TECH_FLG = 'TECH'

| repeat visit ticket | REPEAT_VISIT_FLAG='1'

| not repeat visit ticket | REPEAT_VISIT_FLAG='0'

COMPLIANCE CHECKLIST (Self-Correction)
When a question refers to tickets resolved or tasks completed or task resolved etc, verify that the SQL query correctly filters the TASK_STATUS column using the appropriate values such as "COMPLETED" or "CLOSED".

FAQs (Few-shot Examples)
Questions: What is the overall Field Team Efficiency Score for the July month?

SQL:

WITH MonthlyData AS (

SELECT

    COUNT(TICKET_ID) AS total_tickets_in_month,

    SUM(CASE

        WHEN TRIM(UPPER(TASK_STATUS)) IN ('CLOSED', 'COMPLETED') THEN 1

        ELSE 0

    END) AS total_completed_closed_tickets,

    SUM(CASE

        WHEN TRIM(UPPER(TASK_STATUS)) IN ('CLOSED', 'COMPLETED')

             AND TRIM(UPPER(SLA_COMPLIANCE_CHECK)) = 'YES' THEN 1

        ELSE 0

    END) AS sla_compliant_count,

    SUM(CASE

        WHEN TRIM(UPPER(TASK_STATUS)) IN ('CLOSED', 'COMPLETED')

             AND REPEAT_VISIT_FLAG = '1' AND METER_SERIAL_NUMBER IS NOT NULL AND AREA_CD IS NOT NULL AND DEPARTMENT_CD IS NOT NULL AND OFFICE_CD IS NOT NULL THEN 1

        ELSE 0

    END) AS repeat_visit_count

FROM FTEMS_TICKETS_VW

WHERE CAL_DT >= '2025-07-01 00:00:00'

  AND CAL_DT <  '2025-08-01 00:00:00'
)

SELECT

CASE

    WHEN md.total_tickets_in_month = 0 THEN 0.00

    ELSE (

        (

            /* Part 1: Average of SLA % and First-Time Fix % */

            (

                CASE

                    WHEN md.total_completed_closed_tickets = 0 THEN 0.00

                    ELSE (md.sla_compliant_count * 100.0 / md.total_completed_closed_tickets)

                END

            )

            +

            (

                100.0 - (

                    CASE

                        WHEN md.total_completed_closed_tickets = 0 THEN 0.00

                        ELSE (md.repeat_visit_count * 100.0 / md.total_completed_closed_tickets)

                    END

                )

            )

        ) / 2.0

    )

    * /* Part 2: Weighting by Ticket Closure Rate */

    (

        CASE

            WHEN md.total_tickets_in_month = 0 THEN 0.00

            ELSE (md.total_completed_closed_tickets * 1.0 / md.total_tickets_in_month)

        END

    )

END AS `Overall Field Team Efficiency Score`
FROM MonthlyData md;

Questions: How many tickets were resolved within SLA across all departments?

SQL:

SELECT

COUNT(*) AS `tickets resolved within sla`
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

AND SLA_COMPLIANCE_CHECK = "YES";

Questions: Which department has the highest SLA violation rate?

SQL:

SELECT

DEPARTMENT_DESCR,

ROUND(

    (

        SUM(CASE WHEN SLA_COMPLIANCE_CHECK = "NO" THEN 1 ELSE 0 END) * 100.0

        / NULLIF(COUNT(*), 0)

    ),

    2

) AS `sla violation rate pct`
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

GROUP BY DEPARTMENT_DESCR

ORDER BY sla violation rate pct DESC

LIMIT 1;

Questions: Identify departments with high repeat visit percentages.

SQL:

SELECT

DEPARTMENT_DESCR,

ROUND(

    (

        SUM(CASE WHEN REPEAT_VISIT_FLAG = 1 AND METER_SERIAL_NUMBER IS NOT NULL AND AREA_CD IS NOT NULL AND DEPARTMENT_CD IS NOT NULL AND OFFICE_CD IS NOT NULL THEN 1 ELSE 0 END) * 100.0

        / NULLIF(COUNT(*), 0)

    ),

    2

) AS "Repeat visit rate"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

GROUP BY DEPARTMENT_DESCR

HAVING COUNT(*) > 0

ORDER BY Repeat visit rate DESC;

Questions: What is the total count of tickets resolved with no SLA data

SQL:

SELECT

COUNT(*) AS "total ticket count"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

AND SLA_COMPLIANCE_CHECK="SLA NOT AVAILABLE";

Questions: What is the average resolution time/average complete time or completion time/task close time overall in hours

SQL:

SELECT

ROUND(AVG(TIMESTAMPDIFF(HOUR, ASSIGNED_TIME, COMPLETE_TIME)),2) AS "Avg task complete time"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED');

Questions: What is the average resolution time across all technicians this month in hours?

SQL:

SELECT

TECHNICIAN_ID,

TECH_NAME_EN,

ROUND(AVG(TIMESTAMPDIFF(HOUR, ASSIGNED_TIME, COMPLETE_TIME)),2) AS "Avg resolution time"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

AND CAL_DT >= DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')

AND CAL_DT < DATE_ADD(DATE_FORMAT(CURRENT_DATE, '%Y-%m-01'), INTERVAL 1 MONTH)

GROUP BY TECHNICIAN_ID,

TECH_NAME_EN;

Questions: Which task types have the highest average resolution time?

SQL:

SELECT

REQ_TYPE,

TASK_TYPE,

ROUND(AVG(TIMESTAMPDIFF(HOUR, ASSIGNED_TIME, COMPLETE_TIME)),2) AS "Avg resolution time"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED')

GROUP BY REQ_TYPE,

TASK_TYPE

ORDER BY Avg resolution time DESC;

Questions: How many tickets were resolved in less than 5 minutes ?

SQL:

SELECT

COUNT(*) AS "total tickets resolved in 5 minutes"
FROM AIS_DWH.FTEMS_TICKETS_VW

WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED') AND TIMESTAMPDIFF(MINUTE, ASSIGNED_TIME, COMPLETE_TIME) <= 5;

Questions: What is the total count of tickets completed within 5 mins in Riyadh suburbs Department?

SQL:

SELECT COUNT(*) AS 'Tickets completed within 5 minutes'

FROM FTEMS_TICKETS_VW WHERE TASK_STATUS IN ('CLOSED', 'COMPLETED') AND TIMESTAMPDIFF(MINUTE, ASSIGNED_TIME, COMPLETE_TIME) <= 5

AND TRIM(UPPER(DEPARTMENT_DESCR)) = 'RIYADH SUBURBS' LIMIT 200;