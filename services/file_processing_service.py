import re
import pandas as pd

class FileProcessingService:
    def __init__(self):
        pass

    def extract_text_from_file(self, file) -> str:
        """
        업로드된 파일(.txt, .xlsx, .csv)에서 텍스트를 추출하여 하나의 문자열로 반환합니다.
        """
        try:
            full_text = ""

            # A. 텍스트 파일 (.txt) 
            if file.filename.lower().endswith('.txt'):
                full_text = file.read().decode('utf-8')

            # B. 엑셀/CSV 파일 (.xlsx, .csv)
            else:
                df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file, encoding='utf-8')
                
                # '문장' 또는 'sentence' 컬럼 찾기
                target_col = next((c for c in df.columns if '문장' in str(c) or 'sentence' in str(c).lower()), None)
                
                if target_col:
                    # 모든 행의 해당 컬럼 값을 가져와 줄바꿈으로 연결
                    sentences = df[target_col].astype(str).tolist()
                    full_text = "\n".join(sentences)
                else:
                    # 컬럼을 못 찾으면 첫 번째 컬럼 사용 (fallback)
                    full_text = "\n".join(df.iloc[:, 0].astype(str).tolist())
            
            return full_text.strip()

        except Exception as e:
            raise Exception(f"파일 텍스트 추출 중 오류: {str(e)}")
