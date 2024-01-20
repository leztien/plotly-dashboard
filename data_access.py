
"""
helper functions for data access
"""


from sqlalchemy import create_engine
import psycopg2                        # pip install psycopg2-binary
from dotenv import dotenv_values       # pip install python-dotenv
from pandas import read_sql_query
from constants import DEBUG, ERR_PREFIX, DRIVER, SCHEMA
from constants import TABLE_ACCOUNT, TABLE_MEAL, TABLE_FOODSTUFF, TABLE_MEAL_FOODSTUFF, TABLE_REPORT
from constants import (COLUMN_ACCOUNT_ID, COLUMN_MEAL_ID, COLUMN_DATE, COLUMN_MEAL, COLUMN_FOODSTUFF_ID,
                       COLUMN_NAME, COLUMN_REPORT_ID, COLUMN_SYMPTOM, COLUMN_GRADE, COLUMN_TIMING)


# What is your driver and schema names?
DRIVER # is imported from constants.py
SCHEMA # is imported from constants.py
# Change the DRIVER and SCHEMA names in constants.py or transfer their definitions here.


def make_sqlalchemy_engine():
    """
    TODO: docs

    Undertakes 3 approaches to connect (in try-except blocks)
    try these maybe:
    "postgresql://user:pass@hostname/dbname"
    "postgresql+psycopg2://user:pass@hostname/database"

    also try:
    $ pip install snowflake-sqlalchemy
    $ pip install psycopg2-binary
    import psycopg2 
    """

    # SQL datbase credentials - define constants as they appear in your .env file
    HOST = 'host'
    PORT = 'port'
    DATABASE = 'database'      # maybe 'dbname' ?
    USER = 'user'              # maybe 'username' ?
    PASSWORD = 'password'      # maybe 'pass' ?

    env_dict = dotenv_values(".env")
    keys = [HOST, PORT, DATABASE, USER, PASSWORD]
    connect_args = {key: env_dict[key] for key in keys if key in env_dict}

    # Have the credentials been loaded?
    if not env_dict:
        raise FileNotFoundError(f"{ERR_PREFIX}SQL database credentials haven't been loaded")

    # Attempt 1
    try:
        engine = create_engine(f"{DRIVER}://user:pass@hostname/database", connect_args=connect_args)
        read_sql_query("SELECT 1;", con=engine)
    except: # all kinds of errors = bad practice but ...
        engine = None
    else:
        return engine

    #Attempt 2
    connect_args["dbname"] = connect_args[DATABASE]  # replace the key-name 'database' with 'dbname'
    del connect_args[DATABASE]                       # solution for the error from sqlalchemy   

    try:
        engine = create_engine(f"{DRIVER}://user:pass@hostname/database", connect_args=connect_args)
        read_sql_query("SELECT 1;", con=engine)
    except: # all kinds of errors = bad practice but ...
        engine = None
    else:
        return engine

    # Attempt 3
    try:
        from sqlalchemy import URL
    except ImportError:
        raise ImportError((f"{ERR_PREFIX}Undertook 3 different approaches to connect to your database. "
                           f"The last one implied importing the 'URL' class from sqlalchemy and it didn't work. "
                           f"Try this: pip install snowflake-sqlalchemy"))

    url_object = URL.create(
        DRIVER,             
        username=env_dict[USER],
        password=env_dict[PASSWORD],
        host=env_dict[HOST],
        database=env_dict[DATABASE])

    # no try-except block here to show the original error message from sqlalchemy if an Exception happens.
    return create_engine(url_object)



