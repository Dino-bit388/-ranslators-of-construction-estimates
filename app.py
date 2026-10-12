import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import sys
import webview

load_dotenv()

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))


template_path = os.path.join(base_dir, 'templates')
static_path = os.path.join(base_dir, 'static')

app = Flask(
    __name__,
    template_folder = template_path,
    static_folder = static_path
)
app.secret_key = 'my-secret-key-2026-for-smet-analyzer' 

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        cursor_factory=RealDictCursor
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/estimates')
def estimates():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT ed.*, ot.name as object_type_name, wt.name as work_type_name
        FROM estimate_documents ed
        LEFT JOIN object_types ot ON ed.object_type_id = ot.id
        LEFT JOIN work_types wt ON ed.work_type_id = wt.id
        ORDER BY ed.upload_date DESC
    ''')
    estimates = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('estimates.html', estimates=estimates)

@app.route('/estimates/delete/<int:doc_id>', methods=['POST'])
def delete_estimate(doc_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Сначала удаляем связанные данные из-за внешних ключей
        cur.execute('DELETE FROM estimate_items WHERE document_id = %s', (doc_id,))
        cur.execute('DELETE FROM estimate_documents WHERE id = %s', (doc_id,))
        conn.commit()
        flash('Смета успешно удалена', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('estimates'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            object_type_id = request.form.get('object_type_id')
            work_type_id = request.form.get('work_type_id')
            area = request.form.get('area')
            year = request.form.get('year')
            source_name = request.form.get('source_name')
            object_name = request.form.get('object_name')
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            source_id = None
            if source_name:
                cur.execute('SELECT id FROM sources WHERE name = %s', (source_name,))
                existing = cur.fetchone()
                if existing:
                    source_id = existing['id']
                else:
                    cur.execute('INSERT INTO sources (name) VALUES (%s) RETURNING id', (source_name,))
                    source_id = cur.fetchone()['id']

            cur.execute('''
                INSERT INTO estimate_documents (file_name, source_id, object_name, object_type_id, work_type_id, area, year, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (filename, source_id, object_name, object_type_id, work_type_id, area, year, 'loaded'))
            
            doc_id = cur.fetchone()['id']
            
            try:
                df = pd.read_excel(filepath)
                material_col = None
                quantity_col = None
                unit_col = None
                
                for col in df.columns:
                    col_lower = str(col).lower()
                    if 'наименован' in col_lower or 'материал' in col_lower or 'ресурс' in col_lower:
                        material_col = col
                    if 'количеств' in col_lower or 'объем' in col_lower or 'кол-во' in col_lower:
                        quantity_col = col
                    if 'ед.изм' in col_lower or 'единиц' in col_lower or 'ед изм' in col_lower or 'ед.' in col_lower:
                        unit_col = col
                
                if material_col is None or quantity_col is None:
                    raise Exception("Не удалось определить колонки с наименованиями или количествами")
                
                items_inserted = 0
                for idx, row in df.iterrows():
                    material_name = str(row[material_col]) if pd.notna(row[material_col]) else None
                    quantity = float(row[quantity_col]) if pd.notna(row[quantity_col]) else None
                    unit = str(row[unit_col]) if unit_col and pd.notna(row[unit_col]) else None
                    
                    if material_name and material_name != 'nan' and quantity and quantity > 0:
                        cur.execute('''
                            INSERT INTO estimate_items (document_id, original_name, unit_original, quantity_original, row_number)
                            VALUES (%s, %s, %s, %s, %s)
                        ''', (doc_id, material_name[:500], unit, quantity, idx + 1))
                        items_inserted += 1
                
                cur.execute('UPDATE estimate_documents SET total_items = %s, status = %s WHERE id = %s', 
                           (items_inserted, 'parsed', doc_id))
                conn.commit()
                flash(f'Смета успешно загружена. Обработано {items_inserted} позиций.', 'success')
                
            except Exception as e:
                conn.rollback()
                cur.execute('UPDATE estimate_documents SET status = %s WHERE id = %s', ('error', doc_id))
                conn.commit()
                flash(f'Ошибка при парсинге файла: {str(e)}', 'error')
                logging.error(f"Parse error for {filename}: {str(e)}")
            finally:
                cur.close()
                conn.close()
            
            return redirect(url_for('estimates'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM object_types ORDER BY name')
    object_types = cur.fetchall()
    cur.execute('SELECT id, name FROM work_types ORDER BY name')
    work_types = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('upload.html', object_types=object_types, work_types=work_types)

@app.route('/materials')
def materials():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT ei.id, ei.original_name, ei.unit_original, ei.quantity_original, 
               ed.file_name, ei.is_material, im.subtype_id, msub.name as subtype_name
        FROM estimate_items ei
        JOIN estimate_documents ed ON ei.document_id = ed.id
        LEFT JOIN item_material im ON ei.id = im.item_id
        LEFT JOIN material_subtypes msub ON im.subtype_id = msub.id
        WHERE (ei.is_material = false OR ei.is_material IS NULL)
        LIMIT 100
    ''')
    items = cur.fetchall()
    
    cur.execute('SELECT id, name FROM material_groups ORDER BY name')
    groups = cur.fetchall()
    
    cur.execute('''
        SELECT ms.id, ms.name, mt.name as type_name, mg.name as group_name
        FROM material_subtypes ms
        JOIN material_types mt ON ms.type_id = mt.id
        JOIN material_groups mg ON mt.group_id = mg.id
        ORDER BY mg.name, mt.name, ms.name
    ''')
    subtypes = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('materials.html', items=items, groups=groups, subtypes=subtypes)

@app.route('/estimates/view/<int:doc_id>')
def view_estimate(doc_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT ed.*, ot.name as object_type_name, wt.name as work_type_name, s.name as source_name
        FROM estimate_documents ed
        LEFT JOIN object_types ot ON ed.object_type_id = ot.id
        LEFT JOIN work_types wt ON ed.work_type_id = wt.id
        LEFT JOIN sources s ON ed.source_id = s.id
        WHERE ed.id = %s
    ''', (doc_id,))
    estimate = cur.fetchone()
    
    cur.execute('''
        SELECT ei.*, ms.name as material_name
        FROM estimate_items ei
        LEFT JOIN item_material im ON ei.id = im.item_id
        LEFT JOIN material_subtypes ms ON im.subtype_id = ms.id
        WHERE ei.document_id = %s
        ORDER BY ei.row_number
    ''', (doc_id,))
    items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('view_estimate.html', estimate=estimate, items=items)

@app.route('/materials/classify', methods=['POST'])
def classify_material():
    item_id = request.form.get('item_id')
    subtype_id = request.form.get('subtype_id')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO item_material (item_id, subtype_id, assigned_by_user)
        VALUES (%s, %s, true)
        ON CONFLICT (item_id) DO UPDATE SET subtype_id = EXCLUDED.subtype_id, assigned_by_user = true, assigned_at = CURRENT_TIMESTAMP
    ''', (item_id, subtype_id))
    
    cur.execute('UPDATE estimate_items SET is_material = true WHERE id = %s', (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Материал классифицирован', 'success')
    return redirect(url_for('materials'))

@app.route('/analysis')
def analysis():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT ar.*, ot.name as object_type_name, 
               mg.name as group_name, mt.name as type_name, msub.name as subtype_name,
               bu.name as base_unit_name
        FROM analysis_results ar
        JOIN object_types ot ON ar.object_type_id = ot.id
        JOIN material_subtypes msub ON ar.material_subtype_id = msub.id
        JOIN material_types mt ON msub.type_id = mt.id
        JOIN material_groups mg ON mt.group_id = mg.id
        LEFT JOIN base_units bu ON ar.base_unit_id = bu.id
        ORDER BY ot.name, mg.name, mt.name
    ''')
    results = cur.fetchall()
    
    cur.execute('SELECT id, name FROM object_types ORDER BY name')
    object_types = cur.fetchall()
    
    cur.close()
    conn.close()
    
    results_json = json.dumps([{
        'object_type_name': r['object_type_name'],
        'subtype_name': r['subtype_name'],
        'mean': float(r['mean']) if r['mean'] else 0,
        'probability': float(r['probability']) if r['probability'] else 0
    } for r in results], default=str)
    
    return render_template('analysis.html', results=results, object_types=object_types, results_json=results_json)

