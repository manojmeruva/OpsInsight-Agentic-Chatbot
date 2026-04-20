Domain: rcrdc (Remote Connect & Remote Disconnect). These are real events - remote connection and disconnection , manual reconnection or disconnection.

Data Structure
- Primary Table: MVW_RCRDC 
- Grain: One row per communication attempt; an activity may have multiple communications.
- Key Identifiers: D1_ACTIVITY_ID (Activity) and D1_COMM_ID (Communication).


MANDATORY SQL CONSTRAINTS
- You must strictly follow these rules for every query. Standard SQL patterns must be overridden by these domain-specific rules:
- The Counting Rule: Never use COUNT(*) or COUNT(column_name).
- MANDATORY: Always use COUNT(DISTINCT D1_ACTIVITY_ID).


**Alias Terms**
- Remote Connect (RC): reconnect, reconnection, connect, connected, connection, Remote Connection, with supply, virtually connected
- Remote Disconnect (RDC): disconnect, disconnection, Remote Disconnection, without supply, virtually disconnected



## 1. Remote Connect (RC) Failure/Error Logic
Apply this filter when users ask for "RC/Reconnection" failures, discarded reasons, or errors:
FILTER: 
    TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' 
    AND ACTIVITY_STATUS = 'DISCARDED'

 ## 2. Remote Disconnect (RDC) Failure/Error Logic
 Apply this MANDATORY JOIN PATTERN when users ask for "RDC/Disconnection" failures, discarded reasons, or errors:
 PATTERN:
#     FROM MVW_RCRDC MAIN
#     JOIN (
#         SELECT T1.D1_ACTIVITY_ID, MAX(T1.COMMUNICATION_CREATION_DTTM) AS max_comm
#         FROM MVW_RCRDC T1
#         WHERE T1.ACTIVITY_STATUS = 'DISCARDED' 
#           AND (T1.COMMUNICATION_STATUS = 'DISCARDED' OR T1.COMMUNICATION_STATUS <> 'COMPLETED') 
#         GROUP BY 1
#     ) LAST_COMM ON MAIN.D1_ACTIVITY_ID = LAST_COMM.D1_ACTIVITY_ID
#     AND MAIN.COMMUNICATION_CREATION_DTTM = LAST_COMM.max_comm 

    FROM (
        SELECT 
            D1_ACTIVITY_ID,
            ROW_NUMBER() OVER(
                PARTITION BY D1_ACTIVITY_ID 
                ORDER BY 
                    CASE WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 1 ELSE 2 END, 
                    COMMUNICATION_CREATION_DTTM DESC
            ) as rank_priority
        FROM MVW_RCRDC
        WHERE 
            TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
            AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'
            AND TRIM(UPPER(COMMUNICATION_STATUS)) = 'DISCARDED'
    ) MAIN
    WHERE rank_priority = 1


**Ranking & Tie-Breaking:**
- When asked for "top," "best," "highest," or "least" performers, you MUST show all entities that are tied for that rank.
- MANDATORY: Use RANK() or DENSE_RANK() in a subquery and filter by WHERE rnk = 1 in the outer SELECT.

**Ordering & Grouping:** 
- Use column sequence numbers (e.g., GROUP BY 1, ORDER BY 2 DESC) for all aggregation and sorting operations.

**Alias Restrictions:**
- Internal Subqueries: Aliases MUST NOT contain spaces or quotes; use underscores (e.g., failed_count)
- Final Output: Apply user-friendly aliases with spaces (e.g., "Failed Count") ONLY in the outermost SELECT statement.


