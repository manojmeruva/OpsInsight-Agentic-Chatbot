**Domain:** Synchronous and Asynchronous Peak Load Monitoring System (SPLM)
* Asynchronous peak is highest individual peak for Meter,Office,Department,Region,Service Class,KSA Peak on Daily/ Monthly and Yearly basis(may occur at different times)
* Synchronous peak is highest coincident load across all the geographical hierarchies with respect to KSA for Meter,Office,Department,Region,Service Class on Daily/ Monthly and Yearly basis(from AGG_PEAK_LOAD_KSA table or highest PEAK_LOAD_DTTM match)
**Core Business Rules:**
* Aggregations exist at multiple levels: Meter --> Service Class, Meter --> Office --> Department --> Area(Region) --> KSA
* LOAD_FLG(Load Flag) typically: either 'Sync' or 'Async' only.
* PERIOD_TYPE(Period Type): 'Daily', 'Monthly', 'Yearly' but for Load Curve and Load Duration Curve Tables PERIOD_TYPE: 'WEEKLY', 'MONTHLY', 'YEARLY'
* Use PEAK_LOAD_DTTM for time-of-day analysis
* Customer segments → most commonly represented by SERVICE_CLASS_DESCR
* For service class queries, include ORG_FLG and ORG_CD when present
* ORG_FLG: 'OFFICE' for Office level, 'DEPT' for Department level, 'AREA' for Area level, 'KSA' for KSA level

