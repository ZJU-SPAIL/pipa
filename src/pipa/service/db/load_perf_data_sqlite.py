from __future__ import print_function

import sys
import struct
import sqlite3
import datetime

# An example of using this script with Intel PT:
#
# 	$ perf record -e intel_pt//u ls
# 	$ perf script -s src/pipa/service/db/load_perf_data_sqlite.py pt_example branches calls
# 	2017-07-31 14:26:07.326913 Creating database...
# 	2017-07-31 14:26:07.538097 Writing records...
# 	2017-07-31 14:26:09.889292 Adding indexes
# 	2017-07-31 14:26:09.958746 Done
#
# To browse the database, sqlite3 can be used e.g.
#
# 	$ sqlite3 pt_example
# 	sqlite> .header on
# 	sqlite> select * from samples_view where id < 10;
# 	sqlite> .mode column
# 	sqlite> select * from samples_view where id < 10;
# 	sqlite> .tables
# 	sqlite> .schema samples_view
# 	sqlite> .quit
#
# An example of using the database is provided by the script
# exported-sql-viewer.py.  Refer to that script for details.
#
# The database structure is practically the same as created by the script
# export-to-postgresql.py. Refer to that script for details.  A notable
# difference is  the 'transaction' column of the 'samples' table which is
# renamed 'transaction_' in sqlite because 'transaction' is a reserved word.

perf_db_export_mode = True
perf_db_export_calls = False
perf_db_export_callchains = False


def printerr(*args, **keyword_args):
    print(*args, file=sys.stderr, **keyword_args)


def printdate(*args, **kw_args):
    print(datetime.datetime.today(), *args, sep=" ", **kw_args)


def usage():
    printerr(
        "Usage is: export-to-sqlite.py <database name> [<columns>] [<calls>] [<callchains>] [<pyside-version-1>]"
    )
    printerr("where:  columns            'all' or 'branches'")
    printerr("        calls              'calls' => create calls and call_paths table")
    printerr("        callchains         'callchains' => create call_paths table")
    printerr("        pyside-version-1   'pyside-version-1' => use pyside version 1")
    raise Exception("Too few or bad arguments")


if len(sys.argv) < 2:
    usage()

dbname = sys.argv[1]

if len(sys.argv) >= 3:
    columns = sys.argv[2]
else:
    columns = "all"

if columns not in ("all", "branches"):
    usage()

branches = columns == "branches"

for i in range(3, len(sys.argv)):
    if sys.argv[i] == "calls":
        perf_db_export_calls = True
    elif sys.argv[i] == "callchains":
        perf_db_export_callchains = True
    elif sys.argv[i] == "pyside-version-1":
        pass
    else:
        usage()


def do_query(cursor, query, params=()):
    try:
        cursor.execute(query, params)
    except sqlite3.Error as e:
        raise Exception(f"Query failed: {e}")


def do_query_(cursor, query, params=()):
    try:
        cursor.execute(query, params)
    except sqlite3.Error as e:
        raise Exception(f"Query failed: {e}")


printdate("Creating database ...")

db_exists = False
try:
    f = open(dbname)
    f.close()
    db_exists = True
except Exception as e:
    pass

if db_exists:
    raise Exception(dbname + " already exists")

conn = sqlite3.connect(dbname)
cursor = conn.cursor()

do_query(cursor, "PRAGMA journal_mode = OFF")
do_query(cursor, "BEGIN TRANSACTION")

do_query(
    cursor,
    "CREATE TABLE selected_events ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "name		varchar(80))",
)
do_query(
    cursor,
    "CREATE TABLE machines ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "pid		integer,"
    "root_dir 	varchar(4096))",
)
do_query(
    cursor,
    "CREATE TABLE threads ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "machine_id	bigint,"
    "process_id	bigint,"
    "pid		integer,"
    "tid		integer)",
)
do_query(
    cursor,
    "CREATE TABLE comms ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "comm		varchar(16),"
    "c_thread_id	bigint,"
    "c_time		bigint,"
    "exec_flag	boolean)",
)
do_query(
    cursor,
    "CREATE TABLE comm_threads ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "comm_id	bigint,"
    "thread_id	bigint)",
)
do_query(
    cursor,
    "CREATE TABLE dsos ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "machine_id	bigint,"
    "short_name	varchar(256),"
    "long_name	varchar(4096),"
    "build_id	varchar(64))",
)
do_query(
    cursor,
    "CREATE TABLE symbols ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "dso_id		bigint,"
    "sym_start	bigint,"
    "sym_end	bigint,"
    "binding	integer,"
    "name		varchar(2048))",
)
do_query(
    cursor,
    "CREATE TABLE branch_types ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "name		varchar(80))",
)

