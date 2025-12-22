from __future__ import print_function

import csv
import datetime
import os
import sqlite3
import struct
import sys

perf_db_export_mode = True
perf_db_export_calls = False
perf_db_export_callchains = False
export_csv_dir = None

call_path_events = 0
call_return_events = 0

conn = None
cur = None
branches = False
call_path_insert_sql = None
call_insert_sql = None
sample_insert_sql = None
unhandled_count = 0
sqlite_has_printf = False
dbname = ""


def printerr(*args, **keyword_args):
    print(*args, file=sys.stderr, **keyword_args)


def printdate(*args, **kw_args):
    print(datetime.datetime.today(), *args, sep=" ", **kw_args)


def usage():
    printerr(
        "Usage: pipa-perf-sqlite <database name> [<columns>] [<calls>] [<callchains>] [<csv[=dir>]]"
    )
    printerr("where:  columns            'all' or 'branches'")
    printerr("        calls              'calls' => create calls and call_paths table")
    printerr(
        "        callchains         'callchains' => create call_paths table (implied by calls)"
    )
    printerr("        csv[=dir]          export all tables to CSVs (default dir '.')")
    raise Exception("Too few or bad arguments")


def do_query(sql, params=()):
    try:
        cur.execute(sql, params)
    except sqlite3.Error as e:
        raise Exception("Query failed: " + str(e))


def do_script(sql):
    try:
        cur.executescript(sql)
    except sqlite3.Error as e:
        raise Exception("Query failed: " + str(e))


def emit_to_hex(x):
    if sqlite_has_printf:
        return 'printf("%x", ' + x + ")"
    return x


def bind_exec(sql_stmt, n, x):
    params = tuple("0" if xx is None else str(xx) for xx in x[:n])
    do_query(sql_stmt, params)


def evsel_table(*x):
    bind_exec(insert_sql["evsel"], 2, x)


def machine_table(*x):
    bind_exec(insert_sql["machine"], 3, x)


def thread_table(*x):
    bind_exec(insert_sql["thread"], 5, x)


def comm_table(*x):
    bind_exec(insert_sql["comm"], 5, x)


def comm_thread_table(*x):
    bind_exec(insert_sql["comm_thread"], 3, x)


def dso_table(*x):
    bind_exec(insert_sql["dso"], 5, x)


def symbol_table(*x):
    bind_exec(insert_sql["symbol"], 6, x)


def branch_type_table(*x):
    bind_exec(insert_sql["branch_type"], 2, x)


def sample_table(*x):
    vals = list(x)
    if len(vals) < 25:
        vals += [0] * (25 - len(vals))
    elif len(vals) > 25:
        vals = vals[:25]

    if branches:
        params = vals[:15] + vals[19:25]
        do_query(
            sample_insert_sql, tuple("0" if xx is None else str(xx) for xx in params)
        )
    else:
        bind_exec(sample_insert_sql, 25, vals)


def call_path_table(*x):
    global call_path_events
    if call_path_insert_sql is None:
        return
    call_path_events += 1
    bind_exec(call_path_insert_sql, 4, x)


def call_return_table(*x):
    global call_return_events
    if call_insert_sql is None:
        return
    call_return_events += 1
    bind_exec(call_insert_sql, 14, x)