### MANDATORY SQL CONSTRAINTS (STRICT COMPLIANCE)
* Always filter on PERIOD_TYPE when relevant ('Monthly', 'Yearly', etc.), for load duration and load curve use 'WEEKLY', 'MONTHLY', 'YEARLY'
* Peak tables table level filters: -: If any month is specified then add PERIOD_TYPE='Monthly', if a day, or a date range then, PERIOD_TYPE='Daily', if any year is specified or nothing is specified then use PERIOD_TYPE='Yearly'
* Load Curve and Load duration curve table level filters: - If any month is specified then use PERIOD_TYPE='MONTHLY', if any Week is specified then use PERIOD_TYPE='WEEKLY', if any year is specified or nothing is specified then use PERIOD_TYPE='YEARLY'
* Unit Conversion: Always divide load values (PEAK_LOAD, AVG_PEAK_LOAD, MSRMT_VAL) by 1,000,000 to convert from KW to GW.
* GW Disclosure: If a question is asked, the explanation or response must explicitly state that the values are provided in GW.
* Ranking: Use DENSE_RANK() OVER (...) for Top-N / highest contributing
* Alias Formatting: Always use backticks (`` ` ``) for column aliases that contain spaces or special characters (e.g., `Peak Load (GW)`). Never use double quotes for aliasing.
* Grouping: Prefer GROUP BY 1, 2, ... style
* Never use COUNT(*) for meter/business entities — use COUNT(DISTINCT ...) when applicable


### DATABASE SCHEMA & TABLE DEFINITIONS

**Tables & Grain:**

| Table Name                              | Primary Grain / Keys                                                                 		 | Description                                                                 |
| :--- 									  | :--- 																						 | :--- 																	   |
| AGG_PEAK_LOAD_KSA                       | PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY                                                   		 | National (KSA-level) peak load aggregates – synchronous system-wide peak    |
| AGG_PEAK_LOAD_AREA                      | AREA_CD, LOAD_FLG, PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY                                		 | Area/region level peak load aggregates Sync and Async data                  |
| AGG_PEAK_LOAD_DEPARTMENT                | DEPARTMENT_CD, LOAD_FLG, PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY                          		 | Department level peak load aggregates Sync and Async data                                      |
| AGG_PEAK_LOAD_OFFICE                    | OFFICE_CD, LOAD_FLG, PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY                              		 | Office level peak load aggregates Sync and Async data                                          |
| AGG_PEAK_LOAD_SERVICE_CLASS             | SERVICE_CLASS_DESCR, LOAD_FLG, PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY, ORG_FLG, ORG_CD   		 | Service class / customer segment peak load aggregates Sync and Async data (with org hierarchy)  |
| AGG_PEAK_LOAD_METER                     | METER_SERIAL_NUMBER, LOAD_FLG, PERIOD_TYPE, YEAR, LOAD_PERIOD_KEY, OFFICE_CD         		 | Individual meter-level peak load aggregates Sync and Async data                                |
| PEAK_LOAD_DAILY_PROFILE_KSA             | MSRMT_DATE_TIME, MEASR_COMP_TYPE                                                     		 | National aggregated 30mins interval data for each data                                |
| PEAK_LOAD_DAILY_PROFILE_AREA            | AREA_CD, MSRMT_DATE_TIME, MEASR_COMP_TYPE                                            		 | Area-level aggregated 30mins interval data for each data                              |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | DEPARTMENT_CD, MSRMT_DATE_TIME, MEASR_COMP_TYPE                                      		 | Department-level aggregated 30mins interval data for each data                        |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | OFFICE_CD, MSRMT_DATE_TIME, MEASR_COMP_TYPE                                          		 | Office-level aggregated 30mins interval data for each data                            |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | SERVICE_CLASS_DESCR, MSRMT_DATE_TIME, MEASR_COMP_TYPE, ORG_FLG, ORG_CD               		 | Service class / customer segment aggregated 30mins interval data for each data        |
| AGG_LOAD_CURVE_SERVICE_CLASS            | SERVICE_CLASS_DESCR, OFFICE_CD, DEPARTMENT_CD, AREA_CD, PERIOD_KEY, PERIOD_TYPE, HOUR_BUCKET | Hourly average load curve by service class and org hierarchy                |
| AGG_LOAD_DURATION_CURVE_KSA             | PERIOD_KEY, PERIOD_TYPE, PCT_INTERVAL                                                		 | National load duration curve (sorted descending load vs. % of time)         |
| AGG_LOAD_DURATION_CURVE_AREA            | AREA_CD, PERIOD_KEY, PERIOD_TYPE, PCT_INTERVAL                                       		 | Area-level load duration curve (sorted descending load vs. % of time)                                            |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | DEPARTMENT_CD, AREA_CD, PERIOD_KEY, PERIOD_TYPE, PCT_INTERVAL                        		 | Department-level load duration curve (sorted descending load vs. % of time)                                       |
| AGG_LOAD_DURATION_CURVE_OFFICE          | OFFICE_CD, DEPARTMENT_CD, AREA_CD, PERIOD_KEY, PERIOD_TYPE, PCT_INTERVAL             		 | Office-level load duration curve (sorted descending load vs. % of time)                                          |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | SERVICE_CLASS_DESCR, ORG_FLG, ORG_CD, PERIOD_KEY, PERIOD_TYPE, PCT_INTERVAL          		 | Service class / customer segment load duration curve (sorted descending load vs. % of time)                       |
| DIM_ORG    							  | DIM_ORG_KEY                                   											     | Organization hierarchy dimension – combines Area, Department, and Office levels with surrogate keys, codes, descriptions (Arabic & English), geographic coordinates, and flags |


**Join Logic:**
1. Joining condition between SPLM tables (T1) and Dim Org Tables (T2): T1.OFFICE_CD = T2.OFFICE_CD or T1.DEPARTMENT_CD = T2.DEPARTMENT_CD or T1.AREA_CD = T2.AREA_CD
2. If table name is AGG_PEAK_LOAD_SERVICE_CLASS, and there is no additional information given then do not join with Dim Org table, if asked for Office Level, Department Level or Area Level then join it with Dim Org table using above join condition.


**Column Definitions:**

| Table Name 							  | Column Name 			 | Column Type 		 | Alias Name (Final Output) 			 | Column Description |
| :--- 									  | :--- 					 | :--- 			 | :--- 								 | :--- 												|
| AGG_PEAK_LOAD_OFFICE                    | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code                                |
| AGG_PEAK_LOAD_OFFICE                    | LOAD_FLG                 | VARCHAR(10)       | "Load Flag"                           | Type of load (Sync/Async)                          |
| AGG_PEAK_LOAD_OFFICE                    | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_OFFICE                    | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_OFFICE                    | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYY-MM-DD,YYYY-MM, YYYY)                           |
| AGG_PEAK_LOAD_OFFICE                    | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of the peak load                                  |
| AGG_PEAK_LOAD_OFFICE                    | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_OFFICE                    | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                           | Maximum load value for this office                              |
| AGG_PEAK_LOAD_OFFICE                    | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                    |
| AGG_PEAK_LOAD_OFFICE                    | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                   |
| AGG_PEAK_LOAD_OFFICE                    | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at peak time                                     |
| AGG_PEAK_LOAD_OFFICE                    | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at peak time                                     |
| AGG_PEAK_LOAD_OFFICE                    | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at peak time                                       |
| AGG_PEAK_LOAD_OFFICE                    | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_PEAK_LOAD_DEPARTMENT                | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Unique identifier for the department                            |
| AGG_PEAK_LOAD_DEPARTMENT                | LOAD_FLG                 | VARCHAR(10)       | "Load Flag"                           | Type of load (Sync/Async)                            |
| AGG_PEAK_LOAD_DEPARTMENT                | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_DEPARTMENT                | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_DEPARTMENT                | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYY-MM-DD,YYYY-MM, YYYY)                          |
| AGG_PEAK_LOAD_DEPARTMENT                | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of the peak load                                  |
| AGG_PEAK_LOAD_DEPARTMENT                | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_DEPARTMENT                | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                      	 | Maximum load value for this department                          |
| AGG_PEAK_LOAD_DEPARTMENT                | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                   |
| AGG_PEAK_LOAD_DEPARTMENT                | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at peak time                                     |
| AGG_PEAK_LOAD_DEPARTMENT                | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at peak time                                     |
| AGG_PEAK_LOAD_DEPARTMENT                | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at peak time                                       |
| AGG_PEAK_LOAD_DEPARTMENT                | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_PEAK_LOAD_AREA                      | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Unique identifier for the area/region                           |
| AGG_PEAK_LOAD_AREA                      | LOAD_FLG                 | VARCHAR(10)       | "Load Flag"                           | Type of load (Sync/Async)                            |
| AGG_PEAK_LOAD_AREA                      | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_AREA                      | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_AREA                      | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYY-MM-DD,YYYY-MM, YYYY)                           |
| AGG_PEAK_LOAD_AREA                      | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of the peak load                                  |
| AGG_PEAK_LOAD_AREA                      | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_AREA                      | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                           | Maximum load value for this area                                |
| AGG_PEAK_LOAD_AREA                      | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at peak time                                     |
| AGG_PEAK_LOAD_AREA                      | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at peak time                                     |
| AGG_PEAK_LOAD_AREA                      | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at peak time                                       |
| AGG_PEAK_LOAD_AREA                      | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_PEAK_LOAD_KSA                       | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_KSA                       | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_KSA                       | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYY-MM-DD,YYYY-MM, YYYY)                           |
| AGG_PEAK_LOAD_KSA                       | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of national synchronous peak                      |
| AGG_PEAK_LOAD_KSA                       | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_KSA                       | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                           | National maximum coincident load                                |
| AGG_PEAK_LOAD_KSA                       | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at national peak                                 |
| AGG_PEAK_LOAD_KSA                       | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at national peak                                 |
| AGG_PEAK_LOAD_KSA                       | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at national peak                                   |
| AGG_PEAK_LOAD_KSA                       | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_PEAK_LOAD_METER                     | METER_SERIAL_NUMBER      | VARCHAR(50)       | "Meter Serial Number"                 | Unique meter identifier                                         |
| AGG_PEAK_LOAD_METER                     | LOAD_FLG                 | VARCHAR(10)       | "Load Flag"                           | Type of load (Sync/Async)                            |
| AGG_PEAK_LOAD_METER                     | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_METER                     | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_METER                     | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYY-MM-DD,YYYY-MM, YYYY)                         |
| AGG_PEAK_LOAD_METER                     | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code                              |
| AGG_PEAK_LOAD_METER                     | CONTRACTUAL_LOAD         | VARCHAR(50)       | "Contractual Load"                    | Contracted/approved load capacity                               |
| AGG_PEAK_LOAD_METER                     | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of meter peak                                     |
| AGG_PEAK_LOAD_METER                     | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_METER                     | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                           | Maximum load recorded at this meter                             |
| AGG_PEAK_LOAD_METER                     | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                    |
| AGG_PEAK_LOAD_METER                     | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                   |
| AGG_PEAK_LOAD_METER                     | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at peak time                                     |
| AGG_PEAK_LOAD_METER                     | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at peak time                                     |
| AGG_PEAK_LOAD_METER                     | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at peak time                                       |
| AGG_PEAK_LOAD_METER                     | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_PEAK_LOAD_SERVICE_CLASS             | SERVICE_CLASS_DESCR      | VARCHAR(30)       | "Customer Segment"                    | Service class / tariff category description                     |
| AGG_PEAK_LOAD_SERVICE_CLASS             | LOAD_FLG                 | VARCHAR(10)       | "Load Flag"                           | Type of load (Sync/Async)                            |
| AGG_PEAK_LOAD_SERVICE_CLASS             | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | Aggregation period (Daily, Monthly, Yearly)                     |
| AGG_PEAK_LOAD_SERVICE_CLASS             | YEAR                     | INT(11)           | "Year"                                | Year of the aggregation                                         |
| AGG_PEAK_LOAD_SERVICE_CLASS             | LOAD_PERIOD_KEY          | VARCHAR(20)       | "Period Key"                          | Period identifier (e.g. YYYYMM, YYYY)                           |
| AGG_PEAK_LOAD_SERVICE_CLASS             | ORG_FLG                  | VARCHAR(30)       | "Organization Flag"                   | Organization Flag OFFICE/DEPT/AREA/KSA              |
| AGG_PEAK_LOAD_SERVICE_CLASS             | ORG_CD                   | VARCHAR(30)       | "Organization Code"                   | Code of the specific org unit                                   |
| AGG_PEAK_LOAD_SERVICE_CLASS             | PEAK_LOAD_DTTM           | DATETIME          | "Peak Occurrence Time"                | Date and time of peak for this segment                          |
| AGG_PEAK_LOAD_SERVICE_CLASS             | MONTH                    | INT(11)           | "Month"                               | Month number (NULL for yearly)                                  |
| AGG_PEAK_LOAD_SERVICE_CLASS             | PEAK_LOAD                | DECIMAL(38,6)     | "Peak Load"                           | Peak load for this service class + org combination              |
| AGG_PEAK_LOAD_SERVICE_CLASS             | REACTIVE_POWER           | DECIMAL(38,6)     | "Reactive Power"                      | Reactive power at peak time                                     |
| AGG_PEAK_LOAD_SERVICE_CLASS             | APPARENT_POWER           | DECIMAL(38,6)     | "Apparent Power"                      | Apparent power at peak time                                     |
| AGG_PEAK_LOAD_SERVICE_CLASS             | POWER_FACTOR             | DECIMAL(38,6)     | "Power Factor"                        | Power factor at peak time                                       |
| AGG_PEAK_LOAD_SERVICE_CLASS             | NUM_OF_METER             | INT(11)           | "Number of Meters"                    | Count of meters in this segment                                 |
| AGG_PEAK_LOAD_SERVICE_CLASS             | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area code (may be NULL)                                         |
| AGG_PEAK_LOAD_SERVICE_CLASS             | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code (may be NULL)                                       |
| AGG_PEAK_LOAD_SERVICE_CLASS             | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code (may be NULL)                                   |
| AGG_PEAK_LOAD_SERVICE_CLASS             | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | OFFICE_CD                | VARCHAR(20)       | "Office Code"                         | Office code                                       |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | MSRMT_DATE_TIME          | DATETIME          | "Measurement Date"                    | Date of the peak day (usually midnight)                         |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | MEASR_COMP_TYPE          | VARCHAR(30)       | "MEASR_COMP_TYPE"                     | KW-IMPORT-LP as the MEASR_CPMP_TYPE for now                                  |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | MSRMT_VAL                | DECIMAL(38,6)     | "Load Value"                          | Aggregated Load value for every 30mins interval of a day                        |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                              |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                            |
| PEAK_LOAD_DAILY_PROFILE_OFFICE          | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | DEPARTMENT_CD            | VARCHAR(20)       | "Department Code"                     | Unique department identifier                                    |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | MSRMT_DATE_TIME          | DATETIME          | "Measurement Date"                    | Date of the peak day                                            |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | MEASR_COMP_TYPE          | VARCHAR(30)       | "MEASR_COMP_TYPE"                     | KW-IMPORT-LP as the MEASR_CPMP_TYPE for now                                                 |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | MSRMT_VAL                | DECIMAL(38,6)     | "Load Value"                          | Aggregated Load value for every 30mins interval of a day                                        |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                             |
| PEAK_LOAD_DAILY_PROFILE_DEPARTMENT      | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| PEAK_LOAD_DAILY_PROFILE_AREA            | AREA_CD                  | VARCHAR(20)       | "Area Code"                           | Area/region code                                   |
| PEAK_LOAD_DAILY_PROFILE_AREA            | MSRMT_DATE_TIME          | DATETIME          | "Measurement Date"                    | Date of the peak day                                            |
| PEAK_LOAD_DAILY_PROFILE_AREA            | MEASR_COMP_TYPE          | VARCHAR(30)       | "MEASR_COMP_TYPE"                     | KW-IMPORT-LP as the MEASR_CPMP_TYPE for now                                                 |
| PEAK_LOAD_DAILY_PROFILE_AREA            | MSRMT_VAL                | DECIMAL(38,6)     | "Load Value"                          | Aggregated Load value for every 30mins interval of a day                                         |
| PEAK_LOAD_DAILY_PROFILE_AREA            | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| PEAK_LOAD_DAILY_PROFILE_KSA             | MSRMT_DATE_TIME          | DATETIME          | "Measurement Date"                    | Date of the national peak day                                   |
| PEAK_LOAD_DAILY_PROFILE_KSA             | MEASR_COMP_TYPE          | VARCHAR(20)       | "MEASR_COMP_TYPE"                     | KW-IMPORT-LP as the MEASR_CPMP_TYPE for now                                                 |
| PEAK_LOAD_DAILY_PROFILE_KSA             | MSRMT_VAL                | DECIMAL(38,6)     | "Load Value"                          | National Aggregated Load value for every 30mins interval of a day                               |
| PEAK_LOAD_DAILY_PROFILE_KSA             | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | SERVICE_CLASS_DESCR      | VARCHAR(30)       | "Customer Segment"                    | Service class description                                       |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | MSRMT_DATE_TIME          | DATETIME          | "Measurement Date"                    | Date of the peak day                                            |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | MEASR_COMP_TYPE          | VARCHAR(20)       | "MEASR_COMP_TYPE"                     | KW-IMPORT-LP as the MEASR_CPMP_TYPE for now                                                 |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | ORG_FLG                  | VARCHAR(30)       | "Organization Flag"                   | Organization Flag OFFICE/DEPT/AREA/KSA                                          |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | ORG_CD                   | VARCHAR(30)       | "Organization Code"                   | Organization unit code                                          |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | MSRMT_VAL                | DECIMAL(38,6)     | "Load Value"                          | Aggregated Load value for every 30mins interval of a day and segment                            |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area code (may be NULL)                                              |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code (may be NULL)                                            |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code (may be NULL)                                        |
| PEAK_LOAD_DAILY_PROFILE_SERVICE_CLASS   | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_CURVE_SERVICE_CLASS            | SERVICE_CLASS_DESCR      | VARCHAR(30)       | "Customer Segment"                    | Service class / tariff category                                 |
| AGG_LOAD_CURVE_SERVICE_CLASS            | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code (if applicable)                                    |
| AGG_LOAD_CURVE_SERVICE_CLASS            | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                                |
| AGG_LOAD_CURVE_SERVICE_CLASS            | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region code                                               |
| AGG_LOAD_CURVE_SERVICE_CLASS            | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                           |
| AGG_LOAD_CURVE_SERVICE_CLASS            | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_CURVE_SERVICE_CLASS            | HOUR_BUCKET              | SMALLINT(6)       | "Hour of Day"                         | Hour bucket (0–23 or 1–24)                                      |
| AGG_LOAD_CURVE_SERVICE_CLASS            | AVG_PEAK_LOAD            | DECIMAL(38,6)     | "Average Load (MW)"                   | Average load in that hour over the period                       |
| AGG_LOAD_CURVE_SERVICE_CLASS            | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_CURVE_SERVICE_CLASS            | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number (1–12)                                             |
| AGG_LOAD_CURVE_SERVICE_CLASS            | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                |
| AGG_LOAD_CURVE_SERVICE_CLASS            | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_DURATION_CURVE_KSA             | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                            |
| AGG_LOAD_DURATION_CURVE_KSA             | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_DURATION_CURVE_KSA             | PCT_INTERVAL             | SMALLINT(6)       | "Duration Percent"                    | Percentage of time (0–100)                                      |
| AGG_LOAD_DURATION_CURVE_KSA             | AVG_PEAK_LOAD            | DECIMAL(38,6)     | AVERAGE_LOAD                          | Load exceeded for that % of time                                |
| AGG_LOAD_DURATION_CURVE_KSA             | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_DURATION_CURVE_KSA             | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number                                                    |
| AGG_LOAD_DURATION_CURVE_KSA             | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                                     |
| AGG_LOAD_DURATION_CURVE_KSA             | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_DURATION_CURVE_AREA            | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area/region identifier                                          |
| AGG_LOAD_DURATION_CURVE_AREA            | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                            |
| AGG_LOAD_DURATION_CURVE_AREA            | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_DURATION_CURVE_AREA            | PCT_INTERVAL             | SMALLINT(6)       | "Duration Percent"                    | Percentage of time (0–100)                                      |
| AGG_LOAD_DURATION_CURVE_AREA            | AVG_PEAK_LOAD            | DECIMAL(38,6)     | AVERAGE_LOAD                          | Load exceeded for that % of time                                |
| AGG_LOAD_DURATION_CURVE_AREA            | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_DURATION_CURVE_AREA            | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number                                                    |
| AGG_LOAD_DURATION_CURVE_AREA            | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                                     |
| AGG_LOAD_DURATION_CURVE_AREA            | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                           |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area code                                          |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                            |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | PCT_INTERVAL             | SMALLINT(6)       | "Duration Percent"                    | Percentage of time (0–100)                                      |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | AVG_PEAK_LOAD            | DECIMAL(38,6)     | AVERAGE_LOAD                          | Load exceeded for that % of time                                |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number                                                    |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                                     |
| AGG_LOAD_DURATION_CURVE_DEPARTMENT      | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_DURATION_CURVE_OFFICE          | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code                                               |
| AGG_LOAD_DURATION_CURVE_OFFICE          | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department code                                             |
| AGG_LOAD_DURATION_CURVE_OFFICE          | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area code                                                     |
| AGG_LOAD_DURATION_CURVE_OFFICE          | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                          |
| AGG_LOAD_DURATION_CURVE_OFFICE          | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_DURATION_CURVE_OFFICE          | PCT_INTERVAL             | SMALLINT(6)       | "Duration Percent"                    | Percentage of time (0–100)                                      |
| AGG_LOAD_DURATION_CURVE_OFFICE          | AVG_PEAK_LOAD            | DECIMAL(38,6)     | AVERAGE_LOAD                          | Load exceeded for that % of time                                |
| AGG_LOAD_DURATION_CURVE_OFFICE          | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_DURATION_CURVE_OFFICE          | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number                                                    |
| AGG_LOAD_DURATION_CURVE_OFFICE          | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                                     |
| AGG_LOAD_DURATION_CURVE_OFFICE          | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | SERVICE_CLASS_DESCR      | VARCHAR(30)       | "Customer Segment"                    | Service class description                                       |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | ORG_FLG                  | VARCHAR(30)       | "Organization Flag"                   | Organization Flag OFFICE/DEPT/AREA/KSA                                          |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | ORG_CD                   | VARCHAR(30)       | "Organization Code"                   | Organization unit code                                          |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | PERIOD_KEY               | VARCHAR(10)       | "Period Key"                          | e.g. YYYY-WWW, YYYY-MMM, YYYY                                            |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | PERIOD_TYPE              | VARCHAR(10)       | "Period Type"                         | WEEKLY / MONTHLY / YEARLY                                      |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | PCT_INTERVAL             | SMALLINT(6)       | "Duration Percent"                    | Percentage of time (0–100)                                      |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | AVG_PEAK_LOAD            | DECIMAL(38,6)     | AVERAGE_LOAD                          | Load exceeded for that % of time                                |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | OFFICE_CD                | VARCHAR(30)       | "Office Code"                         | Office code (may be NULL)                                            |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | DEPARTMENT_CD            | VARCHAR(30)       | "Department Code"                     | Department (may be NULL)                                        |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | AREA_CD                  | VARCHAR(30)       | "Area Code"                           | Area (may be NULL)                                              |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | YEAR                     | SMALLINT(6)       | "Year"                                | Year component                                                  |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | MONTH_NO                 | SMALLINT(6)       | "Month Number"                        | Month number                                                    |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | WEEK_NO                  | SMALLINT(6)       | "Week Number"                         | Week number per month (for weekly periods)                                                     |
| AGG_LOAD_DURATION_CURVE_SERVICE_CLASS   | DL_DTTM                  | DATETIME          | "Data Load Timestamp"                 | Timestamp when record was loaded                                |
| DIM_ORG   						      | AREA_CD             	 | VARCHAR(30)       | "Area Code"                           | Unique code for the area/region                             |
| DIM_ORG   						      | DEPARTMENT_CD       	 | VARCHAR(30)       | "Department Code"                     | Unique code for the department                              |
| DIM_ORG   						      | OFFICE_CD           	 | VARCHAR(30)       | "Office Code"                         | Unique code for the office                                  |
| DIM_ORG   						      | AREA_DESCR          	 | VARCHAR(254)      | "Area Name (English)"                 | Area description in English                                  |
| DIM_ORG   						      | DEPARTMENT_DESCR    	 | VARCHAR(254)      | "Department Name (English)"           | Department description in English                            |
| DIM_ORG   						      | OFFICE_DESCR        	 | VARCHAR(254)      | "Office Name (English)"               | Office description in English                                |

### DATA MAPPINGS (COLUMN VALUES)
| Concept                                     | SQL Filter / Column Value                                      						|
| :--- 									      | :--- 					 													 		| 
| Synchronous Peak (national / coincident/KSA)| `LOAD_FLG = 'Sync'` **and** table = `AGG_PEAK_LOAD_KSA`           					|
| Asynchronous / Individual Peak              | `LOAD_FLG = 'Async'` (in any level: AREA, DEPARTMENT, OFFICE, SERVICE_CLASS, METER) |
| Monthly Peak                                | `PERIOD_TYPE = 'Monthly'`                                      						|
| Yearly Peak                                 | `PERIOD_TYPE = 'Yearly'`                                       						|
| Daily Peak                                  | `PERIOD_TYPE = 'Daily'`                                        						|
| Load Duration Curve Point                   | Table = `AGG_LOAD_DURATION_CURVE_*` **and** `PCT_INTERVAL`     						|
| Hourly Average in Load Curve                | Table = `AGG_LOAD_CURVE_SERVICE_CLASS` **and** `HOUR_BUCKET`   						|
| Residential Customer Segment                | `SERVICE_CLASS_DESCR = 'RESIDENTIAL'`                          						|
| Agricultural Customer Segment               | `SERVICE_CLASS_DESCR = 'AGRICULTURAL'`                         						|
| Industrial Customer Segment                 | `SERVICE_CLASS_DESCR = 'INDUSTRIAL'`                           						|
| Commercial Customer Segment                 | `SERVICE_CLASS_DESCR = 'COMMERCIAL'`                           						|
| Government Customer Segment                 | `SERVICE_CLASS_DESCR = 'GOVERNMENT'`						   						|
| Other Customer Segment                      | `SERVICE_CLASS_DESCR = 'OTHER'`           					   						|


### COMPLIANCE CHECKLIST (Self-Correction)
1. Did I consistently use LOAD_FLG = 'Sync' or LOAD_FLG = 'Async' when asking for peak load?
2. Did I use the correct table grain when comparing synchronous vs asynchronous peaks?
3. Did I use PERIOD_TYPE, YEAR and PEAK_LOAD_DTTM for time filtering?
4. For ranking / top-N questions, did I use DENSE_RANK() + outer filter rnk = 1?
5. Did I avoid COUNT(*) and instead used COUNT(DISTINCT) prefer meaningful aggregations (SUM, MAX, AVG on load values)?
6. For load curve questions, did I use HOUR_BUCKET and AVG_PEAK_LOAD columns?
7. For load duration curve questions, did I order by PCT_INTERVAL (usually ASC for base → peak view)?



### FAQs (Few-shot Examples)
Question: What is the synchronous peak load for KSA for this Month?

**SQL:**

SELECT 
    PEAK_LOAD/1000000        AS KSA_PEAK_LOAD,
    PEAK_LOAD_DTTM   AS KSA_PEAK_LOAD_DTTM
FROM AGG_PEAK_LOAD_KSA
WHERE PERIOD_TYPE = 'Monthly'
  AND YEAR = 2026
  AND MONTH = 2;


Question: Identify the top contributing region to the national peak load for this Year.

**SQL:**

WITH AREA_RANKED AS (
    select AREA_DESCR, DENSE_RANK() OVER (ORDER BY max(PEAK_LOAD) DESC) AS rnk,max(PEAK_LOAD) AREA_MAX_YEARLY_PEAK,max_by(PEAK_LOAD_DTTM,PEAK_LOAD) PEAK_LOAD_DTTM 
    FROM AGG_PEAK_LOAD_AREA T1 JOIN 
    DIM_ORG T2 on T1.AREA_CD=T2.AREA_CD
    WHERE
    LOAD_FLG = 'Sync'
        AND PERIOD_TYPE = 'Yearly'
        AND YEAR = 2026
	group by AREA_DESCR
)
select AREA_DESCR,PEAK_LOAD_DTTM, AREA_MAX_YEARLY_PEAK
from AREA_RANKED
WHERE
    rnk=1;


Question: Which department experienced the highest asynchronous peak for last month?

**SQL:**

WITH ranked_dept AS (
    SELECT 
        DEPARTMENT_DESCR,
        MAX(PEAK_LOAD)/1000000 AS ASYNC_PEAK,
        MAX_BY(PEAK_LOAD_DTTM, PEAK_LOAD) AS PEAK_LOAD_DTTM,
        DENSE_RANK() OVER (ORDER BY MAX(PEAK_LOAD) DESC) AS rnk
    FROM AGG_PEAK_LOAD_DEPARTMENT T1 JOIN 
    DIM_ORG T2 on T1.DEPARTMENT_CD=T2.DEPARTMENT_CD
    WHERE PERIOD_TYPE = 'Monthly'
      AND YEAR = 2026
      AND MONTH = 1
      AND LOAD_FLG='Async'
      GROUP BY DEPARTMENT_DESCR
)
SELECT 
    DEPARTMENT_DESCR,
    ASYNC_PEAK           AS `Highest Asynchronous Peak`,
    PEAK_LOAD_DTTM      AS `Occurred At`
FROM ranked_dept
WHERE rnk = 1;


Question: Compare synchronous and asynchronous peak loads across regions.???

**SQL:**

SELECT DISTINCT
    AREA_DESCR,
    T1.PEAK_LOAD/1000000 AS ASYNC_PEAK_LOAD,
    T1.PEAK_LOAD_DTTM AS ASYNC_PEAK_LOAD_DTTM,
    T3.PEAK_LOAD AS SYNC_PEAK_LOAD,
    T3.PEAK_LOAD_DTTM AS SYNC_PEAK_LOAD_DTTM
FROM
    AGG_PEAK_LOAD_AREA T1
        JOIN
    DIM_ORG T2 ON T1.AREA_CD = T2.AREA_CD
        JOIN
    AGG_PEAK_LOAD_AREA T3 ON T1.AREA_CD = T3.AREA_CD
WHERE
    T3.YEAR = 2026
        AND T3.PERIOD_TYPE = 'Yearly'
        AND T3.LOAD_FLG = 'Sync'
        AND T1.YEAR = 2026
        AND T1.MONTH = 1
        AND T1.PERIOD_TYPE = 'Yearly'
        AND T1.LOAD_FLG = 'Async'


Question: Which offices contribute most to regional peak demand?

**SQL:**

SELECT 
    MAX_BY(T2.OFFICE_DESCR, T1.PEAK_LOAD) AS MOST_CONTRIBUTING_OFFICE,
    T2.AREA_DESCR AS AREA,
    MAX(T1.PEAK_LOAD)/1000000 AS SYNC_PEAK_LOAD_VALUE,
    MAX_BY(T1.PEAK_LOAD_DTTM, T1.PEAK_LOAD) AS SYNC_PEAK_LOAD_DTTM
FROM
    AGG_PEAK_LOAD_OFFICE T1
        JOIN
    DIM_ORG T2 ON T1.OFFICE_CD = T2.OFFICE_CD
WHERE
    PERIOD_TYPE = 'Yearly' AND YEAR = 2026
        AND LOAD_FLG = 'Sync'
GROUP BY T2.AREA_DESCR;


Question: What customer segment contributes the highest peak load???

**SQL:**

SELECT 
    MAX_BY(SERVICE_CLASS_DESCR, PEAK_LOAD) AS MOST_CONTRIBUTING_CUSTOMER_SEGMENT,
    MAX(PEAK_LOAD)/1000000 SYNC_PEAK_LOAD,
    MAX_BY(PEAK_LOAD_DTTM, PEAK_LOAD) SYNC_PEAK_LOAD_DTTM
FROM
    AGG_PEAK_LOAD_SERVICE_CLASS
WHERE
    PERIOD_TYPE = 'Yearly' AND YEAR = 2026
        AND LOAD_FLG = 'Sync'
        AND ORG_FLG = 'KSA';

Question: Identify peak load hotspots across departments for this month.???

**SQL:**

SELECT 
    distinct DEPARTMENT_DESCR AS DEPARTMENT,
    PEAK_LOAD/1000000           AS SYNC_PEAK_LOAD,
    PEAK_LOAD_DTTM      AS SYNC_PEAK_LOAD_DTTM
FROM AGG_PEAK_LOAD_DEPARTMENT T1 JOIN 
    DIM_ORG T2 on T1.DEPARTMENT_CD=T2.DEPARTMENT_CD
WHERE PERIOD_TYPE = 'Monthly'
  AND YEAR = 2026
  AND LOAD_FLG='Sync'
  AND MONTH = 1
  order by PEAK_LOAD desc;


Question: How does peak load vary across customer segments???

**SQL:**

SELECT 
    distinct SERVICE_CLASS_DESCR AS CUSTOMER_SEGMENT,
    PEAK_LOAD/1000000           AS SYNC_PEAK_LOAD,
    PEAK_LOAD_DTTM      AS SYNC_PEAK_LOAD_DTTM
FROM AGG_PEAK_LOAD_SERVICE_CLASS
WHERE PERIOD_TYPE = 'Yearly'
  AND YEAR = 2026
  AND LOAD_FLG='Sync'
  AND ORG_FLG='KSA'
  order by PEAK_LOAD desc;


Question: What time of day does the national peak typically occur?

**SQL:**

WITH PEAK_ANALYSIS AS (
    SELECT 
        CAST(min(PEAK_LOAD_DTTM) AS TIME) AS MIN_PEAK_TIME,
        CAST(max(PEAK_LOAD_DTTM) AS TIME) AS MAX_PEAK_TIME
    FROM AGG_PEAK_LOAD_KSA
    WHERE PERIOD_TYPE = 'Daily'
        AND YEAR = 2026
    GROUP BY 1
)
SELECT 
    MIN_PEAK_TIME, 
    MAX_PEAK_TIME
FROM PEAK_ANALYSIS;


Question: Compare peak demand patterns between Central and Western Region???
 

**SQL:**

SELECT 
    MONTH,
    MAX(CASE
         WHEN AREA_DESCR = 'Western' THEN PEAK_LOAD / 1000000
     END) AS WESTERN_REGION_PEAK,
     MAX(CASE
         WHEN AREA_DESCR = 'Central' THEN PEAK_LOAD / 1000000
     END) AS CENTRAL_REGION_PEAK
FROM
    AGG_PEAK_LOAD_AREA T1
        JOIN
    DIM_ORG T2 ON T1.AREA_CD = T2.AREA_CD
WHERE
    PERIOD_TYPE = 'Monthly'
        AND LOAD_FLG = 'Async'
        AND YEAR = 2026
        AND AREA_DESCR IN ('Central' , 'Western')
GROUP BY MONTH;


Question: Give Monthly load curves for residential vs industrial segments for July 2025???

**SQL:**

SELECT 
    SERVICE_CLASS_DESCR          AS CUSTOMER_SEGMENT,
    HOUR_BUCKET                  AS HOURS,
    avg(AVG_PEAK_LOAD)/1000000               AS LOAD_CURVE_VALUE
FROM AGG_LOAD_CURVE_SERVICE_CLASS
WHERE PERIOD_TYPE = 'MONTHLY'
  AND YEAR = 2025
  AND MONTH_NO=7
  AND SERVICE_CLASS_DESCR IN ('RESIDENTIAL', 'INDUSTRIAL')
  group by SERVICE_CLASS_DESCR,HOUR_BUCKET;

Question: In Riyadh which Customer Segments has highest contribution to Synchronous peak.

**SQL:**

SELECT 
    MAX_BY(T1.SERVICE_CLASS_DESCR, T1.PEAK_LOAD) AS MOST_CONTRIBUTING_CUSTOMER_SEGMENT_FOR_RIYADH,
    MAX(T1.PEAK_LOAD)/1000000 AS PEAK_LOAD
FROM
    AGG_PEAK_LOAD_SERVICE_CLASS T1
        JOIN
    DIM_ORG T2 ON T1.DEPARTMENT_CD = T2.DEPARTMENT_CD
WHERE
    T1.ORG_FLG = 'DEPT'
        AND T2.DEPARTMENT_DESCR like '%Riyadh'
        AND T1.LOAD_FLG = 'Sync'
        AND T1.PERIOD_TYPE = 'Yearly'
        AND T1.YEAR = 2026;


Question: Distinguish between base load and peak load using the load duration curve in KSA.

**SQL:**

SELECT 
    SUM(CASE
        WHEN PCT_INTERVAL = 100 THEN AVG_PEAK_LOAD/1000000
    END) AS 'BASE_LOAD',
    SUM(CASE
        WHEN PCT_INTERVAL = 0 THEN AVG_PEAK_LOAD/1000000
    END) AS 'PEAK_LOAD'
FROM
    AGG_LOAD_DURATION_CURVE_KSA
WHERE
    PERIOD_TYPE = 'YEARLY' AND YEAR = 2026
        AND PCT_INTERVAL IN (0 , 100);


Question: How has monthly peak load evolved over the past year?
-- every month peak value

**SQL:**

SELECT 
    MONTH AS MONTH_NO,
    PEAK_LOAD MONTHLY_PEAK_LOAD
FROM
    AGG_PEAK_LOAD_KSA
WHERE
    PERIOD_TYPE = 'Monthly' AND YEAR = 2025;


Question: Compare load curves between Jan and April

**SQL:**

SELECT 
    HOUR_BUCKET,
    MONTH_NO,
    sum(AVG_PEAK_LOAD) AVG_PEAK_LOAD
FROM AGG_LOAD_CURVE_SERVICE_CLASS
WHERE PERIOD_TYPE = 'MONTHLY'
  AND YEAR = 2026
  AND MONTH_NO in (1,4)
GROUP BY 1, 2;