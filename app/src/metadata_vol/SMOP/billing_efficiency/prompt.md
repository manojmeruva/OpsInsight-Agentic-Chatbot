Database Schema & Relationships
	
	Table Name							Primary Grain (Keys)										Description
	MVW_BILLING_EFFICIENCY_DATA_L		"D1_USAGE_ID, BILL_CYCLE_CD"								Contains the information of MRO lifecycle. This contains multiple D1_USAGE_ID for BILL_CYC_CD.
	FACT_ACTIVITY						"ACTIVITY_ID, ACTIVITY_TYPE_CD"								This table stores data for "Missing Read notifications".
	FACT_COMMUNICATION					"COMMUNICATION_ID, ACTIVITY_ID"								This is the child table of FACT_ACTIVITY which stores response received for Missing read Notifications.
	DIM_COMMUNICATION_STATUS			"COMM_STATUS_KEY, COMM_STATUS_CD"							This is a Dimension table stores Communication Status Description.
	DIM_USAGE							"USAGE_ID, SRCH_CHAR_VAL, SEQ_NUM"							Dimension table stores Usage (Billing Request) and Meter reason code mapping.
	DIM_MTR_READ_RZN					"FIELD_NAME, FIELD_VALUE"									Dimension table contains Meter Read Reason Code Description in FIELD_DESCR
	