if branches:
    do_query(
        cursor,
        "CREATE TABLE samples ("
        "id		integer		NOT NULL	PRIMARY KEY,"
        "evsel_id	bigint,"
        "machine_id	bigint,"
        "thread_id	bigint,"
        "comm_id	bigint,"
        "dso_id		bigint,"
        "symbol_id	bigint,"
        "sym_offset	bigint,"
        "ip		bigint,"
        "time		bigint,"
        "cpu		integer,"
        "to_dso_id	bigint,"
        "to_symbol_id	bigint,"
        "to_sym_offset	bigint,"
        "to_ip		bigint,"
        "branch_type	integer,"
        "in_tx		boolean,"
        "call_path_id	bigint,"
        "insn_count	bigint,"
        "cyc_count	bigint,"
        "flags		integer)",
    )
else:
    do_query(
        cursor,
        "CREATE TABLE samples ("
        "id		integer		NOT NULL	PRIMARY KEY,"
        "evsel_id	bigint,"
        "machine_id	bigint,"
        "thread_id	bigint,"
        "comm_id	bigint,"
        "dso_id		bigint,"
        "symbol_id	bigint,"
        "sym_offset	bigint,"
        "ip		bigint,"
        "time		bigint,"
        "cpu		integer,"
        "to_dso_id	bigint,"
        "to_symbol_id	bigint,"
        "to_sym_offset	bigint,"
        "to_ip		bigint,"
        "period		bigint,"
        "weight		bigint,"
        "transaction_	bigint,"
        "data_src	bigint,"
        "branch_type	integer,"
        "in_tx		boolean,"
        "call_path_id	bigint,"
        "insn_count	bigint,"
        "cyc_count	bigint,"
        "flags		integer)",
    )

if perf_db_export_calls or perf_db_export_callchains:
    do_query(
        cursor,
        "CREATE TABLE call_paths ("
        "id		integer		NOT NULL	PRIMARY KEY,"
        "parent_id	bigint,"
        "symbol_id	bigint,"
        "ip		bigint)",
    )
if perf_db_export_calls:
    do_query(
        cursor,
        "CREATE TABLE calls ("
        "id		integer		NOT NULL	PRIMARY KEY,"
        "thread_id	bigint,"
        "comm_id	bigint,"
        "call_path_id	bigint,"
        "call_time	bigint,"
        "return_time	bigint,"
        "branch_count	bigint,"
        "call_id	bigint,"
        "return_id	bigint,"
        "parent_call_path_id	bigint,"
        "flags		integer,"
        "parent_id	bigint,"
        "insn_count	bigint,"
        "cyc_count	bigint)",
    )

do_query(
    cursor,
    "CREATE TABLE ptwrite ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "payload	bigint,"
    "exact_ip	integer)",
)

do_query(
    cursor,
    "CREATE TABLE cbr ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "cbr		integer,"
    "mhz		integer,"
    "percent	integer)",
)

do_query(
    cursor,
    "CREATE TABLE mwait ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "hints		integer,"
    "extensions	integer)",
)

do_query(
    cursor,
    "CREATE TABLE pwre ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "cstate		integer,"
    "subcstate	integer,"
    "hw		integer)",
)

do_query(
    cursor,
    "CREATE TABLE exstop (" "id		integer		NOT NULL	PRIMARY KEY," "exact_ip	integer)",
)

do_query(
    cursor,
    "CREATE TABLE pwrx ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "deepest_cstate	integer,"
    "last_cstate	integer,"
    "wake_reason	integer)",
)

