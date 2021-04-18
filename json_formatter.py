import threading

from pythonjsonlogger import jsonlogger


class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(JsonFormatter, self).add_fields(log_record, record, message_dict)
        # keep only the message attribute
        log_record['timestamp'] = record.created
        log_record['severity'] = record.levelname
        log_record['thread_id'] = threading.get_ident()
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['process'] = record.process
        log_record['processName'] = record.processName
        log_record['logger_name'] = record.name
