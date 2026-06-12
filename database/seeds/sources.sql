-- Seed: Fuentes de datos

INSERT INTO sources (name, base_url, active) VALUES
    ('getonbrd', 'https://www.getonbrd.com', TRUE),
    ('remotive', 'https://remotive.com', TRUE)
ON CONFLICT (name) DO NOTHING;