def ptwrite(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    flags = data[0]
    payload = data[1]
    exact_ip = flags & 1
    do_query(insert_sql["ptwrite"], (str(id), str(payload), str(exact_ip)))


def cbr(id, raw_buf):
    data = struct.unpack_from("<BBBBII", raw_buf)
    cbr_val = data[0]
    mhz = (data[4] + 500) // 1000
    percent = ((cbr_val * 1000 // data[2]) + 5) // 10
    do_query(insert_sql["cbr"], (str(id), str(cbr_val), str(mhz), str(percent)))


def mwait(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    hints = payload & 0xFF
    extensions = (payload >> 32) & 0x3
    do_query(insert_sql["mwait"], (str(id), str(hints), str(extensions)))


def pwre(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    hw = (payload >> 7) & 1
    cstate = (payload >> 12) & 0xF
    subcstate = (payload >> 8) & 0xF
    do_query(insert_sql["pwre"], (str(id), str(cstate), str(subcstate), str(hw)))


def exstop(id, raw_buf):
    data = struct.unpack_from("<I", raw_buf)
    flags = data[0]
    exact_ip = flags & 1
    do_query(insert_sql["exstop"], (str(id), str(exact_ip)))


def pwrx(id, raw_buf):
    data = struct.unpack_from("<IQ", raw_buf)
    payload = data[1]
    deepest_cstate = payload & 0xF
    last_cstate = (payload >> 4) & 0xF
    wake_reason = (payload >> 8) & 0xF
    do_query(
        insert_sql["pwrx"],
        (str(id), str(deepest_cstate), str(last_cstate), str(wake_reason)),
    )


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
    bind_exec(insert_sql["context_switch"], 9, x)


def trace_begin():
    printdate("Writing records...")
    do_query("BEGIN TRANSACTION")
    evsel_table(0, "unknown")
    machine_table(0, 0, "unknown")
    thread_table(0, 0, 0, -1, -1)
    comm_table(0, "unknown", 0, 0, 0)
    dso_table(0, 0, "unknown", "unknown", "")
    symbol_table(0, 0, 0, 0, 0, "unknown")
    sample_table(
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    )
    if call_path_insert_sql is not None:
        call_path_table(0, 0, 0, 0)
    if call_insert_sql is not None:
        call_return_table(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def is_table_empty(table_name):
    try:
        do_query("SELECT 1 FROM " + table_name + " LIMIT 1")
        return cur.fetchone() is None
    except Exception:
        return True


def drop(table_name):
    do_query("DROP VIEW IF EXISTS " + table_name + "_view")
    do_query("DROP TABLE IF EXISTS " + table_name)


def export_all_tables_to_csv(out_dir):
    if out_dir is None:
        return
    try:
        os.makedirs(out_dir, exist_ok=True)
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            safe_table = '"' + t.replace('"', '""') + '"'
            cur.execute(f"SELECT * FROM {safe_table}")
            cols = [desc[0] for desc in cur.description]
            out_path = os.path.join(out_dir, f"{t}.csv")
            with open(out_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                while True:
                    rows = cur.fetchmany(10000)
                    if not rows:
                        break
                    writer.writerows(rows)
            printdate("Exported", out_path)
    except Exception as e:
        printerr("CSV export failed:", e)


def trace_end():
    do_query("END TRANSACTION")

    printdate("Adding indexes")
    if perf_db_export_calls:
        do_query("CREATE INDEX IF NOT EXISTS pcpid_idx ON calls (parent_call_path_id)")
        do_query("CREATE INDEX IF NOT EXISTS pid_idx ON calls (parent_id)")
        try:
            do_query("ALTER TABLE comms ADD COLUMN has_calls boolean")
        except Exception:
            pass
        do_query(
            "UPDATE comms SET has_calls = 1 WHERE comms.id IN (SELECT DISTINCT comm_id FROM calls)"
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
        drop("power_events")
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
    printdate("Stats:", "call_paths=", call_path_events, "calls=", call_return_events)
    conn.commit()
    export_all_tables_to_csv(export_csv_dir)


def trace_unhandled(event_name, context, event_fields_dict):
    global unhandled_count
    unhandled_count += 1


def sched__sched_switch(*x):
    pass


def main(argv=None):
    global perf_db_export_mode
    global perf_db_export_calls
    global perf_db_export_callchains
    global export_csv_dir
    global call_path_events
    global call_return_events
    global conn
    global cur
    global branches
    global call_path_insert_sql
    global call_insert_sql
    global sample_insert_sql
    global unhandled_count
    global sqlite_has_printf
    global dbname
    global insert_sql

    argv = list(sys.argv[1:] if argv is None else argv)

    perf_db_export_mode = True
    perf_db_export_calls = False
    perf_db_export_callchains = False
    export_csv_dir = None
    call_path_events = 0
    call_return_events = 0
    unhandled_count = 0

    if len(argv) < 1:
        usage()

    dbname = argv[0]

    columns = "all"
    arg_start = 1
    if len(argv) >= 2 and argv[1] in ("all", "branches"):
        columns = argv[1]
        arg_start = 2

    if columns not in ("all", "branches"):
        usage()

    branches = columns == "branches"

    for arg in argv[arg_start:]:
        if arg == "calls":
            perf_db_export_calls = True
        elif arg == "callchains":
            perf_db_export_callchains = True
        elif arg.startswith("csv"):
            if export_csv_dir is not None:
                usage()
            if arg == "csv":
                export_csv_dir = os.getcwd()
            elif arg.startswith("csv="):
                export_csv_dir = os.path.abspath(arg.split("=", 1)[1])
            else:
                usage()
        else:
            usage()

    if perf_db_export_calls:
        perf_db_export_callchains = True

    printdate("Creating database ...")

    db_exists = False
    try:
        with open(dbname):
            db_exists = True
    except Exception:
        pass

    if db_exists:
        raise Exception(dbname + " already exists")

    conn = sqlite3.connect(dbname)
    cur = conn.cursor()

    do_query("PRAGMA journal_mode = OFF")
    do_query("BEGIN TRANSACTION")

    schema_statements = []
    schema_statements.append(
        """CREATE TABLE selected_events (
    id          integer     NOT NULL    PRIMARY KEY,
    name        varchar(80)
)"""
    )
    schema_statements.append(
        """CREATE TABLE machines (
    id          integer     NOT NULL    PRIMARY KEY,
    pid         integer,
    root_dir    varchar(4096)
)"""
    )
    schema_statements.append(
        """CREATE TABLE threads (
    id          integer     NOT NULL    PRIMARY KEY,
    machine_id  bigint,
    process_id  bigint,
    pid         integer,
    tid         integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE comms (
    id          integer     NOT NULL    PRIMARY KEY,
    comm        varchar(16),
    c_thread_id bigint,
    c_time      bigint,
    exec_flag   boolean
)"""
    )
    schema_statements.append(
        """CREATE TABLE comm_threads (
    id          integer     NOT NULL    PRIMARY KEY,
    comm_id     bigint,
    thread_id   bigint
)"""
    )
    schema_statements.append(
        """CREATE TABLE dsos (
    id          integer     NOT NULL    PRIMARY KEY,
    machine_id  bigint,
    short_name  varchar(256),
    long_name   varchar(4096),
    build_id    varchar(64)
)"""
    )
    schema_statements.append(
        """CREATE TABLE symbols (
    id          integer     NOT NULL    PRIMARY KEY,
    dso_id      bigint,
    sym_start   bigint,
    sym_end     bigint,
    binding     integer,
    name        varchar(2048)
)"""
    )
    schema_statements.append(
        """CREATE TABLE branch_types (
    id          integer     NOT NULL    PRIMARY KEY,
    name        varchar(80)
)"""
    )

    if branches:
        schema_statements.append(
            """CREATE TABLE samples (
        id          integer     NOT NULL    PRIMARY KEY,
        evsel_id    bigint,
        machine_id  bigint,
        thread_id   bigint,
        comm_id     bigint,
        dso_id      bigint,
        symbol_id   bigint,
        sym_offset  bigint,
        ip          bigint,
        time        bigint,
        cpu         integer,
        to_dso_id   bigint,
        to_symbol_id bigint,
        to_sym_offset bigint,
        to_ip       bigint,
        branch_type integer,
        in_tx       boolean,
        call_path_id bigint,
        insn_count  bigint,
        cyc_count   bigint,
        flags       integer
    )"""
        )
    else:
        schema_statements.append(
            """CREATE TABLE samples (
        id          integer     NOT NULL    PRIMARY KEY,
        evsel_id    bigint,
        machine_id  bigint,
        thread_id   bigint,
        comm_id     bigint,
        dso_id      bigint,
        symbol_id   bigint,
        sym_offset  bigint,
        ip          bigint,
        time        bigint,
        cpu         integer,
        to_dso_id   bigint,
        to_symbol_id bigint,
        to_sym_offset bigint,
        to_ip       bigint,
        period      bigint,
        weight      bigint,
        transaction_ bigint,
        data_src    bigint,
        branch_type integer,
        in_tx       boolean,
        call_path_id bigint,
        insn_count  bigint,
        cyc_count   bigint,
        flags       integer
    )"""
        )

    if perf_db_export_calls or perf_db_export_callchains:
        schema_statements.append(
            """CREATE TABLE call_paths (
        id          integer     NOT NULL    PRIMARY KEY,
        parent_id   bigint,
        symbol_id   bigint,
        ip          bigint
    )"""
        )
    if perf_db_export_calls:
        schema_statements.append(
            """CREATE TABLE calls (
        id          integer     NOT NULL    PRIMARY KEY,
        thread_id   bigint,
        comm_id     bigint,
        call_path_id bigint,
        call_time   bigint,
        return_time bigint,
        branch_count bigint,
        call_id     bigint,
        return_id   bigint,
        parent_call_path_id bigint,
        flags       integer,
        parent_id   bigint,
        insn_count  bigint,
        cyc_count   bigint
    )"""
        )

    schema_statements.append(
        """CREATE TABLE ptwrite (
    id          integer     NOT NULL    PRIMARY KEY,
    payload     bigint,
    exact_ip    integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE cbr (
    id          integer     NOT NULL    PRIMARY KEY,
    cbr         integer,
    mhz         integer,
    percent     integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE mwait (
    id          integer     NOT NULL    PRIMARY KEY,
    hints       integer,
    extensions  integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE pwre (
    id          integer     NOT NULL    PRIMARY KEY,
    cstate      integer,
    subcstate   integer,
    hw          integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE exstop (
    id          integer     NOT NULL    PRIMARY KEY,
    exact_ip    integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE pwrx (
    id              integer     NOT NULL    PRIMARY KEY,
    deepest_cstate  integer,
    last_cstate     integer,
    wake_reason     integer
)"""
    )
    schema_statements.append(
        """CREATE TABLE context_switches (
    id              integer     NOT NULL    PRIMARY KEY,
    machine_id      bigint,
    time            bigint,
    cpu             integer,
    thread_out_id   bigint,
    comm_out_id     bigint,
    thread_in_id    bigint,
    comm_in_id      bigint,
    flags           integer
)"""
    )

    for stmt in schema_statements:
        do_query(stmt)

    try:
        do_query('SELECT printf("")')
        sqlite_has_printf = True
    except Exception:
        sqlite_has_printf = False

    views = []
    views.append(
        """CREATE VIEW machines_view AS
SELECT id, pid, root_dir,
    CASE WHEN id=0 THEN 'unknown' WHEN pid=-1 THEN 'host' ELSE 'guest' END AS host_or_guest
FROM machines"""
    )
    views.append(
        """CREATE VIEW dsos_view AS
SELECT id, machine_id,
    (SELECT host_or_guest FROM machines_view WHERE id = machine_id) AS host_or_guest,
    short_name, long_name, build_id
FROM dsos"""
    )
    views.append(
        """CREATE VIEW symbols_view AS
SELECT id, name,
    (SELECT short_name FROM dsos WHERE id=dso_id) AS dso,
    dso_id, sym_start, sym_end,
    CASE WHEN binding=0 THEN 'local' WHEN binding=1 THEN 'global' ELSE 'weak' END AS binding
FROM symbols"""
    )
    views.append(
        """CREATE VIEW threads_view AS
SELECT id, machine_id,
    (SELECT host_or_guest FROM machines_view WHERE id = machine_id) AS host_or_guest,
    process_id, pid, tid
FROM threads"""
    )
    views.append(
        """CREATE VIEW comm_threads_view AS
SELECT comm_id,
    (SELECT comm FROM comms WHERE id = comm_id) AS command,
    thread_id,
    (SELECT pid FROM threads WHERE id = thread_id) AS pid,
    (SELECT tid FROM threads WHERE id = thread_id) AS tid
FROM comm_threads"""
    )

    if perf_db_export_calls or perf_db_export_callchains:
        views.append(
            """CREATE VIEW call_paths_view AS
SELECT
    c.id,
    """
            + emit_to_hex("c.ip")
            + """ AS ip,
    c.symbol_id,
    (SELECT name FROM symbols WHERE id = c.symbol_id) AS symbol,
    (SELECT dso_id FROM symbols WHERE id = c.symbol_id) AS dso_id,
    (SELECT dso FROM symbols_view WHERE id = c.symbol_id) AS dso_short_name,
    c.parent_id,
    """
            + emit_to_hex("p.ip")
            + """ AS parent_ip,
    p.symbol_id AS parent_symbol_id,
    (SELECT name FROM symbols WHERE id = p.symbol_id) AS parent_symbol,
    (SELECT dso_id FROM symbols WHERE id = p.symbol_id) AS parent_dso_id,
    (SELECT dso FROM symbols_view WHERE id = p.symbol_id) AS parent_dso_short_name
FROM call_paths c INNER JOIN call_paths p ON p.id = c.parent_id"""
        )
    if perf_db_export_calls:
        views.append(
            """CREATE VIEW calls_view AS
SELECT
    calls.id,
    thread_id,
    (SELECT pid FROM threads WHERE id = thread_id) AS pid,
    (SELECT tid FROM threads WHERE id = thread_id) AS tid,
    (SELECT comm FROM comms WHERE id = comm_id) AS command,
    call_path_id,
    """
            + emit_to_hex("ip")
            + """ AS ip,
    symbol_id,
    (SELECT name FROM symbols WHERE id = symbol_id) AS symbol,
    call_time,
    return_time,
    return_time - call_time AS elapsed_time,
    branch_count,
    insn_count,
    cyc_count,
    CASE WHEN cyc_count=0 THEN CAST(0 AS FLOAT) ELSE ROUND(CAST(insn_count AS FLOAT) / cyc_count, 2) END AS IPC,
    call_id,
    return_id,
    CASE WHEN flags=0 THEN '' WHEN flags=1 THEN 'no call' WHEN flags=2 THEN 'no return' WHEN flags=3 THEN 'no call/return' WHEN flags=6 THEN 'jump' ELSE flags END AS flags,
    parent_call_path_id,
    calls.parent_id
FROM calls INNER JOIN call_paths ON call_paths.id = call_path_id"""
        )

    views.append(
        """CREATE VIEW samples_view AS
SELECT
    id,
    time,
    cpu,
    (SELECT pid FROM threads WHERE id = thread_id) AS pid,
    (SELECT tid FROM threads WHERE id = thread_id) AS tid,
    (SELECT comm FROM comms WHERE id = comm_id) AS command,
    (SELECT name FROM selected_events WHERE id = evsel_id) AS event,
    """
        + emit_to_hex("ip")
        + """ AS ip_hex,
    (SELECT name FROM symbols WHERE id = symbol_id) AS symbol,
    sym_offset,
    (SELECT short_name FROM dsos WHERE id = dso_id) AS dso_short_name,
    """
        + emit_to_hex("to_ip")
        + """ AS to_ip_hex,
    (SELECT name FROM symbols WHERE id = to_symbol_id) AS to_symbol,
    to_sym_offset,
    (SELECT short_name FROM dsos WHERE id = to_dso_id) AS to_dso_short_name,
    (SELECT name FROM branch_types WHERE id = branch_type) AS branch_type_name,
    in_tx,
    insn_count,
    cyc_count,
    CASE WHEN cyc_count=0 THEN CAST(0 AS FLOAT) ELSE ROUND(CAST(insn_count AS FLOAT) / cyc_count, 2) END AS IPC,
    flags
FROM samples"""
    )

    views.append(
        """CREATE VIEW ptwrite_view AS
SELECT ptwrite.id, time, cpu,
    """
        + emit_to_hex("payload")
        + """ AS payload_hex,
    CASE WHEN exact_ip=0 THEN 'False' ELSE 'True' END AS exact_ip
FROM ptwrite INNER JOIN samples ON samples.id = ptwrite.id"""
    )

    views.append(
        """CREATE VIEW cbr_view AS
SELECT cbr.id, time, cpu, cbr, mhz, percent
FROM cbr INNER JOIN samples ON samples.id = cbr.id"""
    )

    views.append(
        """CREATE VIEW mwait_view AS
SELECT mwait.id, time, cpu,
    """
        + emit_to_hex("hints")
        + """ AS hints_hex,
    """
        + emit_to_hex("extensions")
        + """ AS extensions_hex
FROM mwait INNER JOIN samples ON samples.id = mwait.id"""
    )

    views.append(
        """CREATE VIEW pwre_view AS
SELECT pwre.id, time, cpu, cstate, subcstate,
    CASE WHEN hw=0 THEN 'False' ELSE 'True' END AS hw
FROM pwre INNER JOIN samples ON samples.id = pwre.id"""
    )

    views.append(
        """CREATE VIEW exstop_view AS
SELECT exstop.id, time, cpu,
    CASE WHEN exact_ip=0 THEN 'False' ELSE 'True' END AS exact_ip
FROM exstop INNER JOIN samples ON samples.id = exstop.id"""
    )

    views.append(
        """CREATE VIEW pwrx_view AS
SELECT pwrx.id, time, cpu, deepest_cstate, last_cstate,
    CASE WHEN wake_reason=1 THEN 'Interrupt'
         WHEN wake_reason=2 THEN 'Timer Deadline'
         WHEN wake_reason=4 THEN 'Monitored Address'
         WHEN wake_reason=8 THEN 'HW'
         ELSE wake_reason END AS wake_reason
FROM pwrx INNER JOIN samples ON samples.id = pwrx.id"""
    )

    views.append(
        """CREATE VIEW power_events_view AS
SELECT
    samples.id,
    time,
    cpu,
    selected_events.name AS event,
    CASE WHEN selected_events.name='cbr' THEN (SELECT cbr FROM cbr WHERE cbr.id = samples.id) ELSE '' END AS cbr,
    CASE WHEN selected_events.name='cbr' THEN (SELECT mhz FROM cbr WHERE cbr.id = samples.id) ELSE '' END AS mhz,
    CASE WHEN selected_events.name='cbr' THEN (SELECT percent FROM cbr WHERE cbr.id = samples.id) ELSE '' END AS percent,
    CASE WHEN selected_events.name='mwait' THEN (SELECT """
        + emit_to_hex("hints")
        + """ FROM mwait WHERE mwait.id = samples.id) ELSE '' END AS hints_hex,
    CASE WHEN selected_events.name='mwait' THEN (SELECT """
        + emit_to_hex("extensions")
        + """ FROM mwait WHERE mwait.id = samples.id) ELSE '' END AS extensions_hex,
    CASE WHEN selected_events.name='pwre' THEN (SELECT cstate FROM pwre WHERE pwre.id = samples.id) ELSE '' END AS cstate,
    CASE WHEN selected_events.name='pwre' THEN (SELECT subcstate FROM pwre WHERE pwre.id = samples.id) ELSE '' END AS subcstate,
    CASE WHEN selected_events.name='pwre' THEN (SELECT hw FROM pwre WHERE pwre.id = samples.id) ELSE '' END AS hw,
    CASE WHEN selected_events.name='exstop' THEN (SELECT exact_ip FROM exstop WHERE exstop.id = samples.id) ELSE '' END AS exact_ip,
    CASE WHEN selected_events.name='pwrx' THEN (SELECT deepest_cstate FROM pwrx WHERE pwrx.id = samples.id) ELSE '' END AS deepest_cstate,
    CASE WHEN selected_events.name='pwrx' THEN (SELECT last_cstate FROM pwrx WHERE pwrx.id = samples.id) ELSE '' END AS last_cstate,
    CASE WHEN selected_events.name='pwrx' THEN (
        SELECT CASE WHEN wake_reason=1 THEN 'Interrupt'
                    WHEN wake_reason=2 THEN 'Timer Deadline'
                    WHEN wake_reason=4 THEN 'Monitored Address'
                    WHEN wake_reason=8 THEN 'HW'
                    ELSE wake_reason END
        FROM pwrx WHERE pwrx.id = samples.id) ELSE '' END AS wake_reason
FROM samples
INNER JOIN selected_events ON selected_events.id = evsel_id
WHERE selected_events.name IN ('cbr','mwait','exstop','pwre','pwrx')"""
    )

    views.append(
        """CREATE VIEW context_switches_view AS
SELECT
    context_switches.id,
    context_switches.machine_id,
    context_switches.time,
    context_switches.cpu,
    th_out.pid AS pid_out,
    th_out.tid AS tid_out,
    comm_out.comm AS comm_out,
    th_in.pid AS pid_in,
    th_in.tid AS tid_in,
    comm_in.comm AS comm_in,
    CASE WHEN context_switches.flags = 0 THEN 'in'
         WHEN context_switches.flags = 1 THEN 'out'
         WHEN context_switches.flags = 3 THEN 'out preempt'
         ELSE context_switches.flags END AS flags
FROM context_switches
INNER JOIN threads AS th_out ON th_out.id   = context_switches.thread_out_id
INNER JOIN threads AS th_in  ON th_in.id    = context_switches.thread_in_id
INNER JOIN comms AS comm_out ON comm_out.id = context_switches.comm_out_id
INNER JOIN comms AS comm_in  ON comm_in.id  = context_switches.comm_in_id"""
    )

    for v in views:
        do_query(v)

    do_query("END TRANSACTION")

    insert_sql = {
        "evsel": "INSERT INTO selected_events VALUES (?, ?)",
        "machine": "INSERT INTO machines VALUES (?, ?, ?)",
        "thread": "INSERT INTO threads VALUES (?, ?, ?, ?, ?)",
        "comm": "INSERT INTO comms VALUES (?, ?, ?, ?, ?)",
        "comm_thread": "INSERT INTO comm_threads VALUES (?, ?, ?)",
        "dso": "INSERT INTO dsos VALUES (?, ?, ?, ?, ?)",
        "symbol": "INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?)",
        "branch_type": "INSERT INTO branch_types VALUES (?, ?)",
        "sample_branches": "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        "sample_all": "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        "call_path": "INSERT INTO call_paths VALUES (?, ?, ?, ?)",
        "call": "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        "ptwrite": "INSERT INTO ptwrite VALUES (?, ?, ?)",
        "cbr": "INSERT INTO cbr VALUES (?, ?, ?, ?)",
        "mwait": "INSERT INTO mwait VALUES (?, ?, ?)",
        "pwre": "INSERT INTO pwre VALUES (?, ?, ?, ?)",
        "exstop": "INSERT INTO exstop VALUES (?, ?)",
        "pwrx": "INSERT INTO pwrx VALUES (?, ?, ?, ?)",
        "context_switch": "INSERT INTO context_switches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    }

    call_path_insert_sql = (
        insert_sql["call_path"]
        if (perf_db_export_calls or perf_db_export_callchains)
        else None
    )
    call_insert_sql = insert_sql["call"] if perf_db_export_calls else None
    sample_insert_sql = (
        insert_sql["sample_branches"] if branches else insert_sql["sample_all"]
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