**Rule for Failure-Based Questions**
- Failed and discarded are considered to mean the same when a user asks in the question.
** IMPORTANT ** 
- To avoid contradiction between technical failures and successful cancellations (both marked 'DISCARDED'), use the following logic:
- Technical Failure: Count distinct(D1_ACTIVITY_ID) where ACTIVITY_STATUS = 'DISCARDED' AND (CANCEL_ACTIVITY_STATUS IS NULL OR CANCEL_ACTIVITY_STATUS <> 'COMPLETE').
- Successful Cancellation: Count distinct(D1_ACTIVITY_ID) where CANCEL_ACTIVITY_STATUS = 'COMPLETE' and ACTIVITY_STATUS = 'DISCARDED'.
- Failed Cancellation: Count distinct(D1_ACTIVITY_ID) where CANCEL_ACTIVITY_STATUS = 'DISCARDED' and ACTIVITY_STATUS = 'COMPLETED'.
- General Failure Criteria: ACTIVITY_STATUS <> 'COMPLETED' AND (COMMUNICATION_STATUS = 'DISCARDED' OR COMMUNICATION_STATUS <> 'COMPLETED').


### Additional details 
**Cancellation Logic**:
- A disconnection request can be superseded by a cancel disconnection request (CANCEL_ACTIVITY_ID). 
- Cancellation Identification: When a user asks about "cancelled" disconnections or  "cancel" disconnections or "cancellation commands," you must filter by CANCEL_ACTIVITY_STATUS = 'COMPLETE' and ACTIVITY_STATUS = 'DISCARDED'
- A DISCARDED activity status alone represents a failure ; it only represents a "successful cancellation" if CANCEL_ACTIVITY_STATUS is 'COMPLETE'. 


### RC/Connection/Reconnection Logic

Intent						    Filter Criteria
Only Count					    ACTIVITY_TYPE_CD = 'REMOTECONNECT'
Only Success				    ACTIVITY_TYPE_CD = 'REMOTECONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED'
Only Failure*				    ACTIVITY_TYPE_CD = 'REMOTECONNECT' AND ACTIVITY_STATUS = 'DISCARDED' AND COMMUNICATION_STATUS = 'DISCARDED' AND COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN'
Remote-Only (HES) Success		ACTIVITY_TYPE_CD = 'REMOTECONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED' AND COMMUNICATION_TYPE_CD = 'CM-CON-DISCON-IN'
Manual-Only (SMOC/HHU) Success  ACTIVITY_TYPE_CD = 'REMOTECONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED' AND COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN'


### RDC/Disconnection Logic

