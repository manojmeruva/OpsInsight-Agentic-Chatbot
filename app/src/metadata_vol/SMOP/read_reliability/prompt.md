Mandatory SQL Rules
	1. Column Referencing: Use column sequence numbers for all GROUP BY and ORDER BY clauses (e.g., GROUP BY 1, 2).
	2. Ranking Logic: For any "Top," "Highest," or "Best" queries, you must use a CTE with a RANK() or DENSE_RANK() function.
		The final output must filter using WHERE rnk = 1.
	3. Aliasing: * Use snake_case for internal subqueries or CTE aliases.
		Use Friendly Names with Spaces in double quotes for final SELECT headers (e.g., "Total Reads").
	4. Time Filtering: Use CURRENT_DATE for "today" or "current" comparisons unless a specific date is mentioned.

Database Schema & Relationships
	
	Table Name					Primary Grain (Keys)										Description
	MVW_ACTIVE_METER_TRACK		"DA_DATE, OFFICE_CD"										Snapshot of active meters at a specific time.
	MVW_IMD_STATS				"OFFICE_CD, IMD_TO_DTTM, MEASR_COMP_TYPE_CD"					Aggregated volume/success counts for Reads.
	MVW_IMD_ERROR_STATS			"OFFICE_CD, IMD_TO_DTTM, MEASR_COMP_TYPE_CD, ERROR_MESSAGE"	Detailed breakdown of failure reasons.
	DIM_ORG						"OFFICE_CD"													Organization Table. Contains Area, Department
	INITIAL_MEASUREMENT_DATA_VW	"INIT_MSRMT_DATA_ID"										Raw table contains meter level information.
	
Join Logic:
	Organization mapping: Join on OFFICE_CD.
	Active Meter Tracking to Stats: Join on OFFICE_CD AND DA_DATE = IMD_TO_DTTM.
	Stats to Errors: Join on OFFICE_CD, IMD_TO_DTTM, and MEASR_COMP_TYPE_CD.
	Warning: The relationship between Stats and Errors is One-to-Many. Use SUM() carefully when joining to avoid duplicating volume counts.

Domain Knowledge (The IMD Lifecycle)
	Reads (IMD): Move from PENDING → VEE → COMPLETE/FINALIZED or ERROR/EXCEPTION.
	IMD_TO_DTTM: This is the date the read was actually taken (the "End Date"), not necessarily when it was received by the system.
	Metric Usage: * Use MVW_IMD_STATS for general volume and finalized counts.
		Use MVW_IMD_ERROR_STATS only when specific error messages are requested.
	Area is also refered as Region
	"MDS Error or negative consumption" in ERROR_MESSAGE column indicates Critical Validation Error

Meter Level Data Fetch Rule:
	INITIAL_MEASUREMENT_DATA_VW table should be used only when Meter level data is asked. 
	

Table: MVW_ACTIVE_METER_TRACK  	

Column Name				Type				Alias					Description
DA_DATE					TIMESTAMP			Snaphot 				Date & time	Indicates the time when device intallation status is captured is taken
OFFICE_CD				TEXT				Office Code				Office Code
HEAD_END_SYS			TEXT				Head End System Code	Head End System Code
HEAD_END_SYS_DESC		TEXT				Head End System			Head End System
ACTIVE_METERS			INTEGER				Active Meter Count		Number of Meters active at given time


Table: MVW_IMD_STATS  		

Column Name					Type			Alias										Description
OFFICE_CD					TEXT			Office Code									Office Code
IMD_TO_DTTM      				TIMESTAMP		IMD End Date								Date for which record/IMD received. For eg> IMD 'x100' is received by system on 5th Jan but this IMD is for 1st Jan. So 1st Jan is IMD T Date
MEASR_COMP_TYPE_CD			TEXT			Measuring Component Type					Measuring Component Type or Register Type
DATA_SRC_FLG				TEXT			Data Source Flag							Indicates from which system, record/IMD is received
HES_END_SYS					TEXT			Head End System								Head End System
READ_RECEIVED_METER			INTEGER			Number of Meters Received Reads				It stores number of meters have received reads on a given date.
ERROR_METER_COUNT			INTEGER			Number of Meters have Reads in Error		Indicates Number of meters have reads in error status
READINGS_COUNT				INTEGER			Total Number of Reads Received				Total Number of Reads Received
ERROR_READING_COUNT			INTEGER			Number of Reads in Error					Indicates Number of reads in error status
FINALIZED_READING_COUNT		INTEGER			Number of Reads Finalized					Indicates Number of Reads finalized/completed
FINALIZE_METER_COUNT		INTEGER			Number of  Meters have finalized reads		Number of  Meters have finalized reads

Table: MVW_IMD_ERROR_STATS  		

Column Name					Type			Alias										Description
OFFICE_CD					TEXT			Office Code									Office Code
IMD_TO_DTTM					TIMESTAMP		IMD End Date								Date for which record/IMD received. For eg> IMD 'x100' is received by system on 5th Jan but this IMD is for 1st Jan. So 1st Jan is IMD T Date
MEASR_COMP_TYPE_CD			TEXT			Measuring Component Type					Measuring Component Type or Register Type
ERROR_MESSAGE				TEXT			Error Message								Error Description
READINGS_COUNT				INTEGER			Total Number of Reads Received				Total Number of Reads Received
NO_OF_METERS				INTEGER			Total Number of  Meters 					Number of  Meters have finalized reads
HEAD_END_SYS				TEXT			Head End System								Head End System

Table: DIM_ORG