def check_account(account_id, engine=None):
    """
    TODO
    apparently it is not necessary to close or kill the engine before "return"

    Raturns:
        None: if user not found in the account table
        False: if use is found but there's no data in either meals OR symptomreport
        True: otherwise
    """

    # Prevent SQL injection
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return ValueError  # will not be raised - just to tell that the value passed is bad
                           # and avoid using a non built-in object
    
    # Start an sqlalchemy engine
    engine = engine or make_sqlalchemy_engine()
    
    # User not found -> None
    query_has_account = f"SELECT COUNT({COLUMN_ACCOUNT_ID}) FROM {SCHEMA}.{TABLE_ACCOUNT} WHERE {COLUMN_ACCOUNT_ID} = (%s);"
    user_input = (account_id,)  # to prevent SQL injection
    df = read_sql_query(query_has_account, params=user_input, con=engine)
    if int(df.values[0][0]) == 0:
        return None
    
    # No data found -> False
    query_has_data = (f"""
SELECT MAX(result) AS min_value
FROM (
	SELECT COUNT({COLUMN_ACCOUNT_ID}) AS result FROM {SCHEMA}.{TABLE_MEAL} WHERE {COLUMN_ACCOUNT_ID} = (%s)
	UNION
	SELECT COUNT({COLUMN_ACCOUNT_ID}) AS result FROM {SCHEMA}.{TABLE_REPORT} WHERE {COLUMN_ACCOUNT_ID} = (%s) 
) AS sub
;""")
    user_input = (account_id, account_id)  # cannot use %(name)s for compatability with mysql
    df = read_sql_query(query_has_data, params=user_input, con=engine)
    if int(df.values[0][0]) == 0:
        return False

    # Data found -> True
    return True



def fetch_eating_data(account_id, engine):
    """
    TODO
    """
    # the input (account_id) should be valid (i.e. int) by now
    # so throw an error here, also to prevent a potential SQL injection
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        raise ValueError(f"{ERR_PREFIX}account_id must be (convertable to) int")
    
    # Define an SQL query to merge three tables for the given account
    query = (f"""
SELECT l.{COLUMN_ACCOUNT_ID}, l.{COLUMN_DATE}, l.{COLUMN_MEAL_ID}, l.{COLUMN_MEAL}, rr.{COLUMN_NAME}, r.{COLUMN_FOODSTUFF_ID}
FROM
	{SCHEMA}.{TABLE_MEAL} l LEFT JOIN {SCHEMA}.{TABLE_MEAL_FOODSTUFF} r ON l.{COLUMN_MEAL_ID} = r.{COLUMN_MEAL_ID} 
	LEFT JOIN {SCHEMA}.{TABLE_FOODSTUFF} rr ON r.{COLUMN_FOODSTUFF_ID} = rr.{COLUMN_FOODSTUFF_ID}
WHERE {COLUMN_ACCOUNT_ID} = (%s)
ORDER BY l.{COLUMN_DATE}, 
		CASE
			WHEN {COLUMN_MEAL} = 'BREAKFAST' THEN 1
			WHEN {COLUMN_MEAL} = 'LUNCH' THEN 2
			WHEN {COLUMN_MEAL} = 'DINNER' THEN 3
            ELSE 4
		END
;""")
    
    # SQL injection prevention
    user_input = (account_id,)

    # Return the merged df
    return read_sql_query(sql=query, params=user_input, con=engine)



def fetch_symptoms_data(account_id, engine):
    """TODO"""

    # the input (account_id) should be valid by now (i.e. int or convertable to int)
    # so throw an error here, also to prevent a potential SQL injection
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        raise ValueError(f"{ERR_PREFIX}account_id must be (convertable to) int")

    # Query to get the symptomreport table in the right shape (no merging here)
    query = f"""
SELECT
    {COLUMN_ACCOUNT_ID},
	{COLUMN_DATE}, 
	{COLUMN_TIMING},
	{COLUMN_SYMPTOM},
	{COLUMN_GRADE}
FROM {SCHEMA}.{TABLE_REPORT}
WHERE {COLUMN_ACCOUNT_ID} = (%s)
ORDER BY 
	{COLUMN_DATE}, 
	CASE 
		WHEN {COLUMN_TIMING} = 'AFTER_GETTING_UP' THEN 1
		WHEN {COLUMN_TIMING} = 'AFTER_BREAKFAST' THEN 2
		WHEN {COLUMN_TIMING} = 'AFTER_LUNCH' THEN 3
		WHEN {COLUMN_TIMING} = 'AFTER_DINNER' THEN 4
		WHEN {COLUMN_TIMING} = 'UNKNOWN' THEN 5
		ELSE 6
	END,
	{COLUMN_REPORT_ID} --to keep the order in which the user made the entries
;"""
    
    # Prevent SQL injection
    user_input = (account_id,)

    # Return df
    return read_sql_query(sql=query, params=user_input, con=engine)