@app.route('/analysis/calculate', methods=['POST'])
def calculate_analysis():
    object_type_id = request.form.get('object_type_id')
    
    if not object_type_id:
        flash('Выберите тип объекта', 'error')
        return redirect(url_for('analysis'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Удаляем старые результаты
    cur.execute('DELETE FROM analysis_results WHERE object_type_id = %s', (object_type_id,))
    
    # Упрощённый запрос без нормализации (используем исходные количества)
    cur.execute('''
        SELECT ed.id as doc_id, ed.area, 
               ei.quantity_original,
               im.subtype_id
        FROM estimate_documents ed
        JOIN estimate_items ei ON ed.id = ei.document_id
        JOIN item_material im ON ei.id = im.item_id
        WHERE ed.area > 0 
          AND ed.object_type_id = %s
          AND ei.quantity_original > 0
          AND ei.is_material = true
    ''', (object_type_id,))
    
    data = cur.fetchall()
    
    if not data:
        flash('Нет данных для анализа. Убедитесь, что:\n- Загружены сметы\n- Классифицированы материалы\n- Указана площадь объекта', 'error')
        cur.close()
        conn.close()
        return redirect(url_for('analysis'))
    
    # Собираем статистику по материалам
    material_stats = {}
    for row in data:
        subtype_id = row['subtype_id']
        doc_id = row['doc_id']
        area = float(row['area'])
        quantity = float(row['quantity_original'])
        
        consumption = quantity / area if area > 0 else None
        
        if subtype_id not in material_stats:
            material_stats[subtype_id] = {
                'consumptions': [],
                'doc_ids': set()
            }
        
        if consumption is not None:
            material_stats[subtype_id]['consumptions'].append(consumption)
            material_stats[subtype_id]['doc_ids'].add(doc_id)
    
    # Получаем общее количество смет
    cur.execute('SELECT COUNT(DISTINCT id) as cnt FROM estimate_documents WHERE object_type_id = %s AND area > 0', (object_type_id,))
    total_docs = cur.fetchone()['cnt']
    
    # Сохраняем результаты
    for subtype_id, stats in material_stats.items():
        consumptions = stats['consumptions']
        doc_count = len(stats['doc_ids'])
        probability = (doc_count / total_docs * 100) if total_docs > 0 else 0
        
        if consumptions:
            mean_val = sum(consumptions) / len(consumptions)
            sorted_cons = sorted(consumptions)
            n = len(sorted_cons)
            median_val = sorted_cons[n // 2] if n % 2 == 1 else (sorted_cons[n // 2 - 1] + sorted_cons[n // 2]) / 2
            min_val = min(consumptions)
            max_val = max(consumptions)
            
            from collections import Counter
            rounded = [round(c, 3) for c in consumptions]
            mode_counter = Counter(rounded)
            mode_val = mode_counter.most_common(1)[0][0] if mode_counter else None
        else:
            mean_val = median_val = mode_val = min_val = max_val = None
        
        cur.execute('''
            INSERT INTO analysis_results 
            (object_type_id, material_subtype_id, sample_count, occurrences, 
             probability, mean, median, mode_value, min_value, max_value, 
             is_reliable)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (object_type_id, subtype_id, len(consumptions), doc_count, 
              probability, mean_val, median_val, mode_val, min_val, max_val,
              len(consumptions) >= 3))
    
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f'Анализ выполнен успешно. Обработано {len(data)} позиций, {len(material_stats)} материалов.', 'success')
    return redirect(url_for('analysis'))

@app.route('/forecast')
def forecast():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT fr.*, po.name as object_name, po.planned_area, po.quantity, po.year,
               msub.name as subtype_name, mg.name as group_name, mt.name as type_name,
               bu.name as base_unit_name
        FROM forecast_results fr
        JOIN planned_objects po ON fr.planned_object_id = po.id
        JOIN material_subtypes msub ON fr.material_subtype_id = msub.id
        JOIN material_types mt ON msub.type_id = mt.id
        JOIN material_groups mg ON mt.group_id = mg.id
        JOIN base_units bu ON fr.base_unit_id = bu.id
        ORDER BY po.year, mg.name
    ''')
    forecasts = cur.fetchall()
    
    cur.execute('SELECT id, name FROM object_types ORDER BY name')
    object_types = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('forecast.html', forecasts=forecasts, object_types=object_types)

@app.route('/forecast/calculate', methods=['POST'])
def calculate_forecast():
    object_type_id = request.form.get('object_type_id')
    planned_area = float(request.form.get('planned_area'))
    quantity = int(request.form.get('quantity'))
    year = int(request.form.get('year'))
    object_name = request.form.get('object_name')
    selected_stat = request.form.get('selected_stat', 'mean')
    
    if not object_type_id:
        flash('Выберите тип объекта', 'error')
        return redirect(url_for('forecast'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Добавляем планируемый объект
    cur.execute('''
        INSERT INTO planned_objects (object_type_id, name, planned_area, quantity, year)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (object_type_id, object_name, planned_area, quantity, year))
    planned_id = cur.fetchone()['id']
    
    # Определяем поле для статистики
    stat_field = {
        'mean': 'mean',
        'median': 'median',
        'mode': 'mode_value'
    }.get(selected_stat, 'mean')
    
    # Получаем данные анализа
    cur.execute(f'''
        SELECT ar.material_subtype_id, ar.{stat_field} as stat_value, 
               ar.probability, ar.base_unit_id
        FROM analysis_results ar
        WHERE ar.object_type_id = %s AND ar.{stat_field} IS NOT NULL
    ''', (object_type_id,))
    
    results = cur.fetchall()
    
    print(f"Найдено материалов для прогноза: {len(results)}")  # Отладка
    
    if not results:
        flash('Нет данных для прогноза. Сначала выполните анализ.', 'error')
        conn.rollback()
        cur.close()
        conn.close()
        return redirect(url_for('forecast'))
    
    total_area = planned_area * quantity
    saved_count = 0
    
    for result in results:
        stat_value = float(result['stat_value']) if result['stat_value'] else 0
        probability = float(result['probability']) if result['probability'] else 0
        forecast_qty = total_area * stat_value
        
        cur.execute('''
            INSERT INTO forecast_results 
            (planned_object_id, material_subtype_id, selected_stat, stat_value, 
             probability, forecast_quantity, base_unit_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (planned_id, result['material_subtype_id'], selected_stat, 
              stat_value, probability, forecast_qty, result['base_unit_id']))
        saved_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f'Прогноз рассчитан. Сохранено {saved_count} материалов.', 'success')
    return redirect(url_for('forecast'))

if __name__ == '__main__':
    app.run()   
   