do_query(
    cursor,
    "CREATE TABLE context_switches ("
    "id		integer		NOT NULL	PRIMARY KEY,"
    "machine_id	bigint,"
    "time		bigint,"
    "cpu		integer,"
    "thread_out_id	bigint,"
    "comm_out_id	bigint,"
    "thread_in_id	bigint,"
    "comm_in_id	bigint,"
    "flags		integer)",
)

# printf was added to sqlite in version 3.8.3
sqlite_has_printf = False
try:
    do_query(cursor, 'SELECT printf("") FROM machines')
    sqlite_has_printf = True
except sqlite3.Error:
    pass


def emit_to_hex(x):
    # if sqlite_has_printf:
    #     return 'printf("%x", ' + x + ")"
    # else:
    return x


do_query(
    cursor,
    "CREATE VIEW machines_view AS "
    "SELECT "
    "id,"
    "pid,"
    "root_dir,"
    "CASE WHEN id=0 THEN 'unknown' WHEN pid=-1 THEN 'host' ELSE 'guest' END AS host_or_guest"
    " FROM machines",
)

do_query(
    cursor,
    "CREATE VIEW dsos_view AS "
    "SELECT "
    "id,"
    "machine_id,"
    "(SELECT host_or_guest FROM machines_view WHERE id = machine_id) AS host_or_guest,"
    "short_name,"
    "long_name,"
    "build_id"
    " FROM dsos",
)

do_query(
    cursor,
    "CREATE VIEW symbols_view AS "
    "SELECT "
    "id,"
    "name,"
    "(SELECT short_name FROM dsos WHERE id=dso_id) AS dso,"
    "dso_id,"
    "sym_start,"
    "sym_end,"
    "CASE WHEN binding=0 THEN 'local' WHEN binding=1 THEN 'global' ELSE 'weak' END AS binding"
    " FROM symbols",
)

do_query(
    cursor,
    "CREATE VIEW threads_view AS "
    "SELECT "
    "id,"
    "machine_id,"
    "(SELECT host_or_guest FROM machines_view WHERE id = machine_id) AS host_or_guest,"
    "process_id,"
    "pid,"
    "tid"
    " FROM threads",
)

do_query(
    cursor,
    "CREATE VIEW comm_threads_view AS "
    "SELECT "
    "comm_id,"
    "(SELECT comm FROM comms WHERE id = comm_id) AS command,"
    "thread_id,"
    "(SELECT pid FROM threads WHERE id = thread_id) AS pid,"
    "(SELECT tid FROM threads WHERE id = thread_id) AS tid"
    " FROM comm_threads",
)

if perf_db_export_calls or perf_db_export_callchains:
    do_query(
        cursor,
        "CREATE VIEW call_paths_view AS "
        "SELECT "
        "c.id," + emit_to_hex("c.ip") + " AS ip,"
        "c.symbol_id,"
        "(SELECT name FROM symbols WHERE id = c.symbol_id) AS symbol,"
        "(SELECT dso_id FROM symbols WHERE id = c.symbol_id) AS dso_id,"
        "(SELECT dso FROM symbols_view  WHERE id = c.symbol_id) AS dso_short_name,"
        "c.parent_id," + emit_to_hex("p.ip") + " AS parent_ip,"
        "p.symbol_id AS parent_symbol_id,"
        "(SELECT name FROM symbols WHERE id = p.symbol_id) AS parent_symbol,"
        "(SELECT dso_id FROM symbols WHERE id = p.symbol_id) AS parent_dso_id,"
        "(SELECT dso FROM symbols_view  WHERE id = p.symbol_id) AS parent_dso_short_name"
        " FROM call_paths c INNER JOIN call_paths p ON p.id = c.parent_id",
    )
