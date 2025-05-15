import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6 import uic
from PyQt6.QtCore import *

import serial
import serial.tools.list_ports
import mysql.connector
import time

def checkSerialPorts():
    """사용 가능한 시리얼 포트 목록 확인"""
    ports = list(serial.tools.list_ports.comports())
    print("=== 사용 가능한 시리얼 포트 목록 ===")
    for port in ports:
        print(f"{port.device} - {port.description}")
    print("================================")
    return ports

# RFID 통신을 담당하는 스레드
class CardReceiver(QThread):
    cardDetected = pyqtSignal(str, str)  # UID, 직원ID 시그널
    registerModeEntered = pyqtSignal()   # 등록 모드 진입 시그널
    cardWriteComplete = pyqtSignal(str)  # 카드 쓰기 완료 시그널
    errorOccurred = pyqtSignal(str)      # 오류 시그널

    def __init__(self, conn, parent=None):
        super(CardReceiver, self).__init__(parent)
        self.is_running = False
        self.conn = conn

    def run(self):
        print("카드 리시버 스레드 시작")
        self.is_running = True
        while self.is_running:
            try:
                if self.conn.readable() and self.conn.in_waiting > 0:
                    res = self.conn.readline().decode('utf-8').strip()
                    print(f"시리얼 수신: '{res}'")
                    
                    if res.startswith("GRok: 등록 모드 진입"):
                        print("등록 모드 진입 시그널 발생")
                        self.registerModeEntered.emit()
                    elif res.startswith("GEwr"):
                        # 등록 모드에서 카드 감지
                        print("카드 감지 데이터 수신")
                        parts = res[4:].split(';')
                        if len(parts) >= 2:
                            uid = parts[0]
                            emp_id = parts[1]
                            print(f"카드 감지: UID={uid}, ID={emp_id}")
                            self.cardDetected.emit(uid, emp_id)
                    elif res.startswith("GEid"):  # 일반 모드에서의 카드 감지
                        print("일반 모드 카드 감지")
                        parts = res[4:].split(';')
                        if len(parts) >= 2:
                            uid = parts[0]
                            emp_id = parts[1]
                            print(f"일반 카드 감지: UID={uid}, ID={emp_id}")
                            # 등록 모드라면 이 데이터도 사용
                            if ';' in res and self.is_running:
                                self.cardDetected.emit(uid, emp_id)
                    elif res.startswith("GRok: 카드 쓰기 완료"):
                        # 카드 쓰기 완료 응답
                        print("카드 쓰기 완료 응답 수신")
                        parts = res.split(" → ")
                        if len(parts) > 1:
                            uid = parts[1].split(" ← ")[0]
                            print(f"쓰기 완료: UID={uid}")
                            self.cardWriteComplete.emit(uid)
                    elif res.startswith("GXe"):
                        # 오류 메시지
                        print(f"오류 메시지 수신: {res}")
                        self.errorOccurred.emit(res)
                    else:
                        print(f"알 수 없는 응답: {res}")
                time.sleep(0.1)  # CPU 사용률 낮추기
            except Exception as e:
                print(f"카드 리시버 오류: {e}")
                time.sleep(0.5)  # 오류 발생 시 잠시 대기
                    
    def stop(self):
        print("카드 리시버 스레드 정지")
        self.is_running = False

