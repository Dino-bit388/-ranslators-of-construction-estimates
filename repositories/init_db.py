import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cur = conn.cursor()
    
    commands = [
        """
        CREATE TABLE IF NOT EXISTS object_types (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS work_types (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            url TEXT,
            source_type VARCHAR(100),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS estimate_documents (
            id SERIAL PRIMARY KEY,
            file_name VARCHAR(255) NOT NULL,
            source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
            object_name VARCHAR(255),
            object_type_id INTEGER REFERENCES object_types(id),
            work_type_id INTEGER REFERENCES work_types(id),
            area NUMERIC(12,2),
            year INTEGER,
            region VARCHAR(100),
            note TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'loaded',
            total_items INTEGER DEFAULT 0,
            material_items INTEGER DEFAULT 0,
            items_need_classification INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS estimate_items (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES estimate_documents(id) ON DELETE CASCADE,
            original_name TEXT NOT NULL,
            unit_original VARCHAR(50),
            quantity_original NUMERIC(15,5),
            work_section VARCHAR(200),
            row_number INTEGER,
            is_material BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS material_groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS material_types (
            id SERIAL PRIMARY KEY,
            group_id INTEGER REFERENCES material_groups(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            UNIQUE(group_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS material_subtypes (
            id SERIAL PRIMARY KEY,
            type_id INTEGER REFERENCES material_types(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            UNIQUE(type_id, name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS item_material (
            item_id INTEGER PRIMARY KEY REFERENCES estimate_items(id) ON DELETE CASCADE,
            subtype_id INTEGER REFERENCES material_subtypes(id) ON DELETE SET NULL,
            assigned_by_user BOOLEAN DEFAULT TRUE,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS base_units (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            dimension VARCHAR(20)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS conversion_rules (
            id SERIAL PRIMARY KEY,
            unit_original VARCHAR(50) NOT NULL,
            base_unit_id INTEGER REFERENCES base_units(id) ON DELETE CASCADE,
            coefficient NUMERIC(20,10) NOT NULL,
            material_subtype_id INTEGER REFERENCES material_subtypes(id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT TRUE,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(unit_original, material_subtype_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS normalized_quantities (
            id SERIAL PRIMARY KEY,
            item_id INTEGER REFERENCES estimate_items(id) ON DELETE CASCADE,
            base_unit_id INTEGER REFERENCES base_units(id),
            normalized_quantity NUMERIC(15,5),
            conversion_rule_id INTEGER REFERENCES conversion_rules(id),
            normalized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id SERIAL PRIMARY KEY,
            object_type_id INTEGER REFERENCES object_types(id) ON DELETE CASCADE,
            material_subtype_id INTEGER REFERENCES material_subtypes(id) ON DELETE CASCADE,
            sample_count INTEGER,
            occurrences INTEGER,
            probability NUMERIC(5,2),
            mean NUMERIC(15,5),
            median NUMERIC(15,5),
            mode_value NUMERIC(15,5),
            min_value NUMERIC(15,5),
            max_value NUMERIC(15,5),
            base_unit_id INTEGER REFERENCES base_units(id),
            is_reliable BOOLEAN,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS planned_objects (
            id SERIAL PRIMARY KEY,
            object_type_id INTEGER REFERENCES object_types(id),
            work_type_id INTEGER REFERENCES work_types(id),
            name VARCHAR(255),
            planned_area NUMERIC(12,2),
            quantity INTEGER,
            year INTEGER,
            region VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS forecast_results (
            id SERIAL PRIMARY KEY,
            planned_object_id INTEGER REFERENCES planned_objects(id) ON DELETE CASCADE,
            material_subtype_id INTEGER REFERENCES material_subtypes(id),
            selected_stat VARCHAR(20),
            stat_value NUMERIC(15,5),
            probability NUMERIC(5,2),
            forecast_quantity NUMERIC(15,5),
            base_unit_id INTEGER REFERENCES base_units(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS error_logs (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES estimate_documents(id) ON DELETE SET NULL,
            item_id INTEGER REFERENCES estimate_items(id) ON DELETE SET NULL,
            error_type VARCHAR(100),
            error_message TEXT,
            severity VARCHAR(20),
            recommendation TEXT,
            status VARCHAR(20) DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        INSERT INTO object_types (name) VALUES ('многоквартирный жилой дом'), ('школа'), ('детский сад'), ('больница'), ('индивидуальный жилой дом')
        ON CONFLICT (name) DO NOTHING
        """,
        """
        INSERT INTO work_types (name) VALUES ('строительство'), ('капитальный ремонт'), ('реконструкция')
        ON CONFLICT (name) DO NOTHING
        """,
        """
        INSERT INTO base_units (name, dimension) VALUES 
        ('кг', 'масса'), ('т', 'масса'), ('м3', 'объем'), ('м2', 'площадь'), ('шт', 'штуки')
        ON CONFLICT (name) DO NOTHING
        """,
        """
        INSERT INTO material_groups (name) VALUES ('бетон'), ('металл'), ('древесина'), ('кирпич'), ('сыпучие')
        ON CONFLICT (name) DO NOTHING
        """
    ]
    
    for command in commands:
        try:
            cur.execute(command)
        except Exception as e:
            print(f"Error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("База данных инициализирована")

if __name__ == '__main__':
    init_database()