if perf_db_export_calls:
    do_query(
        cursor,
        "CREATE VIEW calls_view AS "
        "SELECT "
        "calls.id,"
        "thread_id,"
        "(SELECT pid FROM threads WHERE id = thread_id) AS pid,"
        "(SELECT tid FROM threads WHERE id = thread_id) AS tid,"
        "(SELECT comm FROM comms WHERE id = comm_id) AS command,"
        "call_path_id," + emit_to_hex("ip") + " AS ip,"
        "symbol_id,"
        "(SELECT name FROM symbols WHERE id = symbol_id) AS symbol,"
        "call_time,"
        "return_time,"
        "return_time - call_time AS elapsed_time,"
        "branch_count,"
        "insn_count,"
        "cyc_count,"
        "CASE WHEN cyc_count=0 THEN CAST(0 AS FLOAT) ELSE ROUND(CAST(insn_count AS FLOAT) / cyc_count, 2) END AS IPC,"
        "call_id,"
        "return_id,"
        "CASE WHEN flags=0 THEN '' WHEN flags=1 THEN 'no call' WHEN flags=2 THEN 'no return' WHEN flags=3 THEN 'no call/return' WHEN flags=6 THEN 'jump' ELSE flags END AS flags,"
        "parent_call_path_id,"
        "calls.parent_id"
        " FROM calls INNER JOIN call_paths ON call_paths.id = call_path_id",
    )

do_query(
    cursor,
    "CREATE VIEW samples_view AS "
    "SELECT "
    "id,"
    "time,"
    "cpu,"
    "(SELECT pid FROM threads WHERE id = thread_id) AS pid,"
    "(SELECT tid FROM threads WHERE id = thread_id) AS tid,"
    "(SELECT comm FROM comms WHERE id = comm_id) AS command,"
    "(SELECT name FROM selected_events WHERE id = evsel_id) AS event,"
    + emit_to_hex("ip")
    + " AS ip_hex,"
    "(SELECT name FROM symbols WHERE id = symbol_id) AS symbol,"
    "sym_offset,"
    "(SELECT short_name FROM dsos WHERE id = dso_id) AS dso_short_name,"
    + emit_to_hex("to_ip")
    + " AS to_ip_hex,"
    "(SELECT name FROM symbols WHERE id = to_symbol_id) AS to_symbol,"
    "to_sym_offset,"
    "(SELECT short_name FROM dsos WHERE id = to_dso_id) AS to_dso_short_name,"
    "(SELECT name FROM branch_types WHERE id = branch_type) AS branch_type_name,"
    "in_tx,"
    "insn_count,"
    "cyc_count,"
    "CASE WHEN cyc_count=0 THEN CAST(0 AS FLOAT) ELSE ROUND(CAST(insn_count AS FLOAT) / cyc_count, 2) END AS IPC,"
    "flags"
    " FROM samples",
)

do_query(
    cursor,
    "CREATE VIEW ptwrite_view AS "
    "SELECT "
    "ptwrite.id,"
    "time,"
    "cpu," + emit_to_hex("payload") + " AS payload_hex,"
    "CASE WHEN exact_ip=0 THEN 'False' ELSE 'True' END AS exact_ip"
    " FROM ptwrite"
    " INNER JOIN samples ON samples.id = ptwrite.id",
)

do_query(
    cursor,
    "CREATE VIEW cbr_view AS "
    "SELECT "
    "cbr.id,"
    "time,"
    "cpu,"
    "cbr,"
    "mhz,"
    "percent"
    " FROM cbr"
    " INNER JOIN samples ON samples.id = cbr.id",
)

do_query(
    cursor,
    "CREATE VIEW mwait_view AS "
    "SELECT "
    "mwait.id,"
    "time,"
    "cpu,"
    + emit_to_hex("hints")
    + " AS hints_hex,"
    + emit_to_hex("extensions")
    + " AS extensions_hex"
    " FROM mwait"
    " INNER JOIN samples ON samples.id = mwait.id",
)

do_query(
    cursor,
    "CREATE VIEW pwre_view AS "
    "SELECT "
    "pwre.id,"
    "time,"
    "cpu,"
    "cstate,"
    "subcstate,"
    "CASE WHEN hw=0 THEN 'False' ELSE 'True' END AS hw"
    " FROM pwre"
    " INNER JOIN samples ON samples.id = pwre.id",
)

do_query(
    cursor,
    "CREATE VIEW exstop_view AS "
    "SELECT "
    "exstop.id,"
    "time,"
    "cpu,"
    "CASE WHEN exact_ip=0 THEN 'False' ELSE 'True' END AS exact_ip"
    " FROM exstop"
    " INNER JOIN samples ON samples.id = exstop.id",
)

