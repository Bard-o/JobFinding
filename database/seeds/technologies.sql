-- Seed: Catálogo de tecnologías
-- Usado para matching en el extractor de tecnologías del scraper.

INSERT INTO technologies (name, category) VALUES
    -- Languages
    ('Python', 'language'),
    ('JavaScript', 'language'),
    ('TypeScript', 'language'),
    ('Go', 'language'),
    ('Rust', 'language'),
    ('Java', 'language'),
    ('C#', 'language'),
    ('Ruby', 'language'),
    ('PHP', 'language'),
    ('Swift', 'language'),
    ('Kotlin', 'language'),
    ('Scala', 'language'),

    -- Frameworks
    ('React', 'framework'),
    ('Angular', 'framework'),
    ('Vue', 'framework'),
    ('Django', 'framework'),
    ('FastAPI', 'framework'),
    ('Spring', 'framework'),
    ('Node.js', 'framework'),
    ('Express', 'framework'),
    ('Next.js', 'framework'),
    ('NestJS', 'framework'),
    ('Rails', 'framework'),
    ('Laravel', 'framework'),

    -- Cloud
    ('AWS', 'cloud'),
    ('Azure', 'cloud'),
    ('GCP', 'cloud'),

    -- DevOps
    ('Docker', 'devops'),
    ('Kubernetes', 'devops'),
    ('Terraform', 'devops'),
    ('Ansible', 'devops'),
    ('CI/CD', 'devops'),
    ('Jenkins', 'devops'),
    ('GitHub Actions', 'devops'),

    -- Databases
    ('PostgreSQL', 'database'),
    ('MySQL', 'database'),
    ('MongoDB', 'database'),
    ('Redis', 'database'),
    ('Elasticsearch', 'database'),
    ('SQLite', 'database'),

    -- Mobile
    ('React Native', 'mobile'),
    ('Flutter', 'mobile'),
    ('iOS', 'mobile'),
    ('Android', 'mobile')
ON CONFLICT (name) DO NOTHING;