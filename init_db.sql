-- scenarios table
CREATE TABLE IF NOT EXISTS scenarios (
    id SERIAL PRIMARY KEY,
    scenario_uuid UUID UNIQUE NOT NULL,
    camera_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'init_startup',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- outbox_scenarios table (Transactional Outbox Pattern)
CREATE TABLE IF NOT EXISTS outbox_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_uuid UUID NOT NULL,
    payload JSONB NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP
);

-- scenario_results table (Inference Results Storage)
CREATE TABLE IF NOT EXISTS scenario_results (
    id SERIAL PRIMARY KEY,
    scenario_uuid UUID NOT NULL,
    frame_number INTEGER NOT NULL,
    detections JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(scenario_uuid, frame_number)
);

-- workers table (Worker Process Tracking)
CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    worker_id UUID UNIQUE NOT NULL,
    scenario_uuid UUID NOT NULL,
    camera_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    process_pid INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indices for fast queries
CREATE INDEX IF NOT EXISTS idx_scenarios_uuid ON scenarios(scenario_uuid);
CREATE INDEX IF NOT EXISTS idx_scenarios_status ON scenarios(status);
CREATE INDEX IF NOT EXISTS idx_outbox_published ON outbox_scenarios(published);
CREATE INDEX IF NOT EXISTS idx_results_uuid ON scenario_results(scenario_uuid);
CREATE INDEX IF NOT EXISTS idx_results_frame ON scenario_results(scenario_uuid, frame_number);
CREATE INDEX IF NOT EXISTS idx_workers_scenario ON workers(scenario_uuid);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);