do_query(
    cursor,
    "CREATE VIEW pwrx_view AS "
    "SELECT "
    "pwrx.id,"
    "time,"
    "cpu,"
    "deepest_cstate,"
    "last_cstate,"
    "CASE     WHEN wake_reason=1 THEN 'Interrupt'"
    " WHEN wake_reason=2 THEN 'Timer Deadline'"
    " WHEN wake_reason=4 THEN 'Monitored Address'"
    " WHEN wake_reason=8 THEN 'HW'"
    " ELSE wake_reason "
    "END AS wake_reason"
    " FROM pwrx"
    " INNER JOIN samples ON samples.id = pwrx.id",
)

do_query(
    cursor,
    "CREATE VIEW power_events_view AS "
    "SELECT "
    "samples.id,"
    "time,"
    "cpu,"
    "selected_events.name AS event,"
    "CASE WHEN selected_events.name='cbr' THEN (SELECT cbr FROM cbr WHERE cbr.id = samples.id) ELSE \"\" END AS cbr,"
    "CASE WHEN selected_events.name='cbr' THEN (SELECT mhz FROM cbr WHERE cbr.id = samples.id) ELSE \"\" END AS mhz,"
    "CASE WHEN selected_events.name='cbr' THEN (SELECT percent FROM cbr WHERE cbr.id = samples.id) ELSE \"\" END AS percent,"
    "CASE WHEN selected_events.name='mwait' THEN (SELECT "
    + emit_to_hex("hints")
    + ' FROM mwait WHERE mwait.id = samples.id) ELSE "" END AS hints_hex,'
    "CASE WHEN selected_events.name='mwait' THEN (SELECT "
    + emit_to_hex("extensions")
    + ' FROM mwait WHERE mwait.id = samples.id) ELSE "" END AS extensions_hex,'
    "CASE WHEN selected_events.name='pwre' THEN (SELECT cstate FROM pwre WHERE pwre.id = samples.id) ELSE \"\" END AS cstate,"
    "CASE WHEN selected_events.name='pwre' THEN (SELECT subcstate FROM pwre WHERE pwre.id = samples.id) ELSE \"\" END AS subcstate,"
    "CASE WHEN selected_events.name='pwre' THEN (SELECT hw FROM pwre WHERE pwre.id = samples.id) ELSE \"\" END AS hw,"
    "CASE WHEN selected_events.name='exstop' THEN (SELECT exact_ip FROM exstop WHERE exstop.id = samples.id) ELSE \"\" END AS exact_ip,"
    "CASE WHEN selected_events.name='pwrx' THEN (SELECT deepest_cstate FROM pwrx WHERE pwrx.id = samples.id) ELSE \"\" END AS deepest_cstate,"
    "CASE WHEN selected_events.name='pwrx' THEN (SELECT last_cstate FROM pwrx WHERE pwrx.id = samples.id) ELSE \"\" END AS last_cstate,"
    "CASE WHEN selected_events.name='pwrx' THEN (SELECT "
    "CASE     WHEN wake_reason=1 THEN 'Interrupt'"
    " WHEN wake_reason=2 THEN 'Timer Deadline'"
    " WHEN wake_reason=4 THEN 'Monitored Address'"
    " WHEN wake_reason=8 THEN 'HW'"
    " ELSE wake_reason "
    "END"
    ' FROM pwrx WHERE pwrx.id = samples.id) ELSE "" END AS wake_reason'
    " FROM samples"
    " INNER JOIN selected_events ON selected_events.id = evsel_id"
    " WHERE selected_events.name IN ('cbr','mwait','exstop','pwre','pwrx')",
)

do_query(
    cursor,
    "CREATE VIEW context_switches_view AS "
    "SELECT "
    "context_switches.id,"
    "context_switches.machine_id,"
    "context_switches.time,"
    "context_switches.cpu,"
    "th_out.pid AS pid_out,"
    "th_out.tid AS tid_out,"
    "comm_out.comm AS comm_out,"
    "th_in.pid AS pid_in,"
    "th_in.tid AS tid_in,"
    "comm_in.comm AS comm_in,"
    "CASE	  WHEN context_switches.flags = 0 THEN 'in'"
    " WHEN context_switches.flags = 1 THEN 'out'"
    " WHEN context_switches.flags = 3 THEN 'out preempt'"
    " ELSE context_switches.flags "
    "END AS flags"
    " FROM context_switches"
    " INNER JOIN threads AS th_out ON th_out.id   = context_switches.thread_out_id"
    " INNER JOIN threads AS th_in  ON th_in.id    = context_switches.thread_in_id"
    " INNER JOIN comms AS comm_out ON comm_out.id = context_switches.comm_out_id"
    " INNER JOIN comms AS comm_in  ON comm_in.id  = context_switches.comm_in_id",
)

