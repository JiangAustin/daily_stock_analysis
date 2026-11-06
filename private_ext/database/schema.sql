CREATE TABLE IF NOT EXISTS research_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    raw_data_provider TEXT NOT NULL,
    research_adapter TEXT NOT NULL,
    run_mode TEXT,
    file_run_id TEXT,
    run_dir TEXT,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS raw_data_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    provider TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES research_runs(id)
);

CREATE TABLE IF NOT EXISTS fact_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    fact_pack_json TEXT NOT NULL,
    missing_fields_json TEXT,
    data_quality_warnings_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES research_runs(id)
);

CREATE TABLE IF NOT EXISTS scorecards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    total_score REAL NOT NULL,
    rating_band TEXT,
    scorecard_json TEXT NOT NULL,
    penalty_reasons_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES research_runs(id)
);

CREATE TABLE IF NOT EXISTS research_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    adapter TEXT NOT NULL,
    raw_output TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES research_runs(id)
);

CREATE TABLE IF NOT EXISTS research_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    rating TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    target_position REAL NOT NULL,
    horizon TEXT,
    thesis TEXT,
    bullish_points_json TEXT,
    bearish_points_json TEXT,
    catalysts_json TEXT,
    risks_json TEXT,
    invalidation_conditions_json TEXT,
    decision_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES research_runs(id)
);

CREATE TABLE IF NOT EXISTS paper_trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence REAL NOT NULL,
    target_position REAL NOT NULL,
    risk_gate_passed INTEGER NOT NULL,
    risk_gate_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(decision_id) REFERENCES research_decisions(id)
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    trade_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    amount REAL NOT NULL,
    fee REAL DEFAULT 0,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cost_price REAL NOT NULL,
    last_price REAL,
    market_value REAL,
    unrealized_pnl REAL
);

CREATE TABLE IF NOT EXISTS paper_nav (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    cash REAL NOT NULL,
    market_value REAL NOT NULL,
    total_nav REAL NOT NULL,
    daily_return REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decision_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    horizon_days INTEGER NOT NULL,
    start_price REAL,
    end_price REAL,
    return_pct REAL,
    benchmark_return_pct REAL,
    max_up_pct REAL,
    max_down_pct REAL,
    direction_correct INTEGER,
    review_notes TEXT,
    evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(decision_id) REFERENCES research_decisions(id)
);