# 메인 윈도우 클래스
class EmployeeCardRegister(QDialog):
    def __init__(self):
        super().__init__()
        # UI 파일 직접 작성
        self.setupUi()
        
        # 시리얼 연결 설정
        try:
            # 실제 환경에 맞게 포트 설정 필요
            print("시리얼 포트 연결 시도...")
            self.conn = serial.Serial(port='/dev/ttyACM0', baudrate=9600, timeout=1)
            print(f"시리얼 포트 연결 성공: {self.conn}")
            
            # 연결 테스트 명령
            print("연결 테스트 메시지 전송")
            self.conn.write(b"GCmd0\n")
            self.conn.flush()
            time.sleep(0.5)  # 응답 대기
            if self.conn.in_waiting:
                response = self.conn.readline().decode('utf-8').strip()
                print(f"연결 테스트 응답: {response}")
            else:
                print("연결 테스트: 응답 없음")
                
        except Exception as e:
            print(f"시리얼 포트 연결 실패: {e}")
            QMessageBox.critical(self, "연결 오류", f"RFID 리더기 연결 실패: {e}")
            sys.exit(1)
        
        # 스레드 시작
        self.receiver = CardReceiver(self.conn)
        self.receiver.cardDetected.connect(self.onCardDetected)
        self.receiver.registerModeEntered.connect(self.onRegisterModeEntered)
        self.receiver.cardWriteComplete.connect(self.onCardWriteComplete)
        self.receiver.errorOccurred.connect(self.onErrorOccurred)
        self.receiver.start()
        
        # 버튼 연결
        self.newCardButton.clicked.connect(self.showEmployeeForm)
        self.registerCardButton.clicked.connect(self.registerCard)
        
        # 초기 상태 설정
        self.disableEmployeeForm()
        self.setWindowTitle("직원 카드 등록 시스템")
        
        # 현재 상태
        self.current_uid = ""
        self.current_emp_id = ""
        self.register_mode = False
        self.write_completed = False
    
    def setupUi(self):
        """UI 컴포넌트 직접 설정"""
        # 윈도우 기본 설정
        self.setWindowTitle("직원 카드 등록 시스템")
        self.resize(557, 364)
        
        # 카드 등록 상태 그룹박스
        self.groupBox = QGroupBox("카드 등록 상태", self)
        self.groupBox.setGeometry(QRect(20, 20, 511, 80))
        
        self.label = QLabel("상태:", self.groupBox)
        self.label.setGeometry(QRect(20, 40, 81, 19))
        
        self.statusLabel = QLabel("대기 중", self.groupBox)
        self.statusLabel.setGeometry(QRect(110, 40, 251, 19))
        
        self.newCardButton = QPushButton("신규 카드 등록하기", self.groupBox)
        self.newCardButton.setGeometry(QRect(370, 40, 121, 27))
        
        # 직원 정보 그룹박스
        self.groupBox_2 = QGroupBox("직원 정보", self)
        self.groupBox_2.setGeometry(QRect(20, 120, 511, 211))
        
        self.label_3 = QLabel("사번:", self.groupBox_2)
        self.label_3.setGeometry(QRect(20, 40, 81, 19))
        
        self.empIdEdit = QLineEdit(self.groupBox_2)
        self.empIdEdit.setGeometry(QRect(110, 40, 251, 27))
        
        self.label_4 = QLabel("이름:", self.groupBox_2)
        self.label_4.setGeometry(QRect(20, 90, 81, 19))
        
        self.empNameEdit = QLineEdit(self.groupBox_2)
        self.empNameEdit.setGeometry(QRect(110, 90, 251, 27))
        
        self.label_6 = QLabel("카드 UID:", self.groupBox_2)
        self.label_6.setGeometry(QRect(20, 130, 81, 19))
        
        self.cardUidLabel = QLabel("카드 미등록", self.groupBox_2)
        self.cardUidLabel.setGeometry(QRect(110, 130, 251, 19))
        
        self.registerCardButton = QPushButton("카드 등록", self.groupBox_2)
        self.registerCardButton.setGeometry(QRect(370, 160, 121, 27))
        
    def showEmployeeForm(self):
        """신규 카드 등록 버튼 클릭 시 직원 정보 입력 폼 활성화"""
        self.enableEmployeeForm()
        self.statusLabel.setText("직원 정보 입력 중")
        self.cardUidLabel.setText("카드 미등록")
        
    def enableEmployeeForm(self):
        """직원 정보 입력 폼 활성화"""
        self.empIdEdit.setEnabled(True)
        self.empNameEdit.setEnabled(True)
        self.registerCardButton.setEnabled(True)
        
    def disableEmployeeForm(self):
        """직원 정보 입력 폼 비활성화"""
        self.empIdEdit.setEnabled(False)
        self.empNameEdit.setEnabled(False)
        self.registerCardButton.setEnabled(False)
        
    def registerCard(self):
        """카드 등록 버튼 클릭 시 처리"""
        emp_id = self.empIdEdit.text().strip()
        emp_name = self.empNameEdit.text().strip()
        
        print(f"직원 카드 등록 시작: 사번={emp_id}, 이름={emp_name}")
        
        if not emp_id or not emp_name:
            print("입력 오류: 사번 또는 이름이 비어있음")
            QMessageBox.warning(self, "입력 오류", "사번과 이름을 모두 입력해주세요.")
            return
            
        # DB에서 직원 정보 확인
        print("DB에서 직원 정보 확인 중...")
        if self.checkEmployeeExists(emp_id, emp_name):
            print(f"직원 정보 확인 성공: {emp_id}, {emp_name}")
            # RFID 등록 모드로 전환
            self.statusLabel.setText("카드 등록 모드로 전환 중...")
            self.current_emp_id = emp_id
            self.enterRegisterMode()
        else:
            print(f"직원 정보 확인 실패: {emp_id}, {emp_name}")
            QMessageBox.warning(self, "직원 정보 오류", 
                               f"사번 '{emp_id}'와 이름 '{emp_name}'이 일치하는 직원 정보가 없습니다.")
    
    def checkEmployeeExists(self, emp_id, emp_name):
        """DB에서 직원 정보 확인"""
        try:
            # DB 연결
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="1234",
                database="rail_db"
            )
            
            cursor = conn.cursor()
            
            # 직원 정보 조회
            query = "SELECT * FROM employee WHERE id = %s AND name = %s"
            cursor.execute(query, (emp_id, emp_name))
            
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            QMessageBox.critical(self, "데이터베이스 오류", f"DB 조회 중 오류 발생: {e}")
            return False
            
    def enterRegisterMode(self):
        """RFID 등록 모드로 전환"""
        try:
            # 먼저 카드를 떼라는 메시지 표시
            self.statusLabel.setText("카드를 떼어주세요")
            QMessageBox.information(self, "안내", "먼저 카드를 리더기에서 떼어주세요.")
            
            # GCmd1 명령 전송 (등록 모드 진입)
            print(f"등록 모드 명령 전송: GCmd1")
            self.conn.write(b"GCmd1\n")
            self.conn.flush()  # 버퍼 즉시 전송
            print(f"등록 모드 명령 전송 완료")
            self.register_mode = True
            
            # 안내 메시지 표시
            self.statusLabel.setText("카드를 태그해주세요")
            QMessageBox.information(self, "안내", "이제 카드를 리더기에 태그해주세요.")
        except Exception as e:
            print(f"등록 모드 전환 오류: {e}")
            QMessageBox.critical(self, "통신 오류", f"등록 모드 전환 중 오류 발생: {e}")
            
    def onRegisterModeEntered(self):
        """등록 모드 진입 시그널 처리"""
        print("등록 모드 진입 시그널 처리")
        self.statusLabel.setText("카드를 태그해주세요")
        
    def onCardDetected(self, uid, emp_id):
        """카드 감지 시그널 처리"""
        print(f"카드 감지 처리: UID={uid}, EmpID={emp_id}")
        if self.register_mode:
            self.current_uid = uid
            self.cardUidLabel.setText(uid)
            self.statusLabel.setText("카드 감지됨. 등록 중...")
            
            # 카드에 직원 ID 쓰기
            try:
                # 잠시 대기 추가 - 사용자에게 상태 표시를 위해
                QApplication.processEvents()
                time.sleep(0.5)
                
                write_cmd = f"GCwr{self.current_emp_id}\n"
                print(f"카드 쓰기 명령 전송: {write_cmd.strip()}")
                self.conn.write(write_cmd.encode('utf-8'))
                self.conn.flush()
                print("카드 쓰기 명령 전송 완료")
            except Exception as e:
                print(f"카드 쓰기 명령 오류: {e}")
                QMessageBox.critical(self, "통신 오류", f"카드 쓰기 명령 전송 중 오류 발생: {e}")
                
            # 응답이 없는 경우 수동 처리 추가
            # 15초 이내에 응답이 없으면 타이머로 강제 종료
            QTimer.singleShot(15000, self.checkWriteComplete)
                
    def onCardWriteComplete(self, uid):
        """카드 쓰기 완료 시그널 처리"""
        try:
            print(f"카드 쓰기 완료 처리: UID={uid}")
            self.write_completed = True
            
            # DB에 RFID UID 업데이트
            self.updateEmployeeRfidUid(self.current_emp_id, uid)
            
            # 등록 모드 종료
            self.conn.write(b"GCmd0\n")
            self.register_mode = False
            
            # UI 업데이트
            QMessageBox.information(self, "등록 완료", f"직원 카드가 성공적으로 등록되었습니다.\n사번: {self.current_emp_id}\nUID: {uid}")
            self.statusLabel.setText("등록 완료")
            self.disableEmployeeForm()
            self.empIdEdit.setText("")
            self.empNameEdit.setText("")
            
        except Exception as e:
            print(f"카드 쓰기 완료 처리 오류: {e}")
            QMessageBox.critical(self, "등록 오류", f"카드 등록 중 오류 발생: {e}")
            
    def checkWriteComplete(self):
        """쓰기 완료 응답이 없을 경우 수동으로 처리"""
        if self.register_mode and not self.write_completed and self.current_uid:
            print("쓰기 완료 응답 타임아웃 - 수동 처리")
            # 이미 카드 UID를 받았으므로 수동으로 DB 업데이트
            self.updateEmployeeRfidUid(self.current_emp_id, self.current_uid)
            
            # 등록 모드 종료
            self.conn.write(b"GCmd0\n")
            self.register_mode = False
            
            # UI 업데이트
            QMessageBox.information(self, "등록 완료", 
                                    f"직원 카드가 등록되었습니다(수동 처리).\n사번: {self.current_emp_id}\nUID: {self.current_uid}")
            self.statusLabel.setText("등록 완료")
            self.disableEmployeeForm()
            self.empIdEdit.setText("")
            self.empNameEdit.setText("")
            
    def updateEmployeeRfidUid(self, emp_id, uid):
        """DB에 직원 RFID UID 업데이트"""
        try:
            # DB 연결
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="1234",
                database="rail_db"
            )
            
            cursor = conn.cursor()
            
            # UID의 콜론(:)을 제거하고 16진수를 정수로 변환
            uid_int = int(uid.replace(":", ""), 16)
            
            # RFID UID 업데이트
            query = "UPDATE employee SET rfid_uid = %s WHERE id = %s"
            cursor.execute(query, (uid_int, emp_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "데이터베이스 오류", f"DB 업데이트 중 오류 발생: {e}")
            return False
            
    def onErrorOccurred(self, error_msg):
        """오류 메시지 처리"""
        QMessageBox.warning(self, "RFID 오류", f"카드 등록 중 오류 발생: {error_msg}")
        
    def closeEvent(self, event):
        """프로그램 종료 시 정리 작업"""
        try:
            if self.register_mode:
                # 등록 모드 상태라면 정상 모드로 복귀
                self.conn.write(b"GCmd0\n")
                
            # 스레드 종료
            self.receiver.stop()
            self.receiver.wait()
            
            # 시리얼 연결 종료
            if self.conn.is_open:
                self.conn.close()
                
        except Exception as e:
            print(f"종료 중 오류: {e}")
            
        event.accept()
        
if __name__ == "__main__":
    # 사용 가능한 시리얼 포트 목록 확인
    ports = checkSerialPorts()
    
    app = QApplication(sys.argv)
    window = EmployeeCardRegister()
    window.show()
    sys.exit(app.exec())