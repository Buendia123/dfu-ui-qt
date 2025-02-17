import DbProvider as DB
import datetime
import pymssql
import time
import logging,sys,os
import uuid


def myLog(LOG_NAME):
    logger = logging.getLogger(f'{LOG_NAME}')
    logger.setLevel(logging.DEBUG)

    # 检查并创建目录
    log_dir = 'Log_center'
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


def upload_result_to_database(SN:str, PN:str,logger, Result:str, test_id,MCU_Rev:str,DSP_Rev, \
    MSA_Rev, MCU_Ver,DSP_Ver,MSA_Ver,PC_SN):
    try:
        conn = pymssql.connect(DB.DbProvider.Db.server, DB.DbProvider.Db.user, DB.DbProvider.Db.password,
                               DB.DbProvider.Db.database)
        cursor = conn.cursor()
        result = Result
        Date = datetime.datetime.now()
        sqltask = f"INSERT INTO {DB.DbProvider.Db.resulttable} (Id, PN, SN, TestTime, MCU_Rev, \
            DSP_Rev, MSA_Rev, MCU_Ver,DSP_Ver,MSA_Ver,PC_SN,Result) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sqltask, (str(test_id), SN, PN, Date, MCU_Rev, DSP_Rev, MSA_Rev, MCU_Ver, DSP_Ver, MSA_Ver, PC_SN, result))
        conn.commit()
        time.sleep(2)
        logger.debug(f"{SN}:upload result to database success,test result:{Result}")
        return True
    except Exception as e:
        logger.debug(f"{SN}:upload result to database fail,test result:{Result}", str(e))
        return False


def read_file_as_binary(file_path):
    try:
        with open(file_path, 'rb') as file:
            binary_data = file.read()
            return binary_data
    except Exception as e:
        raise Exception(f"Failed to read file '{file_path}': {str(e)}")


def upload_log_to_database(sn_log, logger, start_date_time, test_id):
    try:
        # 连接到 SQL Server 数据库
        conn = pymssql.connect(DB.DbProvider.Db.server, DB.DbProvider.Db.user, DB.DbProvider.Db.password,
                               DB.DbProvider.Db.database)
        cursor = conn.cursor()

        sn = sn_log.split('_')[0]
        log_file_path = os.path.join('dfu_version_logs', sn_log)
        if not os.path.exists(log_file_path):
            print(log_file_path)
            logger.debug(f"file {log_file_path} not exist。")
        log_Stream = read_file_as_binary(log_file_path)

        cursor.execute(
            f"INSERT INTO {DB.DbProvider.Db.logtable} (Id, UPGradFWRecordId, SN, LogFileName, TestLog, TestTime) VALUES (%s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), str(test_id), sn, sn_log, log_Stream, start_date_time))

        conn.commit()
        conn.close()

        logger.debug(f"{sn} log has upload")
        return True

    except Exception as e:
        logger.debug(f"{sn_log} log upload failed", str(e))
        return False


def get_latest_files(log_path, count=1):
    files = [os.path.join(log_path, f) for f in os.listdir(log_path) if os.path.isfile(os.path.join(log_path, f))]
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return [os.path.basename(f) for f in files[:count]]