Column Name					Type			Alias										Description
OFFICE_CD					TEXT			Office Code									Office Code
OFFICE_DESCR 				TEXT			Office Name									Office Name
AREA_CD						TEXT			Area Code									Area Name
AREA_DESCR					TEXT			Area Name									Area Name
DEPARTMENT_CD				TEXT			Department Code								Department Code
DEPARTMENT_DESCR			TEXT			Department Name								Department Name

Table: INITIAL_MEASUREMENT_DATA_VW

Column               Type       	Alias Column                    Description
AREA_CD              INTEGER    	Area Code                       Code representing the geographic area (e.g. 1, 2, 3, 4)
AREA_CD_DESCR        TEXT       	Area name                       Description of the area (e.g. Central, East, West, South)
CRE_DTTM             TIMESTAMP  	Read Creation Date & Time       Date and time when the read activity is created
D1_DEVICE_ID         INTEGER    	Device ID                       Primary identifier for tracking meter readings and measurements
DATA_SRC_FLG         TEXT       	Data Source Flag                Initial measurement data source flag
DEPARTMENT_CD        INTEGER    	Department Code                 Code representing the department within the area (e.g. 1500, 2200, 1100, 2500)
DEPARTMENT_CD_DESCR  TEXT       	Department Name                 Description of the department (e.g. ELECTRICITY ADMINISTRATION HAIL, ELECTRICITY ADMINISTRATION JEDDAH)
DEVICE_CONFIG_ID     INTEGER    	Device Configuration ID         Identifier representing a specific configuration of a physical meter device
ERROR_MESSAGE        TEXT       	Error Message                   Reasons for error or failure
HEAD_END_SYS         TEXT       	Head End System                 Head-end system identifier (HES). Values: SCHN, NARI
IMD_CONSUMPTION      INTEGER    	Consumption                     Initial measurement consumption
IMD_END_READ         INTEGER    	End Reading                     Initial measurement ending read value
IMD_FROM_DTTM        TIMESTAMP  	Read Start Date & Time          Start date/time of IMD (ignore when IMD_TO_DTTM is available)
IMD_MSRMT_COND       INTEGER    	Reads Quality code              Measurement condition code indicating source/quality (e.g. Regular, Missing, Estimated)
IMD_START_READ       INTEGER    	Start Reading                   Initial measurement starting read value
IMD_STATUS           TEXT       	Read Status                     IMD processing status: COMPLETE, ERROR, VEEEXCP, DISCARDED, REMOVE
IMD_TO_DTTM         TIMESTAMP  	Read To Date & Time             IMD end date/time (used as read date). Use CRE_DTTM for “received on date” questions
IMD_UOM              TEXT       	Unit of Measure                 Unit of measure (e.g. KWH, KVAH, KW, KWH-EXPORT, etc.)
INIT_MSRMT_DATA_ID   VARCHAR    	Read Identifier                 Unique identifier for each Initial Measurement Data (IMD) record
MEASR_COMP_ID        INTEGER    	Measuring Component ID          Measuring component or channel identifier
MEASR_COMP_TYPE_CD   TEXT       	Measuring Component Type        Measuring component type (e.g. KWH-IMPORT, KWH-EXPORT, PF-IMPORT)
MTR_MNFR             TEXT       	Meter Manufacturer              Meter manufacturer code (e.g. ITRON, GA)
MTR_SERIAL_NBR       VARCHAR    	Meter Serial Number             Serial number of the smart meter
OFFICE_CD            INTEGER    	Office Code                     Code representing the specific office within the department
OFFICE_CD_DESCR      TEXT       	Office Name                     Description of the office (e.g. AD DAMMAM SERVICE OFFICE)
STATUS_UPD_DTTM      TIMESTAMP  	Status Last Update Date & Time  Date and time when the IMD status was last updated


### FAQs (Few-shot Examples) ###
Question                                                                      SQL
How many total read requests were received across in kharj department today?  SELECT 
																					SUM(s.READINGS_COUNT) AS "Total Read Requests Today"
																				FROM MVW_IMD_STATS s
																				JOIN DIM_ORG o ON s.OFFICE_CD = o.OFFICE_CD
																				WHERE o.DEPARTMENT_DESCR LIKE '%KHARJ%'
																				  AND s.IMD_TO_DTTM = CURRENT_DATE;

How many total read requests were processed successfully today?               SELECT 
																				SUM(FINALIZED_READING_COUNT) AS "Total Successful Reads"
																			  FROM MVW_IMD_STATS
																			  WHERE IMD_TO_DTTM = CURRENT_DATE;


How many total read requests have failed today?                               SELECT 
																					SUM(ERROR_READING_COUNT) AS "Total Failed Reads"
																				FROM MVW_IMD_STATS
																				WHERE IMD_TO_DTTM = CURRENT_DATE;

How many total reads received on 17th Dec 2025                                SELECT 
																					SUM(READINGS_COUNT) AS "Total Reads Received"
																				FROM MVW_IMD_STATS
																				WHERE IMD_TO_DTTM = '2025-12-17';

Give me last 7 days consumption for a meter 'AEL202018976'					SELECT 
																				IMD_TO_DTTM AS "Read Date", 
																				IMD_CONSUMPTION AS "Consumption"
																			FROM INITIAL_MEASUREMENT_DATA_VW
																			WHERE MTR_SERIAL_NBR = 'AEL202018976'
																			  AND IMD_TO_DTTM >= CURRENT_DATE - INTERVAL '7 days'
																			ORDER BY 1 DESC;