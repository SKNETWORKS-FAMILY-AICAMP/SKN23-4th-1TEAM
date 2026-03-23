import csv
import sys
import os
from db.database import get_connection

def import_csv_to_question_pool(csv_file_path, category_id):
    if not os.path.exists(csv_file_path):
        print(f"File not found: {csv_file_path}")
        return

    with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        if 'question' not in reader.fieldnames:
            print("Error: CSV 파일에 'question' 헤더가 없습니다.")
            return

        query = """
            INSERT INTO question_pool 
            (category_id, question_type, skill_tag, difficulty, content, reference_answer, keywords)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted_count = 0
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                for line_num, row in enumerate(reader, start=2):
                    content = row.get('question', '').strip()
                    
                    if not content:
                        continue
                        
                    answer = row.get('answer', '').strip()
                    code_example = row.get('code_example', '').strip()
                    if code_example:
                        answer += f"\n\n[코드 예시]\n{code_example}"
                        
                    time_comp = row.get('time_complexity', '').strip()
                    space_comp = row.get('space_complexity', '').strip()
                    if time_comp or space_comp:
                        answer += f"\n\n[복잡도]\n시간: {time_comp} / 공간: {space_comp}"

                    difficulty = row.get('difficulty', '').strip()
                    skill_tag = row.get('topic', '').strip()
                    keywords = row.get('tags', '').strip()
                    
                    values = (
                        category_id,
                        '기술',
                        skill_tag,
                        difficulty,
                        content,
                        answer,
                        keywords
                    )
                    
                    cur.execute(query, values)
                    inserted_count += 1
                    
    print(f"성공: 총 {inserted_count}개의 질문이 DB에 저장되었습니다.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        target_csv = sys.argv[1]
        try:
            cat_id = int(sys.argv[2])
            import_csv_to_question_pool(target_csv, cat_id)
        except ValueError:
            print("Error: category_id는 숫자여야 합니다.")
    else:
        print("사용법: python import_questions.py <data.csv> <category_id>")

# 사용법
# python import_questions.py <파일경로>.csv <category_id>
# ex. python import_questions.py backend/data/python_interview_questions_500.csv 1