Join Logic:
	- Billing Efficiency Data to Fact Activity (Missing Read Notification): MVW_BILLING_EFFICIENCY_DATA_L B LEFT OUTER Join FACT_ACTIVITY A ON T1.D1_USAGE_ID=T2.USAGE_ID
	- Fact Activity (Missing Read Notification) to Fact Communication ((Missing Read Notification Response): FACT_ACTIVITY A LEFT OUTER JOIN FACT_COMMUNICATION C ON A.ACTIVITY_ID=C.ACTIVITY_ID.
	- Fact Communication (Missing Read Notification Response) to Communication Status: Join on COMM_STATUS_KEY.
	- Dimension Usage to Fact Activity (Missing Read Notification): Join on USAGE_ID
	- Meter Read Reaon Dimension to Usage Dimension: Join on DIM_USAGE Y JOIN DIM_MTR_READ_RZN M ON U.SRCH_CHAR_VAL=M.FIELD_VALUE
	- Warning: The relationship between Fact Activity and Fact Communication is One-to-Many. Use SUM() carefully when joining to avoid duplicating volume counts.



**Core Domain Logic:**
- MRO Identification: Use COUNT(DISTINCT D1_USAGE_ID) for all counts of Usage Requests/MROs.
- BILL_CYCLE_CD Hint: A unique identifier for a predefined "Billing Batch/Bucket" of customers whose meters are read and billed simultaneously.
- Efficiency Metric: 
	- Success: USAGE_STATUS_CD IN ('SENT', 'ACKRECEIVED')
	- Failure: USAGE_STATUS_CD = 'DISCARDED'
- Billing Efficiency Definition: This is the success rate of all MROs (Meter Reading Orders) generated for specific billing batches/cycles
	- Efficiency formula: (count of distinct success MROs* 100)/(total count of distinct MROs)
- Billing Cycle Stages:
	- Pending: Current Date < WINDOW_START_DT.
	- Active: Current Date between WINDOW_START_DT and WINDOW_START_DT + 4 days.
	- Finalized/Closed: Current Date > WINDOW_START_DT + 4 days (matches WINDOW_END_DT).
	
- Sub Domain: Missing Read Notifications & Work Orders
	Description: When a Billing Request, MRO, or Usage Request fails, it triggers a "Missing Read Notification" activity.
	Key Identifiers & Filtering: 
		- Activity Type: Missing Read Notification activities are identified by ACTIVITY_TYPE_CD = 'CM-MISSING-MTR-RD'
		- Communication Object: Responses from the SMOC team are stored with COMMUNICATION_OBJECT = 'CM-MissingMtrRdNtf'.
		- Table Mapping: Work order details are stored in the FACT_COMMUNICATION table.
	Business Logic: Status Categorization: 
		- Completed by Probe: WO_DESCR_CD = 2139 AND WO_STATUS = 'COMP'
		- Completed by FT (Field Technician): WO_DESCR_CD = 2140 AND WO_STATUS = 'COMP'.
		- Completed Remotely: WO_DESCR_CD = 2141 AND WO_STATUS = 'COMP'.
		- Failed Work Order: WO_STATUS = 'FAILED'.
		- In Progress Notification: STATUS = 'COMMINPROG'.
	  
	
	
**Strict Query Construction Rules:**
- Temporal Filtering (Mandatory)
	- Rule: If the user query mentions a specific month or year (e.g., "Jan 2026"), you MUST use MRO_MONTH and MRO_YEAR.
	- Forbidden: Do not use WINDOW_START_DT or WINDOW_END_DT for calendar month/year filtering.
	- Correct Syntax: WHERE MRO_MONTH = 1 AND MRO_YEAR = 2026
	- When no date is provided then consider current month in filter criteria
	- When no year is provided then consider current year in filter criteria
	- Date Comparison Rule: Use CURRENT_DATE for all "current" or "today" comparisons (e.g., active billing cycles, pending cycles). Do not use CURRENT_TIMESTAMP unless specific hour/minute precision is requested.	
- Logic constraints
	- WINDOW_START_DT is restricted to calculating "Cycle Stages" (Pending/Active) or identifying "Periodic" vs "Off-Cycle" requests
- Ordering & Grouping
	- Rule: Use column sequence numbers for all GROUP BY and ORDER BY clauses.
	- Example: SELECT AREA_DESCRIPTION, COUNT(DISTINCT D1_USAGE_ID) FROM ... GROUP BY 1 ORDER BY 2 DESC

- Tie-Breaking & Ranking
	- Rule: For "top," "best," or "highest," use RANK() or DENSE_RANK() in a subquery.	
	- Requirement: The final filter must be WHERE rnk = 1 to ensure all tied entities are displayed.
- Aliasing & Formatting
	- Internal Aliases: Use underscores (e.g., success_count) in subqueries.
	- External Aliases: Use user-friendly names with spaces and double quotes (e.g., "Total Success Count") only in the final SELECT.
- String Matching Rule: 
	- When filtering by DEPARTMENT_DESCRIPTION, OFFICE_DESCRIPTION, or AREA_DESCRIPTION, always use the LIKE operator with wildcards (%) and TRIM(UPPER(...)) to ensure case-insensitive partial matching.
		Example: WHERE TRIM(UPPER(DEPARTMENT_DESCRIPTION)) LIKE '%KHARJ%'


### TABLES ###							
Table: MVW_BILLING_EFFICIENCY_DATA_L 

### COLUMNS ###
Database Column				Type			Alias Name								Description
CONSUMPTION					DECIMAL			Consumption								Energy consumed by customer in kWh
D1_USAGE_ID					TEXT			Usage ID								Unique identifier for each usage/MRO request. Use DISTINCT count
CREATION_DATE_TIME			TIMESTAMP		Usage Request Creation Date/Time		The date and time when the usage record was logged
STATUS_UPDATE_DATE_TIME		TIMESTAMP		Usage Request Status Update Date/Time	Date/time of usage status change
USAGE_START_DATE_TIME		TIMESTAMP		Usage Start Date/Time					Start of usage request period
USAGE_END_DATE_TIME			TIMESTAMP		Usage End Date/Time						End of usage request period
REGISTER_TYPE				TEXT			Register Type							Biling Register for which usage is requested
USAGE_STATUS_CD				TEXT			Usage Status Code						Success: ('ACKRECEIVED', 'SENT'). Failure: ('DISCARDED')
USAGE_STATUS				TEXT			Usage Status							Description of Usage request or MRO 
US_TYPE_CD					TEXT			Usage Subscription Type Code			Usage Subscription type code
US_TYPE_DESC				TEXT			Usage Subscription Type					Usage Subscription type description
SERVICE_TYPE				TEXT			Service Type							eg. Electric, Water
SERVICE_PROVIDER			TEXT			Service Provider						Company providing service
US_ID						TEXT			Usage Subscription ID					Usage subscription Identifier
US_STATUS					TEXT			Usage Subscription Status				Status of usage subscription
ACCOUNT_NBR					TEXT			Accout Number							Account number of customer
CITY						TEXT			City									City
STATE						TEXT			State									State
COUNTRY						TEXT			Country									Country
NET_MTR_CUST_FLG			TEXT			Net Meter Customer Flag					Indicates if customer is Net-Metering
GEO_LATITUDE				DECIMAL			Latitude								Latitude
GEO_LONGITIDE				DECIMAL			Longitude								Longitude
CUSTOMER_CLASS_CD			INTEGER			Customer Class Code						Code representing the customer class
CUSTOMER_CLASS_DESCR		TEXT			Customer Class 							eg. Residential, Commercial, Industrial, Government etc
MDM_SP_ID					TEXT			Service Point ID						Service Point where meter is installed
AREA_CD						TEXT			Area Code								Geographic area code (1,2,3,4 )
OFFICE_CD					TEXT			Office Code								Specific office within the department(like: 1511,2208,1140,1110,2502,1640,1340,4224,3430,2304,3540,..)
DEPARTMENT_CD				TEXT			Department Code							Department within the area.(like: 1500,2200,1100,2500,1600,1300,...)
AREA_DESCRIPTION			TEXT			Area Name								'Central','East','West','South'
OFFICE_DESCRIPTION			TEXT			Office Name								Name of the service office (like: 'AD DAMMAM SERVICE OFFICE','AD DAMMAM WEST SERVICE OFFICE','AD DUWADIMI ELECTRICITY-AD DUWADIMI SERVICE OFFICE',...)
DEPARTMENT_DESCRIPTION		TEXT			Department Name							 the department (like: 'ELECTRICITY ADMINISTRATION HAIL','ELECTRICITY ADMINISTRATION JEDDAH',..)
USAGE_EXCP_TYPE_CD			TEXT			Usage Error Type Code					Code representing the type of usage exception. Values: 'MSRMT-RETRIEVAL','CONFIGURATION','INVAILD-DATA'
USAGE_EXCP_TYPE				TEXT			Usage Error Type						Description of type of usage exception
EXCP_SEVERITY_FLG			TEXT			Error Severity Type						Error/Exception severity flag. Values: 'D1IF', 'D1IS', 'D1TM'
OPEN_CLOSE_FLG				TEXT			Error Open/Close Flag					Indicates if error/exception is open or closed
ERROR_MESSAGE				TEXT			Error Message							Failure reason for status not in success list
BILL_CYCLE_CD				TEXT			Bill Cycle code							A unique batch identifier for simultaneous reading/billing
WINDOW_START_DT				TIMESTAMP		Bill Cycle Window Start Date			Scheduled start date. Used for stages/classification
WINDOW_END_DT				TIMESTAMP		Bill Cycle Window End Date				Scheduled end date (WINDOW_START_DT + 4)
METER_SERIAL_NUMBER			TEXT			Meter Serial Number						Unique identifier for the meter
MANUFACTURER_CD				TEXT			Meter Manufacturer Code					e.g 'ITRON','GA'
MTR_MANFR_DESC				TEXT			Meter Manufacturer						Name of meter manufacturer
HEAD_END_SYS				TEXT			Head End System Code					'SCHN','NARI' 
HEAD_END_SYS_DESC			TEXT			Head End System Name					Name of head End System
IE_STATUS_DESCR				TEXT			Installation Status						Meter installation status
MRO_MONTH					INTEGER			MRO Month								Primary Filter for all monthly requests
MRO_YEAR					INTEGER			MRO Year								Primary Filter for all yearly requests

Table: FACT_ACTIVITY 

### COLUMNS ###
Database Column				Type			Alias Name								Description
ACTIVITY_ID					TEXT			Activity ID								Activity ID
ACTIVITY_CRE_DTTM			datetime		Activity Creation Date & Time			The date and time when the activity record was logged
ACTIVITY_TYPE_CD			TEXT			Activity Type Code						"Code for activity type (e.g. CM-MISSING-MTR-RD)"
STATUS						TEXT			Activity Status							"Current status (e.g. COMPLETED,COMERROR,COMINPROG)"
ACTIVITY_START_DTTM			datetime		Activity Start Date & Time				The date and time when the activity started
ACTIVITY_END_DTTM			datetime		Activity Completion Date & Time			The date and time when the activity ended
DEVICE_ID					TEXT			Device ID								Device ID
METER_READ_DTTM				datetime		Meter Read Time 						Time when meter was read and reading was sent
ACTIVITY_EXPIRATION_DTTM	datetime		Activity Exiration Time					Date and time when activy expires.
USAGE_ID					TEXT			Usage ID								Usage ID or MRO ID

Table: FACT_COMMUNICATION 

### COLUMNS ###
Database Column					Type			Alias Name								Description
COMMUNICATION_ID				TEXT			Communication ID						Communication ID
ACTIVITY_ID						TEXT			Activity ID								Activity ID
COMMUNICATION_OBJECT			TEXT			Communication Object					Communication Object
COMMUNICATION_CREATION_DTTM		TIMESTAMP		Communication Created Date & Time		Date and time communication record was created
COMM_STATUS_KEY					TEXT			Communication Status Key				Communication Status Key	
WO_NBR							TEXT			Work Order Numbner						Work Order Numbner
WO_STATUS						TEXT			Work Order Status						Current status: OPEN, COMP (Complete), INPROG, FAILED, REASSIGN.
WO_DESCR						TEXT			Work Order Description					Detailed description of the status
WO_DESCR_CD						TEXT			Work Order Description Code				Numeric code representing the specific resolution type.
WO_ACTUAL_FINISH_TIME			TIMESTAMP		Work Order Completion Time				Timestamp when the work order was finished.


Table: DIM_COMMUNICATION_STATUS

### COLUMNS ###
Database Column					Type			Alias Name								Description
COMM_STATUS_CD					TEXT			Communication Status					Communciation Status Code
COMM_STATUS_KEY					TEXT			Communication Status Key				Communication Status Key
COMM_STATUS_DESCR				TEXT			Communication Status Description		Communciation Status Description

Table: DIM_USAGE  

### COLUMNS ###
Database Column					Type			Alias Name								Description
USAGE_ID						TEXT			Usage ID								Usage ID
SEQ_NUM							INTEGER			Sequence Number							Sequence Number
SRCH_CHAR_VAL					TEXT			Meter Read Reason Code					Meter Read Reason Code

Table: DIM_MTR_READ_RZN 

### COLUMNS ###
Database Column					Type			Alias Name								Description
FIELD_NAME						TEXT			Field Name								Field name
FIELD_VALUE						TEXT			Meter Read Reason Code					Meter Read Reason Code
FIELD_DESCR						TEXT			Meter Read Reason						Meter Read Reason

### FAQs (Few-shot Examples) ###
Question                                                               SQL
How many billing cycles are currently active in Kharj department?      SELECT COUNT(DISTINCT BILL_CYCLE_CD) AS "active bill cycles"
                                                                              FROM MVW_BILLING_EFFICIENCY_DATA_L
                                                                              WHERE CURRENT_DATE >= WINDOW_START_DT  
                                                                                AND CURRENT_DATE <= WINDOW_END_DT    
                                                                                AND TRIM(UPPER(DEPARTMENT_DESCRIPTION)) LIKE '%KHARJ%';
What is the last billing cycle that was finalized on or before today?  SELECT BILL_CYCLE_CD AS "Bill Cycle", WINDOW_END_DT "Bill Cycle Window End Date"
                                                                              FROM MVW_BILLING_EFFICIENCY_DATA_L
                                                                              WHERE CURRENT_DATE > WINDOW_END_DT
                                                                              ORDER BY 2 DESC
                                                                              LIMIT 1;
What is the bill-cycle-wise success rate for JAN 2026?                 SELECT BILL_CYCLE_CD AS "Bill Cycle",																			
																			ROUND((SUM(CASE WHEN TRIM(UPPER(USAGE_STATUS_CD)) IN ('SENT','ACKRECEIVED') THEN 1 ELSE 0 END) *100 / COUNT(DISTINCT D1_USAGE_ID) ), 2) AS "success Rate"
																		FROM MVW_BILLING_EFFICIENCY_DATA_L
																		WHERE MRO_MONTH=1 AND MRO_YEAR=2026
																		GROUP BY 1
																		ORDER BY 1;

How many MROs created in December 2025 for bill cycle 19 have failed?  SELECT COUNT(DISTINCT D1_USAGE_ID) AS "failed mros"  
                                                                              FROM MVW_BILLING_EFFICIENCY_DATA_L
                                                                              WHERE BILL_CYCLE_CD = 19
                                                                                AND MRO_MONTH = 12
                                                                                AND MRO_YEAR = 2025
                                                                                AND TRIM(UPPER(USAGE_STATUS_CD)) = 'DISCARDED';
What is the success rate of MROs for currently active billing cycles?  SELECT BILL_CYCLE_CD AS "Bill Cycle",	 
																			 ROUND(SUM(CASE WHEN TRIM(UPPER(USAGE_STATUS_CD)) IN ('SENT','ACKRECEIVED') THEN 1 ELSE 0 END) *100/ COUNT(DISTINCT D1_USAGE_ID), 2) AS "Success Rate"
																		FROM MVW_BILLING_EFFICIENCY_DATA_L
																		WHERE CURRENT_DATE >= WINDOW_START_DT  
																		AND CURRENT_DATE <= WINDOW_END_DT    
																		GROUP BY 1;
What is the overall MRO success rate for December 2025?                SELECT ROUND(SUM(CASE WHEN TRIM(UPPER(USAGE_STATUS_CD)) IN ('SENT','ACKRECEIVED') THEN 1 ELSE 0 END) *100/ COUNT(DISTINCT D1_USAGE_ID), 2) AS "Success Rate"
																		FROM MVW_BILLING_EFFICIENCY_DATA_L
																		WHERE MRO_MONTH = 12
																		AND MRO_YEAR = 2025;
Can you give me window end dates for all bill cycles for dec 2025 ?    SELECT DISTINCT WINDOW_END_DT "Bill Cycle Window End Date", BILL_CYCLE_CD "Bill Cycle" 
																		FROM MVW_BILLING_EFFICIENCY_DATA_L
																		WHERE MRO_MONTH = 12 AND MRO_YEAR = 2025 
																		ORDER BY 1 LIMIT 1000;

How many Missing Read Work Orders were completed remotely in Jan 2026?		SELECT 
																				COUNT(DISTINCT ACTIVITY_ID) AS "Remote Completions"
																			FROM FACT_COMMUNICATION
																			WHERE COMMUNICATION_OBJECT = 'CM-MissingMtrRdNtf'
																			  AND WO_STATUS = 'COMP'
																			  AND WO_DESCR_CD = 2141
																			  AND MRO_MONTH = 1 
																			  AND MRO_YEAR = 2026;		

How many active Missing Read Notifications for Department 1500. 		SELECT 
																				COUNT(DISTINCT ACTIVITY_ID)
																			FROM FACT_ACTIVITY A
																				JOIN MVW_BILLING_EFFICIENCY_DATA_L B ON A.USAGE_ID = B.D1_USAGE_ID
																			WHERE A.ACTIVITY_TYPE_CD = 'CM-MISSING-MTR-RD'
																			  AND B.DEPARTMENT_CD = '1500'
																			  AND A.ACTIVITY_STATUS = 'COMMINPROG';