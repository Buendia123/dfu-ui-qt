#Version 2.0
#produce by Buendia.Deng
import sys
import os
import configparser
import re
import chardet

from enum import Enum
from PyQt5.QtCore import pyqtSlot, QProcess, pyqtSignal, QMetaObject, QObject, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from app_ui import Ui_ATE
from PyQt5.QtGui import QIcon
from sqllll import upload_result_to_database, upload_log_to_database

import datetime
import pymssql
import time
import logging, sys, os
import uuid
from pathlib import Path
from pprint import pprint

current_dir = os.path.dirname(os.path.abspath(__file__))

def myLog(LOG_NAME):
    logger = logging.getLogger(f'{LOG_NAME}')
    logger.setLevel(logging.DEBUG)

    # 检查并创建目录
    log_dir = os.path.join(current_dir, 'Log_center')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建文件 handler，用于写入日志文件
    fh = logging.FileHandler(f'{log_dir}/{LOG_NAME}.log')
    fh.setLevel(logging.DEBUG)

    # 创建 console handler，用于输出到控制台
    ch = logging.StreamHandler(sys.stdout)  # 使用 sys.stdout 确保控制台输出实时
    ch.setLevel(logging.DEBUG)

    # 定义 handler 的输出格式
    formatter = logging.Formatter('%(asctime)s-%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # 添加 handler 到 logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


config = configparser.ConfigParser()
config_path = os.path.join(current_dir, 'config.ini')

config.read(config_path)
SleepTime = config['HardWare']['Sleep_time']
MCU_FW_version = config['HardWare']['expected_mcu_fw']
MSA_FW_version = config['HardWare']['expected_msa_fw']
DSP_MM_FW_version = config['HardWare']['expected_dsp_fw_mm']
DSP_PMD_FW_version = config['HardWare']['expected_dsp_fw_pmd']
check_sn_flag = config['HardWare']['check_SN']

log = myLog("Upload_log")

ColorSelect = {
    'Green': 'rgb(0, 170, 0)',
    'Black': 'rgb(0, 0, 0)',
    'Red': 'rgb(255, 0, 0)',
    'Yellow': 'rgb(0, 170, 0)',
    'Blue': 'rgb(85, 0, 255)',
    'white': 'rgb(255, 255, 255)'
}

update_fw = ['MCU','MSA','DSP']

class Progress(Enum):
    Pending = 0
    Running = 1
    Finished = 2


class Status(Enum):
    Start = 0
    Running = 1
    Done = 2
    Finished = 3


class TestRes(Enum):
    Passed = 0
    PartialFailed = 1
    Failed = 2
    Default = 3


class ErrSNLine(Enum):
    A1 = 0
    A2 = 1
    A3 = 2
    A4 = 3
    Default = 4
    AllFalut = 5


class PassedSN(Enum):
    A1 = 0
    A2 = 1
    A3 = 2
    A4 = 3
    Default = 4


class UiAppX(Ui_ATE):
    def setupUi(self, App):
        super().setupUi(App)

        self.scrollArea.verticalScrollBar().rangeChanged.connect(
            lambda minV, maxV: self.scrollArea.verticalScrollBar().setValue(maxV)
        )
        self.scrollArea_2.verticalScrollBar().rangeChanged.connect(
            lambda minV, maxV: self.scrollArea_2.verticalScrollBar().setValue(maxV)
        )
        self.scrollArea_3.verticalScrollBar().rangeChanged.connect(
            lambda minV, maxV: self.scrollArea_3.verticalScrollBar().setValue(maxV)
        )
        self.scrollArea_4.verticalScrollBar().rangeChanged.connect(
            lambda minV, maxV: self.scrollArea_4.verticalScrollBar().setValue(maxV)
        )
        self.scrollArea_5.verticalScrollBar().rangeChanged.connect(
            lambda minV, maxV: self.scrollArea_5.verticalScrollBar().setValue(maxV)
        )

        self.pushButton.toggled.connect(
            lambda checked: self.pushButton.setText('&Stop' if checked else '&Run')
        )

    def change_status(self, status: Status):
        if status == Status.Start:
            self.label.setText('Start')
            self.label.setStyleSheet(f'color:{ColorSelect["Black"]}')
        elif status == Status.Running:
            self.label.setText('Running')
            self.label.setStyleSheet(f'color:{ColorSelect["Black"]}')
        elif status == Status.Done:
            self.label.setText('')
            self.label.setStyleSheet(f'color:{ColorSelect["Blue"]}')
        elif status == Status.Finished:
            self.label.setText('')

    def ShowRes(self, Res: TestRes):
        if Res == TestRes.Passed:
            self.label_4.setText('Passed')
            self.label_4.setStyleSheet(f'color:{ColorSelect["Green"]}')
        elif Res == TestRes.PartialFailed:
            self.label_4.setText('Failed')
            self.label_4.setStyleSheet(f'color:{ColorSelect["Red"]}')
        elif Res == TestRes.Failed:
            self.label_4.setText('Failed')
            self.label_4.setStyleSheet(f'color:{ColorSelect["Red"]}')
        elif Res == TestRes.Default:
            self.label_4.setText('')
            self.label_4.setStyleSheet(f'color:{ColorSelect["white"]}')

    def SetListRed(self, SNEr: ErrSNLine):
        if SNEr == ErrSNLine.A1:
            self.lineEdit_2.setStyleSheet(f'background-color:rgb(255, 0, 0)')
        elif SNEr == ErrSNLine.A2:
            self.lineEdit_3.setStyleSheet(f'background-color: rgb(255, 0, 0)')
        elif SNEr == ErrSNLine.A3:
            self.lineEdit_4.setStyleSheet(f'background-color: rgb(255, 0, 0)')
        elif SNEr == ErrSNLine.A4:
            self.lineEdit_5.setStyleSheet(f'background-color:rgb(255, 0, 0)')
        elif SNEr == ErrSNLine.Default:
            self.lineEdit_2.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_3.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_4.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_5.setStyleSheet(f'background-color: rgb(255, 255, 255)')
        elif SNEr == ErrSNLine.AllFalut:
            self.lineEdit_2.setStyleSheet(f'background-color: rgb(255, 0, 0)')
            self.lineEdit_3.setStyleSheet(f'background-color: rgb(255, 0, 0)')
            self.lineEdit_4.setStyleSheet(f'background-color: rgb(255, 0, 0)')
            self.lineEdit_5.setStyleSheet(f'background-color: rgb(255, 0, 0)')

    def SetListGreen(self, SNPs: PassedSN):
        if SNPs == PassedSN.A1:
            self.lineEdit_2.setStyleSheet(f'background-color:rgb(0, 170, 0)')
        elif SNPs == PassedSN.A2:
            self.lineEdit_3.setStyleSheet(f'background-color: rgb(0, 170, 0)')
        elif SNPs == PassedSN.A3:
            self.lineEdit_4.setStyleSheet(f'background-color: rgb(0, 170, 0)')
        elif SNPs == PassedSN.A4:
            self.lineEdit_5.setStyleSheet(f'background-color:rgb(0, 170, 0)')
        elif SNPs == PassedSN.Default:
            self.lineEdit_2.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_3.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_4.setStyleSheet(f'background-color: rgb(255, 255, 255)')
            self.lineEdit_5.setStyleSheet(f'background-color: rgb(255, 255, 255)')


class App(QMainWindow):
    logging = pyqtSignal(str)
    logging_a1 = pyqtSignal(str)
    logging_a2 = pyqtSignal(str)
    logging_a3 = pyqtSignal(str)
    logging_a4 = pyqtSignal(str)
    locked = pyqtSignal(bool)
    running = pyqtSignal(bool)
    _reset = pyqtSignal()
    status = pyqtSignal(Status)
    test_res = pyqtSignal(TestRes)
    SN_Failed = pyqtSignal(ErrSNLine)
    SN_Pass = pyqtSignal(PassedSN)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UiAppX()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon('Volex-Logo.ico'))
        self.sleep_time = int(SleepTime)
        self.failednum = 0
        self.portnum = 0
        self.detenum = 0
        self.stop_flag = 0

        self.missing_keys = []
        self.sns = {
            'A1': '',
            'A2': '',
            'A3': '',
            'A4': '',
        }
        
        self.UID = {
            'A1': '',
            'A2': '',
            'A3': '',
            'A4': '',
        }
        self.outputs = {
            'DEFAULT': '',
            'A1': '',
            'A2': '',
            'A3': '',
            'A4': '',
        }
        self.loggings = {
            'DEFAULT': self.logging,
            'A1': self.logging_a1,
            'A2': self.logging_a2,
            'A3': self.logging_a3,
            'A4': self.logging_a4,
        }
        self.processes = {
            'DEFAULT': QProcess(self),
            'A1': QProcess(self),
            'A2': QProcess(self),
            'A3': QProcess(self),
            'A4': QProcess(self),
        }
        self.progresses = {
            'DEFAULT': Progress.Pending,
            'A1': Progress.Pending,
            'A2': Progress.Pending,
            'A3': Progress.Pending,
            'A4': Progress.Pending,
        }
        self.script_result = {
            'A1': '',
            'A2': '',
            'A3': '',
            'A4': ''
        }
        self.version_result = {
            'A1': '',
            'A2': '',
            'A3': '',
            'A4': ''
        }
        self.utb_out = ''
        self.step = 0
        self.form_template = {
            'slot': '0',
            'Type':' ',
            'SN': ' ',
            'PC-SN': ' ',
            'MCU': '0.0.0.0',
            'DSP': '0.0.0.0',
            'MSA': '0.0.0'
        }
        self.fw_status = {
            'A1': update_fw[0],
            'A2': update_fw[0],
            'A3': update_fw[0],
            'A4': update_fw[0]
        }

        
        self.pre_version = {f"A{i}": self.form_template.copy() for i in range(1, 5)}
        self.updated_version = {f"A{i}": self.form_template.copy() for i in range(1, 5)}
        
        for key, process in self.processes.items():
            process.errorOccurred.connect(lambda error, name=key: self.handle_error(error, name=name))
            process.readyReadStandardOutput.connect(lambda name=key: self.read_stdout(name=name))
            process.readyReadStandardError.connect(lambda name=key: self.read_stderr(name=name))
            process.started.connect(lambda name=key: self.process_started(name=name))
            process.finished.connect(
                lambda exit_code, exit_status, name=key: self.process_finished(exit_code, exit_status, name=name))

        self.once_connections: list[QMetaObject.Connection] = []

        self.status.connect(self.ui.change_status)
        self.status.emit(Status.Start)

        self.test_res.connect(self.ui.ShowRes)
        self.test_res.emit(TestRes.Default)

        self.SN_Failed.connect(self.ui.SetListRed)
        self.SN_Failed.emit(ErrSNLine.Default)

        self.SN_Pass.connect(self.ui.SetListGreen)
        self.SN_Pass.emit(PassedSN.Default)

    @pyqtSlot(int)
    def set_sleep_time(self, value: int):
        self.sleep_time = value
        self.log(f'Sleep time: {self.sleep_time}')

    def _set_sn(self, value: str, name: str):
        self.sns[name] = value

    @pyqtSlot(str)
    def set_sn_a1(self, value: str):
        self._set_sn(value, 'A1')

    @pyqtSlot(str)
    def set_sn_a2(self, value: str):
        self._set_sn(value, 'A2')

    @pyqtSlot(str)
    def set_sn_a3(self, value: str):
        self._set_sn(value, 'A3')

    @pyqtSlot(str)
    def set_sn_a4(self, value: str):
        self._set_sn(value, 'A4')

    @pyqtSlot(QProcess)
    def hardware_setup(self, process: QProcess):
        self.log('Hardware setup')  
        process.start('utb_util', ['-status'])

    @pyqtSlot()
    def start_testing(self,component:int):
        target_dir = os.path.join(current_dir, "EM20_DFU_V0.0.3")
        if 'EM20_DFU_V0.0.3' not in current_dir:
            os.chdir(target_dir)
        def command(com: int, type: str,component:str):
            if type == 'DD':
                path = r'./firmware/em400qd/release'
            if type == '56':
                path = r'./firmware/em200q/release'
            return 'python', [
                'ALdfu.py',
                '-d',
                'linux',
                '-p',
                str(com),
                '-b',
                str(path),
                '-c',
                str(component)
            ]
        for com, (name, sn) in enumerate(self.sns.items(), 3):
            self.fw_status[f'{name}']=update_fw[component]
            if sn == '':
                self.progresses[name] = Progress.Finished
                continue
            if "DD" in self.pre_version[f'{name}']['Type']:
                self.processes[name].start(*command(com, 'DD',self.fw_status[f'{name}']))
            elif "QSFP+" in self.pre_version[f'{name}']['Type']:
                self.processes[name].start(*command(com, '56',self.fw_status[f'{name}']))
        os.chdir('..')

    def run_status_set(self):
        self.clearLog('A1')
        self.clearLog('A2')
        self.clearLog('A3')
        self.clearLog('A4')
        self.clearLog()
        self.SN_Failed.emit(ErrSNLine.Default)
        self.status.emit(Status.Start)
        self.test_res.emit(TestRes.Default)
        self.SN_Pass.emit(PassedSN.Default)
        self.failednum = 0
        self.portnum = 0
        self.stop_flag = 0
        self.missing_keys = []
        self.utb_out = ''
        self.step = 0
        self.detenum = 0

    @pyqtSlot(bool)
    def run_or_stop(self, to: bool):
        if to:
            self.run_status_set()
            self.acquire(self.running, self._reset)
            self.log('Running')
            self.init()
            for sn in self.sns.values():
                if sn != '' and sn != ' ' and sn != '\r' and sn != '\n':
                    self.portnum += 1
            process = self.processes['DEFAULT']

            self.hardware_setup(process)
        else:
            self.log('Stopped')
            self.status.emit(Status.Done)
            self.step = 0
            self.reset()

    def handle_error(self, error: QProcess.ProcessError, name: str = 'DEFAULT'):
        error_map = {
            QProcess.ProcessError.FailedToStart: 'Failed to start',
            QProcess.ProcessError.Crashed: 'Crashed',
            QProcess.ProcessError.Timedout: 'Timed out',
            QProcess.ProcessError.WriteError: 'Write error',
            QProcess.ProcessError.ReadError: 'Read error',
            QProcess.ProcessError.UnknownError: 'Unknown error',
        }
        self.log(f'Error: {error_map[error]}', name=name)
        self.reset()

    def collect_relevant_slots(self, slot_to_sn):
        relevant_keys = []

        for slot, sn in self.sns.items():
            if slot not in slot_to_sn:
                if sn.strip() != '':
                    relevant_keys.append(slot)
            elif slot_to_sn[slot].strip() != sn.strip():
                relevant_keys.append(slot)
        return relevant_keys

    def SetPortColor(self, port: str):
        if port == 'A1':
            self.SN_Failed.emit(ErrSNLine.A1)
        elif port == 'A2':
            self.SN_Failed.emit(ErrSNLine.A2)
        elif port == 'A3':
            self.SN_Failed.emit(ErrSNLine.A3)
        elif port == 'A4':
            self.SN_Failed.emit(ErrSNLine.A4)

    def SetPortGreen(self, port: str):
        if port == 'A1':
            self.SN_Pass.emit(PassedSN.A1)
        elif port == 'A2':
            self.SN_Pass.emit(PassedSN.A2)
        elif port == 'A3':
            self.SN_Pass.emit(PassedSN.A3)
        elif port == 'A4':
            self.SN_Pass.emit(PassedSN.A4)

    def Set_Failed_SN(self, name):
        if name == 'A1':
            self.SN_Failed.emit(ErrSNLine.A1)
        elif name == 'A2':
            self.SN_Failed.emit(ErrSNLine.A2)
        elif name == 'A3':
            self.SN_Failed.emit(ErrSNLine.A3)
        elif name == 'A4':
            self.SN_Failed.emit(ErrSNLine.A4)

    def parse_al_pll_screen_output(self, name: str, output: str):
        sn = self.sns[f'{name}']
        log_filename = f'{sn}_dfu_precess.log'
        log_path = os.path.join(current_dir, 'dfu_process_logs', log_filename)
        with open(log_path, 'w') as log_file:
            log_file.write(output)
            
        pattern = re.compile(r"'exception':\s+None")
        match = pattern.search(output)
        if match:
            self.script_result[name] = 'passed'
        else:
            self.script_result[name] = 'failed'
        # self.step+=1
    
            
    ## TODO jude detected failed        
    def version_detected(self, output: str):
        pattern = re.compile(
            r'Slot\s+(\d+):\s+(QSFP(?:-DD|\+)).*?\s+(\S+)\s+(CA|CV[\w-]+).*?MCU:(\d+\.\d+\.\d+\.\d+)\s+DSP:(\d+\.\d+\.\d+\.\d+)\s+MSA:(\d+\.\d+\.\d+)',
            re.DOTALL
        )
        pattern_SN = r"QSFP\+?\S+\s+(\S+)\s+(\S+)"
        matches = pattern.findall(output)
        matche_sn = re.findall(pattern_SN, output)
        if self.step == 0:
            for key, sn in self.sns.items():
                if sn != '':
                    log_filename = f'{sn}_dfu.log'
                    log_path = os.path.join(current_dir, 'dfu_version_logs', log_filename)
                with open(log_path, 'w') as log_file:
                    log_file.write(f"pre-updated version\n\n{output}")
            for idx, (match, sn_pair) in enumerate(zip(matches, matche_sn)):
                self.detenum += 1
                slot_number = int(match[0])
                module_type = match[1]
                sn = sn_pair[1]
                pcsn = match[3] 
                mcu_version = match[4]
                dsp_version = match[5]
                msa_version = match[6]
                
                if f'A{slot_number}' in self.pre_version:
                    self.pre_version[f'A{slot_number}'].update({
                        "slot": slot_number,
                        "Type": module_type,
                        "SN": sn,
                        "PC-SN": pcsn,
                        "MCU": mcu_version,
                        "DSP": dsp_version,
                        "MSA": msa_version
                    })
            if self.portnum != self.detenum:
                self.log(f'{self.portnum}, {self.detenum}')
                self.log('Number not match')
                self.status.emit(Status.Finished)
                self.test_res.emit(TestRes.Failed)
                self.SN_Failed.emit(ErrSNLine.AllFalut)
                self.reset()
                return
            
        elif self.step==4:
            for key, sn in self.sns.items():
                if sn != '':
                    log_filename = f'{sn}_dfu.log'
                    log_path = os.path.join(current_dir, 'dfu_version_logs', log_filename)
                with open(log_path, 'a') as log_file:
                    log_file.write(f"updated version\n\n {output}")
            for idx, (match, sn_pair) in enumerate(zip(matches, matche_sn)):
                slot_number = int(match[0])
                module_type = match[1]
                sn = sn_pair[1] 
                pcsn = match[3] 
                mcu_version = match[4]
                dsp_version = match[5]
                msa_version = match[6]
                if f'A{slot_number}' in self.updated_version:
                        self.updated_version[f'A{slot_number}'].update({
                        "slot": slot_number,
                        "Type": module_type,
                        "SN": sn,
                        "PC-SN": pcsn,
                        "MCU": mcu_version,
                        "DSP": dsp_version,
                        "MSA": msa_version
                    })
        
    def jude_sn(self):
        if check_sn_flag == 'True':
            for com, (name, sn) in enumerate(self.sns.items(), 3):
                det_sn = str(self.pre_version[f'{name}']['SN'])
                if 'VD' in sn:
                    if sn != det_sn:
                        self.log(f'SN not match, detected is {det_sn} \n',name=name)
                        self.SetPortColor(name)
                        self.stop_flag = 1
                        self.test_res.emit(TestRes.Failed)
                        self.status.emit(Status.Finished)
                        self.reset()
                        break
    
    def read_stdout(self, name: str = 'DEFAULT'):
        output = self.processes[name].readAllStandardOutput().data().decode("utf-8", errors="replace")
        if name == 'DEFAULT':
            self.utb_out += output
        if name != 'DEFAULT':
            self.log(output, end='', name=name)

    def read_stderr(self, name: str = 'DEFAULT'):
        error: str = self.processes[name].readAllStandardError().data().decode()
        self.log(''.join(f'Error: {line}' for line in error.splitlines(keepends=True)), end='', name=name)

    def process_started(self, name: str = 'DEFAULT'):
        self.log('Process started', name=name)
        self.progresses[name] = Progress.Running

    def get_latest_files(self):
        Log_path =  os.path.join(current_dir, 'dfu_version_logs')
        files = [os.path.join(Log_path, f) for f in os.listdir(Log_path) if
                 os.path.isfile(os.path.join(Log_path, f))]
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [os.path.basename(f) for f in files[:self.portnum]]

    def update_SQL(self):
        upload_flag = 0
        sn = ''
        pcsn = ''
        for key, value in self.version_result.items():
            self.UID[key] = str(uuid.uuid4())
            id = self.UID[key]
            # print("Res:", key, ":", self.UID[key])
            if value == 'passed' and self.sns[key] != '':
                if 'VD'in self.sns[key]:
                    sn = self.sns[key]
                else:
                    pcsn = self.sns[key]
                if upload_result_to_database(sn,' ',log, 'OK', id,self.pre_version[f'{key}']['MCU'],\
                    self.pre_version[f'{key}']['DSP'],self.pre_version[f'{key}']['MSA'],\
                        self.updated_version[f'{key}']['MCU'],self.updated_version[f'{key}']['DSP'],\
                        self.updated_version[f'{key}']['MSA'],pcsn):
                    self.log(f"{self.sns[key]} Results is upload")
                else:
                    self.log(f"{self.sns[key]} Results upload failed!")
                    self.test_res.emit(TestRes.Failed)
                    upload_flag = 1
            if value == 'failed':
                self.failednum += 1
                if upload_result_to_database(sn,' ',log, 'NG', id,self.pre_version[f'{key}']['MCU'],\
                    self.pre_version[f'{key}']['DSP'],self.pre_version[f'{key}']['MSA'],\
                        self.updated_version[f'{key}']['MCU'],self.updated_version[f'{key}']['DSP'],\
                        self.updated_version[f'{key}']['MSA'],pcsn):
                    self.log(f"{self.sns[key]} Results is upload")
                else:
                    self.log(f"{self.sns[key]} Results upload failed!")
                    self.test_res.emit(TestRes.Failed)
                    upload_flag = 1
        log_path = self.get_latest_files()

        for path in log_path:
            uploaded = False
            for sensor_key in ['A1', 'A2', 'A3', 'A4']:
                if self.sns[sensor_key] in path:
                    id = self.UID[sensor_key]
                    print("log:", sensor_key, ":", id)
                    time = datetime.datetime.now()
                    if upload_log_to_database(path, log, time, id):
                        self.log(f"{path} Log is uploaded")
                        uploaded = True
                        break
            if not uploaded:
                self.log(f"{path} Log upload failed!")
                upload_flag = 1
        if upload_flag == 0 and self.failednum == 0:
            self.test_res.emit(TestRes.Passed)
        else:
            self.test_res.emit(TestRes.Failed)
        self.status.emit(Status.Finished)
            
    def result_check(self):
        self.log(f'Port number:', str(self.portnum))
        for com, (name, sn) in enumerate(self.sns.items(), 3): 
            if sn != '':
                if self.updated_version[f'{name}']['MCU'] == MCU_FW_version and self.updated_version[f'{name}']['MSA'] == MSA_FW_version \
                    and (self.updated_version[f'{name}']['DSP'] == DSP_MM_FW_version or self.updated_version[f'{name}']['DSP'] == DSP_PMD_FW_version):
                    self.version_result[f'{name}'] = 'passed'
                else:
                    self.version_result[f'{name}'] = 'failed'
                    self.test_res.emit(TestRes.Failed)
                    self.log('FW update failed',name=name)
                    return 
        for key, value in self.version_result.items():
            if self.sns[f'{key}'] !='':
                if not (value == self.script_result[f'{key}'] == 'passed'):
                    self.SetPortColor(str(key))
                    self.test_res.emit(TestRes.Failed)
                    self.log('check failed','\n',key)
                    return 
                else:
                    self.SetPortGreen(str(key))

        self.log('update successfully')
        # self.test_res.emit(TestRes.Passed)
        # self.status.emit(Status.Finished)
    
    
    def process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus, name: str = 'DEFAULT'):
        if name == 'DEFAULT':
            if self.step==0:
                self.version_detected(self.utb_out)
                self.utb_out = ''
                self.jude_sn()
                self.log("Start MCU")
                self.step+=1
                self.start_testing(0)
            if  self.step==4:
                self.version_detected(self.utb_out)
                self.utb_out = ''
                self.result_check()
                self.update_SQL()
                self.reset()
                return

        if name != 'DEFAULT':
            self.log(f'Process finished with exit code {exit_code}', name=name)
            self.parse_al_pll_screen_output(name, self.outputs[name])
        self.progresses[name] = Progress.Finished
        if all(progress == Progress.Finished for progress in self.progresses.values() if progress != self.progresses['DEFAULT']):
            if self.step==1:
                self.log("Start MSA")
                self.step+=1
                self.start_testing(1)
            elif self.step==2:
                self.log("Start DSP")
                self.step+=1
                self.start_testing(2)
            elif self.step==3:
                self.progresses['DEFAULT'] = Progress.Pending
                self.hardware_setup(self.processes['DEFAULT'])
                self.step+=1

            
    def init(self):
        self.stop_flag = 0
        self.status.emit(Status.Running)

    def reset(self):
        self._reset.emit()
        for connection in self.once_connections:
            QObject.disconnect(connection)
        self.once_connections.clear()
        for key, process in self.processes.items():
            process.kill()
        for key in self.progresses:
            self.progresses[key] = Progress.Pending

    def acquire(self, lock: pyqtSignal, key: pyqtSignal):
        class Releaser:
            def __init__(self, app=self):
                self.app = app
                self.connection = key.connect(self)

            def __call__(self, *args, **kwargs):
                self.app.log('Releasing lock')
                key.disconnect(self.connection)
                QTimer.singleShot(0, lambda: lock.emit(False))

        self.log('Acquiring lock')
        lock.emit(True)
        Releaser()

    def log(self, message: str, end: str = '\n', name: str = 'DEFAULT'):
        self.outputs[name] += message + end
        self.loggings[name].emit(self.outputs[name])

    def clearLog(self, name: str = 'DEFAULT'):
        self.outputs[name] = ''
        self.loggings[name].emit(self.outputs[name])

    def clear_rest(self):
        self.ui.lineEdit_5.clear()
        self.ui.lineEdit_4.clear()
        self.ui.lineEdit_3.clear()
        self.ui.lineEdit_2.clear()
        self.clearLog()
        self.clearLog('A1')
        self.clearLog('A2')
        self.clearLog('A3')
        self.clearLog('A4')
        self.status.emit(Status.Start)
        self.test_res.emit(TestRes.Default)
        self.SN_Failed.emit(ErrSNLine.Default)
        self.SN_Pass.emit(PassedSN.Default)
        self.ui.lineEdit_2.setFocus()
        self.failednum = 0
        self.portnum = 0
        self.stop_flag = 0
        self.detenum = 0
        self.missing_keys = []

    def focus_next_line_edit(self):
        current_line_edit = self.sender()
        if current_line_edit == self.ui.lineEdit_2:	
            self.ui.lineEdit_3.clear()
            self.ui.lineEdit_3.setFocus()
        elif current_line_edit == self.ui.lineEdit_3:
            self.ui.lineEdit_4.clear()
            self.ui.lineEdit_4.setFocus()
        elif current_line_edit == self.ui.lineEdit_4:
            self.ui.lineEdit_5.clear()
            self.ui.lineEdit_5.setFocus()


if __name__ == "__main__":
    os.environ['PATH'] += f':{os.environ["HOME"]}/diag_bin'
    # pprint({key: value for key, value in os.environ.items()})
    app = QApplication(sys.argv)
    widget = App()
    widget.show()
    sys.exit(app.exec())