do_query(cursor, "END TRANSACTION")
conn.commit()


printdate("Database setup completed.")


# 插入数据函数
def insert_selected_events(cursor, values):
    cursor.execute("INSERT INTO selected_events VALUES (?, ?)", values)


def insert_machines(cursor, values):
    cursor.execute("INSERT INTO machines VALUES (?, ?, ?)", values)


def insert_threads(cursor, values):
    cursor.execute("INSERT INTO threads VALUES (?, ?, ?, ?, ?)", values)


def insert_comms(cursor, values):
    cursor.execute("INSERT INTO comms VALUES (?, ?, ?, ?, ?)", values)


def insert_comm_threads(cursor, values):
    cursor.execute("INSERT INTO comm_threads VALUES (?, ?, ?)", values)


def insert_dsos(cursor, values):
    cursor.execute("INSERT INTO dsos VALUES (?, ?, ?, ?, ?)", values)


def insert_symbols(cursor, values):
    cursor.execute("INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?)", values)


def insert_branch_types(cursor, values):
    cursor.execute("INSERT INTO branch_types VALUES (?, ?)", values)


def insert_samples(cursor, values):
    if branches:
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
    else:
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )


def insert_call_paths(cursor, values):
    cursor.execute("INSERT INTO call_paths VALUES (?, ?, ?, ?)", values)


def insert_calls(cursor, values):
    cursor.execute(
        "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values
    )


def trace_begin():
    printdate("Writing records...")
    do_query(cursor, "BEGIN TRANSACTION")

    # 插入初始数据
    insert_selected_events(cursor, (0, "unknown"))
    insert_machines(cursor, (0, 0, "unknown"))
    insert_threads(cursor, (0, 0, 0, -1, -1))
    insert_comms(cursor, (0, "unknown", 0, 0, 0))
    insert_dsos(cursor, (0, 0, "unknown", "unknown", ""))
    insert_symbols(cursor, (0, 0, 0, 0, 0, "unknown"))

    if branches:
        insert_samples(
            cursor, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        )
    else:
        insert_samples(
            cursor,
            (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        )

    if perf_db_export_calls or perf_db_export_callchains:
        insert_call_paths(cursor, (0, 0, 0, 0))
        insert_calls(cursor, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))


unhandled_count = 0


def trace_end():
    do_query(cursor, "END TRANSACTION")
    conn.commit()

    printdate("Adding indexes")
    if perf_db_export_calls:
        do_query(cursor, "CREATE INDEX pcpid_idx ON calls (parent_call_path_id)")
        do_query(cursor, "CREATE INDEX pid_idx ON calls (parent_id)")
        do_query(cursor, "ALTER TABLE comms ADD COLUMN has_calls boolean")
        do_query(
            cursor,
            "UPDATE comms SET has_calls = 1 WHERE comms.id IN (SELECT DISTINCT comm_id FROM calls)",
        )

    printdate("Dropping unused tables")
    if is_table_empty("ptwrite"):
        drop("ptwrite")
    if (
        is_table_empty("mwait")
        and is_table_empty("pwre")
        and is_table_empty("exstop")
        and is_table_empty("pwrx")
    ):
        do_query(cursor, "DROP VIEW power_events_view")
        drop("mwait")
        drop("pwre")
        drop("exstop")
        drop("pwrx")
        if is_table_empty("cbr"):
            drop("cbr")
    if is_table_empty("context_switches"):
        drop("context_switches")

    if unhandled_count:
        printdate("Warning: ", unhandled_count, " unhandled events")
    printdate("Done")


def is_table_empty(table_name):
    do_query(cursor, f"SELECT * FROM {table_name} LIMIT 1")
    if cursor.fetchone():
        return False
    return True


