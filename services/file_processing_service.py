import pandas as pd # Removed if unused, but check if needed. logic.py used it. Here it was used for excel.
# Actually, I should remove `import pandas` if I don't use it.
# Wait, I am replacing the method. I should also check imports.

class FileProcessingService:
    def __init__(self):
        pass

    def extract_text_from_file(self, file) -> str:
        """
        업로드된 파일(.txt)에서 텍스트를 추출하여 하나의 문자열로 반환합니다.
        지원 형식: .txt
        """
        try:
            full_text = ""

            # 텍스트 파일 (.txt) 
            if file.filename.lower().endswith('.txt'):
                full_text = file.read().decode('utf-8')
            else:
                raise Exception("지원되지 않는 파일 형식입니다. .txt 파일만 가능합니다.")
            
            return full_text.strip()

        except Exception as e:
            raise Exception(f"파일 텍스트 추출 중 오류: {str(e)}")
