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
                content = file.read()
                try:
                    full_text = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        # 한국어 윈도우 기본 인코딩(CP949/EUC-KR) 시도
                        full_text = content.decode('cp949')
                    except UnicodeDecodeError:
                        # 그래도 안되면 ignore (깨진 채로라도 반환) 혹은 latin1
                        full_text = content.decode('utf-8', errors='ignore')
            else:
                raise Exception("지원되지 않는 파일 형식입니다. .txt 파일만 가능합니다.")
            
            return full_text.strip()

        except Exception as e:
            raise Exception(f"파일 텍스트 추출 중 오류: {str(e)}")
