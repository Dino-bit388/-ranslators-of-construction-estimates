INSERT INTO material_groups (name) VALUES ('Металл') ON CONFLICT (name) DO NOTHING;
INSERT INTO material_groups (name) VALUES ('Бетон') ON CONFLICT (name) DO NOTHING;
INSERT INTO material_groups (name) VALUES ('Сыпучие') ON CONFLICT (name) DO NOTHING;
INSERT INTO material_groups (name) VALUES ('Кирпич') ON CONFLICT (name) DO NOTHING;