def drop(table_name):
    do_query(cursor, f"DROP VIEW IF EXISTS {table_name}_view")
    do_query(cursor, f"DROP TABLE IF EXISTS {table_name}")


def trace_unhandled(event_name, context, event_fields_dict):
    global unhandled_count
    unhandled_count += 1


def sched__sched_switch(*x):
    pass


def bind_exec(cursor, query, values):
    cursor.execute(query, values)


def evsel_table(*x):
    bind_exec(cursor, "INSERT INTO selected_events VALUES (?, ?)", x)


def machine_table(*x):
    bind_exec(cursor, "INSERT INTO machines VALUES (?, ?, ?)", x)


def thread_table(*x):
    bind_exec(cursor, "INSERT INTO threads VALUES (?, ?, ?, ?, ?)", x)


def comm_table(*x):
    bind_exec(cursor, "INSERT INTO comms VALUES (?, ?, ?, ?, ?)", x)


def comm_thread_table(*x):
    bind_exec(cursor, "INSERT INTO comm_threads VALUES (?, ?, ?)", x)


def dso_table(*x):
    bind_exec(cursor, "INSERT INTO dsos VALUES (?, ?, ?, ?, ?)", x)


def symbol_table(*x):
    bind_exec(cursor, "INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?)", x)


def branch_type_table(*x):
    bind_exec(cursor, "INSERT INTO branch_types VALUES (?, ?)", x)


def sample_table(*x):
    if branches:
        values = x[:15] + x[19:25]
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
    else:
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            x[:25],
        )


def call_path_table(*x):
    bind_exec(cursor, "INSERT INTO call_paths VALUES (?, ?, ?, ?)", x)


def call_return_table(*x):
    bind_exec(
        cursor, "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", x
    )


def ptwrite(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    flags = data[0]
    payload = data[1]
    exact_ip = flags & 1
    insert_values = (id, payload, exact_ip)
    bind_exec(cursor, "INSERT INTO ptwrite VALUES (?, ?, ?)", insert_values)


def cbr(id, raw_buf):
    data = struct.unpack_from("<BBBBII", raw_buf)
    cbr = data[0]
    MHz = (data[4] + 500) / 1000
    percent = ((cbr * 1000 / data[2]) + 5) / 10
    insert_values = (id, cbr, MHz, percent)
    bind_exec(cursor, "INSERT INTO cbr VALUES (?, ?, ?, ?)", insert_values)


def mwait(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    hints = payload & 0xFF
    extensions = (payload >> 32) & 0x3
    insert_values = (id, hints, extensions)
    bind_exec(cursor, "INSERT INTO mwait VALUES (?, ?, ?)", insert_values)


def pwre(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    hw = (payload >> 7) & 1
    cstate = (payload >> 12) & 0xF
    subcstate = (payload >> 8) & 0xF
    insert_values = (id, cstate, subcstate, hw)
    bind_exec(cursor, "INSERT INTO pwre VALUES (?, ?, ?, ?)", insert_values)


def exstop(id, raw_buf):
    data = struct.unpack_from("<I", raw_buf)
    flags = data[0]
    exact_ip = flags & 1
    insert_values = (id, exact_ip)
    bind_exec(cursor, "INSERT INTO exstop VALUES (?, ?)", insert_values)


def pwrx(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    deepest_cstate = payload & 0xF
    last_cstate = (payload >> 4) & 0xF
    wake_reason = (payload >> 8) & 0xF
    insert_values = (id, deepest_cstate, last_cstate, wake_reason)
    bind_exec(cursor, "INSERT INTO pwrx VALUES (?, ?, ?, ?)", insert_values)


def synth_data(id, config, raw_buf, *x):
    if config == 0:
        ptwrite(id, raw_buf)
    elif config == 1:
        mwait(id, raw_buf)
    elif config == 2:
        pwre(id, raw_buf)
    elif config == 3:
        exstop(id, raw_buf)
    elif config == 4:
        pwrx(id, raw_buf)
    elif config == 5:
        cbr(id, raw_buf)


def context_switch_table(*x):
    bind_exec(
        cursor, "INSERT INTO context_switches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", x
    )