Intent						    Filter Criteria
Only Count					    ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT'
Only Success				    ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED'
Only Failure*				    ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'DISCARDED' AND COMMUNICATION_STATUS = 'DISCARDED' (Prioritize COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN' or use MAX(COMMUNICATION_CREATION_DTTM))
Remote-Only (HES) Success	    ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED' AND COMMUNICATION_TYPE_CD = 'CM-CON-DISCON-IN'
Manual-Only (SMOC/HHU) Success	ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND COMMUNICATION_STATUS = 'COMPLETED' AND COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN'
Cancelled Disconnections        ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'DISCARDED' AND CANCEL_ACTIVITY_STATUS = 'COMPLETE' (Prioritize COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN' or use MAX(COMMUNICATION_CREATION_DTTM))
Failed by Cancellation 		    ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'DISCARDED' AND CANCEL_ACTIVITY_ID IS NOT NULL AND CANCEL_ACTIVITY_STATUS = 'COMPLETE' (Prioritize COMMUNICATION_TYPE_CD = 'CM-SMOC-RDC-IN' or use MAX(COMMUNICATION_CREATION_DTTM))
Failed Cancellation             ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT' AND ACTIVITY_STATUS = 'COMPLETED' AND CANCEL_ACTIVITY_STATUS = 'DISCARDED'  AND COMMUNICATION_STATUS = 'COMPLETED'

**Manual vs Remote Identification**
- Total Requests (Overall): If the user asks for "total," "overall," or "volume," count DISTINCT(D1_ACTIVITY_ID) based only on the ACTIVITY_TYPE_CD ('REMOTECONNECT' or 'REMOTEDISCONNECT').
- Completed Activities: You must check which specific communication status is COMPLETED and adopt that COMMUNICATION_TYPE_CD (e.g., CM-CON-DISCON-IN for Remote or CM-SMOC-RDC-IN for Manual).
- Discarded Activities: 
    - For Disconnect (ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT'): Prioritize any existence of a manual record (CM-SMOC-RDC-IN); otherwise, take the most recent communication (MAX(COMMUNICATION_CREATION_DTTM)).
    - For Connect (ACTIVITY_TYPE_CD = 'REMOTECONNECT'): Strictly take the manual record (CM-SMOC-RDC-IN).
- Other Statuses: For any other activity status (such as COMINPROG or COMERROR), you must prioritize the record that was created most recently using the MAX(COMMUNICATION_CREATION_DTTM)


**AMBIGUITY RESOLUTION GUARDRAILS**
- Total Count Logic: If the user asks for "total," "overall," "volume," or a general count of connections/disconnections without specifying the method, the SQL should count all distinct D1_ACTIVITY_ID.
- Mandatory AI Note: For every query that provides a total count (inclusive of both  remote or HES and manual or SMOC), the AI response MUST include: "This count includes both remote (HES) and manual (SMOC) actions. Would you like a breakdown by method?"
- Cancellation Identification: When a user asks about "cancelled" requests, the filter CANCEL_ACTIVITY_STATUS is not null is MANDATORY.
- Terminology Mapping:
	- Remote Specific: remote connect, HES connect, automated connection, non-manual connection, remote disconnect, HES disconnect, automated disconnection, non-manual disconnection.
	- Manual Specific: SMOC connection, manual reconnect, field connection, HHU intervention, SMOC disconnection, manual disconnect.
- NULL HANDLING RULE: Whenever a query requires grouping or displaying DEPARTMENT_DESCRIPTION, AREA_DESCRIPTION, OFFICE_DESCRIPTION, REASON_DESCR, or HEAD_END_SYS, the SQL must wrap the column in COALESCE(<column_name>, 'Value Not Available'). This applies to both the SELECT and the GROUP BY statements.
- Reason vs. Error:
	- If the user asks "What are the reasons for [RC/RDC]?", use REASON_DESCR
	- If the user asks "What are the reasons for failed/discarded [RC/RDC]?", use ERROR_MESSAGE

**Alias Terms**
- General Reconnection(RC): reconnect, reconnection, connect, connected, connection, with supply, virtually connected
- Remote Specific Reconnection((RC): remote connect, HES connect, automated connection, non-manual connection.
- Manual (SMOC/HHU) Specific Reconnection: SMOC connection, manual reconnect, field connection, HHU intervention.
- General Disconnection (RDC): disconnect, disconnection, without supply, virtually disconnected
- Remote Specific Disconnection: remote disconnect, HES disconnect, automated disconnection, non-manual disconnection.
- Manual (SMOC/HHU) Specific Disconnection: SMOC disconnection,SMOC disconnect, manual disconnect, field disconnection, HHU intervention.

DOMAIN MAPPINGS
**Activity Classification:**
Concept						SQL Filter
Remote Connect (RC)			ACTIVITY_TYPE_CD = 'REMOTECONNECT'
Remote Disconnect (RDC)		ACTIVITY_TYPE_CD = 'REMOTEDISCONNECT'

**Time Filtering**
- Requests Initiated: Filter by ACTIVITY_CREATION_DTTM
- Requests COMPLETED: Filter by ACTIVITY_END_DTTM

**COMPLIANCE CHECKLIST BEFORE RESPONDING**
1. Did I use COUNT(DISTINCT D1_ACTIVITY_ID)?
2. If it's a "Top/Best" query, did I use DENSE_RANK()?
# 3. For RDC failures, did I use the MAX time JOIN pattern?
3. Are my subquery aliases underscored and my final aliases spaced?
4. Did I use GROUP BY 1, 2?


### FAQs (Few-shot Examples) ###
Question                                                                                        SQL
how many total remote connections requests are sent last month in riyadh department?            SELECT COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) as `Remote connection requests`
																								FROM 
																									MVW_RCRDC MAIN
																								WHERE TRIM(UPPER(MAIN.ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																									AND TRIM(UPPER(MAIN.DEPARTMENT_DESCRIPTION)) LIKE '%RIYADH%'
																									AND MAIN.ACTIVITY_START_DTTM >= DATE_TRUNC('month', CURRENT_TIMESTAMP) - INTERVAL 1 MONTH
																									AND MAIN.ACTIVITY_START_DTTM < DATE_TRUNC('month', CURRENT_TIMESTAMP);
how many remote connections requests are sent last month with out manual intervention or HHU?   SELECT
																									COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) as "Remote connection requests"
																								FROM
																									MVW_RCRDC MAIN
																									
																								WHERE TRIM(UPPER(MAIN.ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'	
																									AND MAIN.D1_ACTIVITY_ID NOT IN (SELECT T2.D1_ACTIVITY_ID from MVW_RCRDC T2
																																		where TRIM(UPPER(T2.COMMUNICATION_TYPE_CD)) ='CM-SMOC-RDC-IN'
																																		and T2.D1_ACTIVITY_ID=MAIN.D1_ACTIVITY_ID)
																									AND MAIN.ACTIVITY_START_DTTM >= DATE_TRUNC('month', CURRENT_TIMESTAMP) - INTERVAL 1 MONTH
																										AND MAIN.ACTIVITY_START_DTTM < DATE_TRUNC('month', CURRENT_TIMESTAMP);
																										
how many remote connections requests had manual or HHU intervention last month?                 SELECT COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) as "Remote connection requests"
																									FROM MVW_RCRDC MAIN
																										JOIN (SELECT T1.D1_ACTIVITY_ID,
																												MAX(T1.COMMUNICATION_CREATION_DTTM) AS COMMUNICATION_CREATION_DTTM
																											FROM MVW_RCRDC T1
																											WHERE TRIM(UPPER(T1.ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																												AND TRIM(UPPER(T1.COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN'                
																												AND T1.ACTIVITY_START_DTTM >= CURRENT_TIMESTAMP - INTERVAL 1 MONTH
																												AND T1.ACTIVITY_START_DTTM < CURRENT_TIMESTAMP
																										GROUP BY T1.D1_ACTIVITY_ID) LAST_COMM
																								ON MAIN.D1_ACTIVITY_ID = LAST_COMM.D1_ACTIVITY_ID      
																									AND MAIN.COMMUNICATION_CREATION_DTTM = LAST_COMM.COMMUNICATION_CREATION_DTTM ;
																										
How many failed remote disconnection requests are there?                                        SELECT COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failed Remote Disconnections"
																								FROM MVW_RCRDC 
																									WHERE
																											TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																											AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED';
Show departments where the number of discarded remote connection was highest in October 2025    SELECT
																									DEPARTMENT_DESCRIPTION AS "Department Name",
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failed Count"       
																								FROM MVW_RCRDC 
																									WHERE
																										TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																										AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'     		
																										AND ACTIVITY_CREATION_DTTM >= '2025-10-01'
																										AND ACTIVITY_CREATION_DTTM < '2025-11-01'
																								GROUP BY 1
																								ORDER BY 2 DESC
																								LIMIT 1000;
																								
Which weekday had the least number of remote disconnections in October 2025?                    SELECT DAYNAME(ACTIVITY_CREATION_DTTM) AS weekday,
                                                                                                              COUNT(DISTINCT D1_ACTIVITY_ID) AS "Disconnect Count"  
                                                                                                       FROM MVW_RCRDC
                                                                                                       WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'   
                                                                                                         AND ACTIVITY_CREATION_DTTM >= '2025-10-01'
                                                                                                         AND ACTIVITY_CREATION_DTTM < '2025-11-01'
                                                                                                       GROUP BY 1
                                                                                                       ORDER BY 2 ASC
                                                                                                       LIMIT 1;
Give a breakdown of successful remote connections and manual connections in October 2025        SELECT
																									COUNT(DISTINCT CASE
																										 WHEN TRIM(UPPER(MAIN.COMMUNICATION_TYPE_CD)) = 'CM-CON-DISCON-IN'
																										 THEN MAIN.D1_ACTIVITY_ID
																									END) AS "Successful Remote Connections",
																									COUNT(DISTINCT CASE
																										 WHEN TRIM(UPPER(MAIN.COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN'
																										 THEN MAIN.D1_ACTIVITY_ID
																									END) AS "Successful Manual Connections"
																								FROM MVW_RCRDC MAIN 
																									JOIN (SELECT T1.D1_ACTIVITY_ID,
																											 MAX(T1.COMMUNICATION_CREATION_DTTM) AS COMMUNICATION_CREATION_DTTM
																										  FROM MVW_RCRDC T1
																										  WHERE TRIM(UPPER(T1.ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																												 AND TRIM(UPPER(T1.ACTIVITY_STATUS)) = 'COMPLETED'    
																												 AND TRIM(UPPER(T1.COMMUNICATION_STATUS)) = 'COMPLETED'
																												 AND T1.ACTIVITY_START_DTTM >= '2025-10-01'       
																												 AND T1.ACTIVITY_START_DTTM < '2025-11-01'
																										GROUP BY T1.D1_ACTIVITY_ID) LAST_COMM
																								ON MAIN.D1_ACTIVITY_ID = LAST_COMM.D1_ACTIVITY_ID      
																								  AND MAIN.COMMUNICATION_CREATION_DTTM = LAST_COMM.COMMUNICATION_CREATION_DTTM 
																									
what the success percentage of remote connections on 30 Dec 2025?                               SELECT
                                                                                                        (COUNT(DISTINCT CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED' THEN D1_ACTIVITY_ID END) * 100.0) / COUNT(DISTINCT D1_ACTIVITY_ID) AS "Success Percentage"
                                                                                                                FROM MVW_RCRDC
                                                                                                                WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
                                                                                                        AND DATE(ACTIVITY_CREATION_DTTM) = '2025-12-30';
give me breakdown by success and failed remote connection on Jan 11 2026 including NARI & SCHN  SELECT
																									HEAD_END_SYS AS "Head end system",
																									COUNT(DISTINCT CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED' THEN D1_ACTIVITY_ID ELSE 0 END) AS "Successful Connections",
																									COUNT(DISTINCT CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED' THEN D1_ACTIVITY_ID ELSE 0 END) AS "Failed Connections"
																								FROM MVW_RCRDC 
																								WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																											AND DATE(ACTIVITY_CREATION_DTTM) = '2026-01-11'                                                                                                                
																											AND HEAD_END_SYS IN ('NARI', 'SCHN')
																								GROUP BY 1;

List the top 5 days with the highest number of remote disconnection failures                    SELECT
																									DATE(ACTIVITY_CREATION_DTTM) AS "Failure Date",                                                                                                          
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failure Count"    
																								FROM MVW_RCRDC 
																								WHERE
																												 TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																												 AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'                                                                                                                 				 
																								GROUP BY 1
																								ORDER BY 2 DESC
																								LIMIT 5;
																								
Summary of error messages for failed or discarded remote connections on 21 Dec 2025             SELECT ERROR_MESSAGE AS "Error Message",
																									   COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failure Count"
																								FROM MVW_RCRDC 
																								WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																										AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'  
																										AND TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN'				
																										AND DATE(ACTIVITY_CREATION_DTTM) = '2025-12-21'   	  
																								GROUP BY 1
																								ORDER BY 2;

Summary of error messages for failed or discarded remote disconnection on 21 Dec 2025           SELECT MAIN.ERROR_MESSAGE AS "Error Message",
                                                                                                               COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) AS "Failure count"
                                                                                                FROM MVW_RCRDC MAIN        
                                                                                                     JOIN (SELECT T1.D1_ACTIVITY_ID, MAX(COMMUNICATION_CREATION_DTTM) AS COMMUNICATION_CREATION_DTTM
                                                                                                         FROM MVW_RCRDC T1       
                                                                                                         WHERE TRIM(UPPER(T1.ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
                                                                                                                AND TRIM(UPPER(T1.ACTIVITY_STATUS)) = 'DISCARDED'
                                                                                                                AND TRIM(UPPER(T1.COMMUNICATION_STATUS)) <> 'COMPLETED'
                                                                                                                AND DATE(T1.ACTIVITY_CREATION_DTTM) = '2025-12-21'
                                                                                                              GROUP BY 1) LAST_COMM 
																								ON MAIN.D1_ACTIVITY_ID = LAST_COMM.D1_ACTIVITY_ID
																								  AND MAIN.COMMUNICATION_CREATION_DTTM = LAST_COMM.COMMUNICATION_CREATION_DTTM
																								GROUP BY 1
																								ORDER BY 2 DESC;
																								
How many meters received repeated RDC requests in the last 7 days?								SELECT 
																									COUNT(meter_serial) AS "Meters with Repeated RDC Requests"
																								FROM (
																									SELECT
																										METER_SERIAL_NUMBER AS meter_serial,
																										COUNT(DISTINCT D1_ACTIVITY_ID) AS request_count
																									FROM MVW_RCRDC
																									WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																									  AND ACTIVITY_CREATION_DTTM >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
																									GROUP BY 1
																									HAVING COUNT(DISTINCT D1_ACTIVITY_ID) > 1
																								) AS repeated_requests;

How many failed remote disconnection requests are there?"										SELECT COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failed Remote Disconnections"
																								FROM 
																									MVW_RCRDC 
																								WHERE
																										TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																										AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED';
														
Show departments where the number of discarded remote connection was highest in October 2025?    SELECT
																									DEPARTMENT_DESCRIPTION AS "Department Name",
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failed Count"       
																								FROM MVW_RCRDC 
																									WHERE
																										TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																										AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'     		
																										AND ACTIVITY_CREATION_DTTM >= '2025-10-01'
																										AND ACTIVITY_CREATION_DTTM < '2025-11-01'
																								GROUP BY 1
																								ORDER BY 2 DESC ;

Which weekday had the least number of remote disconnections in October 2025?					SELECT DAYNAME(ACTIVITY_CREATION_DTTM) AS weekday,
																										COUNT(DISTINCT D1_ACTIVITY_ID) AS "Disconnect Count"  
																								FROM MVW_RCRDC
																								WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'   
																									AND ACTIVITY_CREATION_DTTM >= '2025-10-01'
																									AND ACTIVITY_CREATION_DTTM < '2025-11-01'
																								GROUP BY 1
																								ORDER BY 2 ASC
																								LIMIT 1;

Give a breakdown of successful remote connections and manual connections in October 2025? 		SELECT 
																									CASE 
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-CON-DISCON-IN' THEN 'Remote Success (HES)'
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 'Manual Success (SMOC)'
																									END AS Connection_Method,
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS Success_Count
																								FROM MVW_RCRDC
																								WHERE 
																									TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																									AND TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED'
																									AND TRIM(UPPER(COMMUNICATION_STATUS)) = 'COMPLETED'
																									AND ACTIVITY_CREATION_DTTM >= '2026-02-15' 
																									AND ACTIVITY_CREATION_DTTM < '2026-02-16'
																									AND TRIM(UPPER(COMMUNICATION_TYPE_CD)) IN ('CM-CON-DISCON-IN', 'CM-SMOC-RDC-IN')
																								GROUP BY 1
    
Give a breakdown of remote connections and manual connections for 15 FEB 2026?					SELECT 
																									CASE 
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-CON-DISCON-IN' THEN 'Remote (HES)'
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 'Manual (SMOC)'
																										ELSE 'Other/Unknown'
																									END AS Method,
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS Total_Count
																								FROM (
																									SELECT 
																										D1_ACTIVITY_ID,
																										COMMUNICATION_TYPE_CD,
																										ROW_NUMBER() OVER(
																											PARTITION BY D1_ACTIVITY_ID 
																											ORDER BY 
																												CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED' 
																													AND TRIM(UPPER(COMMUNICATION_STATUS)) = 'COMPLETED' THEN 1 ELSE 10 END,
																												CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED' 
																													AND TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 2 ELSE 10 END,
																												COMMUNICATION_CREATION_DTTM DESC
																										) as rank_priority
																									FROM MVW_RCRDC
																									WHERE 
																										TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																										AND DATE(ACTIVITY_START_DTTM) = '2026-02-15'
																								) MAIN
																								WHERE rank_priority = 1
																								GROUP BY 1
																								ORDER BY 2 DESC;

what the success percentage of remote connections on 30 Dec 2025?								SELECT
																									(COUNT(DISTINCT CASE WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED' THEN D1_ACTIVITY_ID END) * 100.0) / COUNT(DISTINCT D1_ACTIVITY_ID) AS "Success Percentage"
																								FROM MVW_RCRDC
																											WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																									AND DATE(ACTIVITY_CREATION_DTTM) = '2025-12-30';

give me breakdown by success and failed remote connection on FEB 15 2026 including NARI & SCHN?	SELECT 
																									COALESCE(HEAD_END_SYS, 'Value Not Available') AS Head_End_System,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'COMPLETED' 
																										AND TRIM(UPPER(COMMUNICATION_STATUS)) = 'COMPLETED' 
																										THEN D1_ACTIVITY_ID 
																									END) AS successful_remote_connections,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED' 
																										AND (TRIM(UPPER(COMMUNICATION_STATUS)) = 'DISCARDED' 
																											OR TRIM(UPPER(COMMUNICATION_STATUS)) <> 'COMPLETED' 
																											OR COMMUNICATION_STATUS IS NULL)
																										THEN D1_ACTIVITY_ID 
																									END) AS failed_remote_connections
																								FROM MVW_RCRDC
																								WHERE 
																									TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																									AND DATE(ACTIVITY_CREATION_DTTM) = '2026-02-15'
																									AND TRIM(UPPER(HEAD_END_SYS)) IN ('NARI', 'SCHN')
																								GROUP BY COALESCE(HEAD_END_SYS, 'Value Not Available');

List the top 5 days with the highest number of remote disconnection failures?				    SELECT
																									DATE(ACTIVITY_CREATION_DTTM) AS "Failure Date",                                                                                                          
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS "Failure Count"    
																								FROM MVW_RCRDC 
																								WHERE
																													TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																													AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'                                                                                                                 				 
																								GROUP BY 1
																								ORDER BY 2 DESC
																								LIMIT 5;

Show total connections and disconnections today by department. 									SELECT 
																									COALESCE(DEPARTMENT_DESCRIPTION, 'Value Not Available') AS department,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT' 
																										THEN D1_ACTIVITY_ID 
																									END) AS connect_count,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT' 
																										THEN D1_ACTIVITY_ID 
																									END) AS disconnect_count
																								FROM MVW_RCRDC
																								WHERE DATE(ACTIVITY_CREATION_DTTM) = CURRENT_DATE
																								GROUP BY COALESCE(DEPARTMENT_DESCRIPTION, 'Value Not Available')
																								ORDER BY department ASC;

How many disconnections were cancelled today by cancel command?									SELECT 
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS cancelled_disconnections
																								FROM MVW_RCRDC
																								WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																									AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'
																									AND TRIM(UPPER(CANCEL_ACTIVITY_STATUS)) = 'COMPLETE'
																									AND DATE(ACTIVITY_CREATION_DTTM) = CURRENT_DATE;


region wise remote vs manual rc received today?													SELECT 
																									COALESCE(AREA_DESCRIPTION, 'Value Not Available') AS Region,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-CON-DISCON-IN' 
																										AND D1_ACTIVITY_ID NOT IN (
																											SELECT T1.D1_ACTIVITY_ID 
																											FROM MVW_RCRDC T1 
																											WHERE TRIM(UPPER(T1.COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN'
																										) THEN D1_ACTIVITY_ID END) AS remote_only_rc_received,
																									COUNT(DISTINCT CASE 
																										WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' 
																										THEN D1_ACTIVITY_ID END) AS manual_rc_received
																								FROM MVW_RCRDC 
																								WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT' 
																									AND DATE(ACTIVITY_CREATION_DTTM) = CURRENT_DATE 
																								GROUP BY COALESCE(AREA_DESCRIPTION, 'Value Not Available') 
																								ORDER BY Region ASC;
 
Summary of error messages for failed or discarded remote disconnection on 15 FEB 2026?			SELECT 
																									MAIN.ERROR_MESSAGE, 
																									COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) AS failure_count
																								FROM MVW_RCRDC MAIN
																								INNER JOIN (
																									SELECT 
																										D1_ACTIVITY_ID,
																										MAX(COMMUNICATION_CREATION_DTTM) AS LATEST_COMM
																									FROM MVW_RCRDC
																									WHERE 
																										TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																										AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'
																										AND (TRIM(UPPER(COMMUNICATION_STATUS)) = 'DISCARDED' 
																											OR TRIM(UPPER(COMMUNICATION_STATUS)) <> 'COMPLETED' 
																											OR COMMUNICATION_STATUS IS NULL)
																										AND DATE(ACTIVITY_CREATION_DTTM) = '2026-02-15'
																									GROUP BY D1_ACTIVITY_ID
																								) SUB ON MAIN.D1_ACTIVITY_ID = SUB.D1_ACTIVITY_ID 
																									AND MAIN.COMMUNICATION_CREATION_DTTM = SUB.LATEST_COMM
																								GROUP BY MAIN.ERROR_MESSAGE
																								ORDER BY failure_count DESC;

How many meters received repeated RDC requests in the last 7 days?								SELECT 
																									COUNT(meter_serial) AS "Meters with Repeated RDC Requests"
																								FROM (
																									SELECT
																										METER_SERIAL_NUMBER AS meter_serial,
																										COUNT(DISTINCT D1_ACTIVITY_ID) AS request_count
																									FROM MVW_RCRDC
																									WHERE TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																										AND ACTIVITY_CREATION_DTTM >= CURRENT_TIMESTAMP - INTERVAL 7 DAY
																									GROUP BY 1
																									HAVING COUNT(DISTINCT D1_ACTIVITY_ID) > 1
																								) AS repeated_requests;,"rcrdc"),

How many rdc request were failed by cancellation command on 15 Feb 2026?						SELECT 
																									COUNT(DISTINCT D1_ACTIVITY_ID) AS cancelled_rdc_failures
																								FROM MVW_RCRDC
																								WHERE 
																									TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTEDISCONNECT'
																									AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'
																									AND TRIM(UPPER(CANCEL_ACTIVITY_STATUS)) = 'COMPLETE'
																									AND DATE(ACTIVITY_CREATION_DTTM) = '2026-02-15';,"rcrdc"),            
                
Summary of error messages for failed or discarded remote connections on 15 Feb 2026?			SELECT 
																									COALESCE(MAIN.ERROR_MESSAGE, 'No Error Message Provided') AS Error_Reason,
																									COUNT(DISTINCT MAIN.D1_ACTIVITY_ID) AS Failure_Count
																								FROM MVW_RCRDC MAIN
																								INNER JOIN (
																									SELECT 
																										D1_ACTIVITY_ID,
																										MIN(rank_priority) as top_priority
																									FROM (
																										SELECT 
																											D1_ACTIVITY_ID,
																											CASE 
																												WHEN TRIM(UPPER(COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 1 
																												ELSE 2 
																											END as rank_priority
																										FROM MVW_RCRDC
																										WHERE 
																											TRIM(UPPER(ACTIVITY_TYPE_CD)) = 'REMOTECONNECT'
																											AND TRIM(UPPER(ACTIVITY_STATUS)) = 'DISCARDED'
																											AND DATE(ACTIVITY_CREATION_DTTM) = '2026-02-15'
																									) PriorityTable
																									GROUP BY D1_ACTIVITY_ID
																								) SUB_FILTER ON MAIN.D1_ACTIVITY_ID = SUB_FILTER.D1_ACTIVITY_ID
																								WHERE 
																									(CASE WHEN TRIM(UPPER(MAIN.COMMUNICATION_TYPE_CD)) = 'CM-SMOC-RDC-IN' THEN 1 ELSE 2 END) = SUB_FILTER.top_priority
																									AND DATE(MAIN.ACTIVITY_CREATION_DTTM) = '2026-02-15'
																								GROUP BY 1
																								ORDER BY 2 DESC;