# -*- coding: utf-8 -*-
import logging
logging.basicConfig(filename='log.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('Info')
import os, sqlite3
import language_support
import numpy as np

jsonresponse = language_support.responses

""" 
Create a database and initialise the tables - This is mainly used for setting up own instances of the bot 
The database contains three tables
- Names    - Maps the TelegramID of users to their respective Trainername and Trainercode
- Username - Stores the SilphID of a username (currently not used until Silph releases an API)
- Groups   - Stores the settings for Telegram Groups i.e. if IV-queries are enabled
"""
def create_db():
    connection = sqlite3.connect("www/names.db")
    cursor = connection.cursor()
    sql = "CREATE TABLE `Names` (`TelegramID` INT PRIMARY KEY NOT NULL, `Trainername` TEXT, `Trainercode` INT(12))"
    cursor.execute(sql)
    sql = "CREATE TABLE `Silph` (`Username` TEXT, `SilphID` INT PRIMARY KEY NOT NULL)"
    cursor.execute(sql)
    sql = "CREATE TABLE `Groups` (`GroupID` INT PRIMARY KEY NOT NULL, `Rank` BOOLEAN, `IV` BOOLEAN, `Attacks` BOOLEAN, `Moves` BOOLEAN, `Language` TEXT)"
    cursor.execute(sql)
    sql = "CREATE TABLE `IV` (`TelegramID` INT PRIMARY KEY NOT NULL, `IV` BOOLEAN NOT NULL DEFAULT 1, `CP` BOOLEAN NOT NULL DEFAULT 1, `Level` BOOLEAN NOT NULL DEFAULT 1, `Stat Product` BOOLEAN NOT NULL DEFAULT 1, `Percent` BOOLEAN NOT NULL DEFAULT 1, `Percent minimum` BOOLEAN NOT NULL DEFAULT 1, `IV Percent` BOOLEAN  NOT NULL DEFAULT 0, `Base Stats` BOOLEAN  NOT NULL DEFAULT 0, `Feasible Combinations` BOOLEAN  NOT NULL DEFAULT 0)"
    cursor.execute(sql)
    sql = "CREATE TABLE `Moves` (`TelegramID` INT PRIMARY KEY NOT NULL, `Fast moves` BOOLEAN NOT NULL DEFAULT 1, `Charge moves` BOOLEAN  NOT NULL DEFAULT 1, `Legacy moves` BOOLEAN  NOT NULL DEFAULT 1, `Type` BOOLEAN  NOT NULL DEFAULT 1, `Damage` BOOLEAN  NOT NULL DEFAULT 1, `Duration` BOOLEAN  NOT NULL DEFAULT 1, `Energy` BOOLEAN  NOT NULL DEFAULT 1, `EPS` BOOLEAN  NOT NULL DEFAULT 0, `DPS` BOOLEAN  NOT NULL DEFAULT 0)"
    cursor.execute(sql)
    connection.commit()
    connection.close()

""" Connect to the database """
def connect():
    # Check, if we have a database. If it doesn't exist, create one
    if not os.path.exists("www/names.db"):
        logger.info("Datenbank names.db nicht vorhanden - Datenbank wird anglegt.")
        create_db()
    """ Connect to MySQL database """
    try:
        conn = sqlite3.connect("www/names.db")
        return conn
    except:
        logger.info("Error while connecting to database")

"""
Adds the SilphID associated with a user to the database. 
This reduces the queries to Silph since the ID doesn't
have to be searched on their website every time
"""
def add_silph_id(name, silph_id):
    conn = connect()
    cursor = conn.cursor()
    query = "INSERT INTO `Silph` (Username, SilphID) VALUES (?,?);"             
    cursor.execute(query, (name, silph_id,))
    conn.commit()
    conn.close()

"""
Returns the SilphID of a username. If it does not exist, return none
"""
def get_silph_id(name):
    conn = connect()
    cursor = conn.cursor()
    sql = "SELECT SilphID FROM Silph WHERE Username=?"
    logger.info("Get SilphID: %s, %s", sql, name)
    cursor.execute(sql, (name,))
    rows = cursor.fetchall()
    conn.close()
    try:
        silph_id = rows[0][0]
        logger.info("Return SilphID %s from user %s", silph_id, name)
        return id
    except:
        logger.info("No SilphID for user %s", name)
        return None

"""
Update the settings of for groups. Type represents the setting which should be updated
"""
def toggle_groups(update, context, type):
    #Check, if chat_id is negative (which is a telegram group) or if we want to set the language. 
    if update.message.chat_id > 0 and not type == 'Language':
        logger.info("/%s in private chat", type)
        language = get_language(update.message.chat_id)
        response = jsonresponse[language]['group_notice']
        context.bot.send_message(chat_id=update.message.chat_id, text=response)
        return
    
    #If we are in a group retrieve a list of admins
    if update.message.chat_id < 0:
        admins = (admin.user.id for admin in context.bot.get_chat_administrators(update.message.chat.id))     
    #Only continue, if the user is an admin or if its a private chat
    if update.message.chat_id > 0 or update._effective_user.id in admins:
        #Connect to database and prepare queries
        conn = connect()
        cursor = conn.cursor()
        insert = "INSERT INTO `Groups` (GroupID," + type + ") VALUES (?,?);"             
        change = "UPDATE `Groups` SET " + type + "=? WHERE GroupID=?;";
        #Try to insert a new entry for this group
        try:
            value = context.args[0] if (type=='Language') else context.args[0] == 'enable'  
            cursor.execute(insert, (update.message.chat_id, value,))
            logger.info("Insert new entry %s (%s, %s)", insert, update.message.chat_id, (context.args[0] == 'enable'))
        #If the entry already exists we get an error and update it instead
        except:
            value = context.args[0] if (type=='Language') else context.args[0] == 'enable'  
            cursor.execute(change, (value, update.message.chat_id,))
            logger.info("Update entry %s (%s, %s)", change, (context.args[0] == 'enable'), update.message.chat_id)

        conn.commit()
        conn.close()
        #Settings updaed successfully. Let the user know!
        logger.info("/%s by a admin %s changed to %s", type, update._effective_chat.username, context.args[0] == 'enable')
        language = get_language(update.message.chat_id)
        response = jsonresponse[language]['settings_updated']
        context.bot.send_message(chat_id=update.message.chat_id, text=response)
    #Delete the request if it was performed by a non admin in a group
    else:
        logger.info("/%s by a non-admin %s", type, update._effective_user.username)
        context.bot.delete_message(chat_id=update.message.chat_id,message_id=update.message.message_id)

"""
Update which IV attributes should be returned.
"""
def configure_iv_response(chat_id, table, field):
    #Connect to database and prepare queries
    conn = connect()
    cursor = conn.cursor()
    insert = "INSERT INTO `"+ table +"` (TelegramID,`" + field + "`) VALUES (?,?);"
    change = "UPDATE `"+ table +"` SET `" + field + "`=NOT `" + field + "` WHERE TelegramID=?;";
    #Try to insert a new entry for this group
    try:
        cursor.execute(insert, (chat_id, False,))
        logger.info("Insert new entry %s (%s, %s)", insert, chat_id, False)
    #If the entry already exists we get an error and update it instead
    except:
        cursor.execute(change, (chat_id,))
        logger.info("Update entry %s (%s, %s)", change, chat_id, field)

    conn.commit()
    conn.close()
    #Settings updated successfully. Let the user know!
    language = get_language(chat_id)
    response = jsonresponse[language]['settings_updated']
    return response

"""
Queries the database and returns if we have an entry for a specific group
Otherwise return true
"""
def get_iv_config(chat_id, table):
    conn = connect()
    cursor = conn.cursor()
    query = "SELECT * FROM `" + table + "` WHERE TelegramID="+str(chat_id)
    try:
        cursor.execute(query)
        conn.commit()
    except:
        logger.warn("Could not get group!" + query)
    rows = cursor.fetchall()
    names = list(map(lambda x: x[0], cursor.description))
    conn.close()
    try:
        config = dict(zip(names, rows[0]))
        logger.info("IV config: %s", config)
    except:
        #If the user has customised the output we want to return the default reponse
        #ChatID, IV, CP, Level, Stat Product, Percent, Percent minimum, IV-percent, FastMoves, ChargeMoves
        default_config = [chat_id, 1, 1, 1, 1, 1, 1]
        filler = np.zeros(len(names)-len(default_config))
        config = dict(zip(names, [*default_config, *filler]))
    return config
    

"""
Return if iv or rank checks are enabled in a given group
"""
def group_enabled(group_id, type):
    enabled = get_group_setting(group_id, type)
    return True if (enabled is None) else bool(enabled)

"""
Queries the database and returns if we have an entry for a specific group
Otherwise return true
"""
def get_group_setting(group_id, type):
    conn = connect()
    cursor = conn.cursor()
    query = "SELECT " + type + " FROM Groups WHERE GroupID="+str(group_id)
    try:
        cursor.execute(query)
        conn.commit()
    except:
        logger.warn("Could not get group!" + query)
    rows = cursor.fetchall()
    conn.close()
    try:
        logger.info("%s is on state %s for group %s", type, rows[0][0], group_id)
        return rows[0][0]
    except:
        return True
"""
Retrieves the language settings of a group - return english by default
"""
def get_language(group_id):
    language = get_group_setting(group_id, "Language")
    if str(language) not in language_support.supported_languages:
        return 'en'
    else:
        return language

""" Adds a new collumn to a table without deleting the whole database """    
#def add_column_to_table():
#    connection = sqlite3.connect("www/names.db")
#    cursor = connection.cursor()
#    sql = "ALTER TABLE `Groups` ADD `Language` TEXT"
#    cursor.execute(sql)
#    connection.commit()
#    connection.close()

def add_table_to_db():
    connection = sqlite3.connect("www/names.db")
    cursor = connection.cursor()
    connection.commit()
    sql = "CREATE TABLE `Moves` (`TelegramID` INT PRIMARY KEY NOT NULL, `Fast moves` BOOLEAN NOT NULL DEFAULT 1, `Charge moves` BOOLEAN  NOT NULL DEFAULT 1, `Legacy moves` BOOLEAN  NOT NULL DEFAULT 1, `Type` BOOLEAN  NOT NULL DEFAULT 1, `Damage` BOOLEAN  NOT NULL DEFAULT 1, `Duration` BOOLEAN  NOT NULL DEFAULT 1, `Energy` BOOLEAN  NOT NULL DEFAULT 1, `EPS` BOOLEAN  NOT NULL DEFAULT 0, `DPS` BOOLEAN  NOT NULL DEFAULT 0)"
    cursor.execute(sql)
    sql = "CREATE TABLE `IV_temp` (`TelegramID` INT PRIMARY KEY NOT NULL, `IV` BOOLEAN NOT NULL DEFAULT 1, `CP` BOOLEAN NOT NULL DEFAULT 1, `Level` BOOLEAN NOT NULL DEFAULT 1, `Stat Product` BOOLEAN NOT NULL DEFAULT 1, `Percent` BOOLEAN NOT NULL DEFAULT 1, `Percent minimum` BOOLEAN NOT NULL DEFAULT 1, `IV Percent` BOOLEAN  NOT NULL DEFAULT 0, `Base Stats` BOOLEAN  NOT NULL DEFAULT 0, `Feasible Combinations` BOOLEAN  NOT NULL DEFAULT 0);"
    cursor.execute(sql)
    sql = "INSERT INTO `IV_temp` (`TelegramID`, `IV`, `CP`, `Level`, `Stat Product`, `Percent`, `Percent minimum`, `Base Stats`, `Feasible Combinations`) SELECT `TelegramID`, `IV`, `CP`, `Level`, `Stat Product`, `Percent`, `Percent minimum`, `Base Stats`, `MinLevel` FROM `IV`;"
    cursor.execute(sql)
    sql = "DROP TABLE `IV`;"
    cursor.execute(sql)
    sql = "ALTER TABLE `IV_temp` RENAME TO `IV`;"
    cursor.execute(sql)
    connection.commit()
    connection.close()

if __name__ == '__main__':
    add_table_to_db()
