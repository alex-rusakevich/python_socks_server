import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(module)-17s line:%(lineno)-4d '
                      '%(levelname)-8s %(message)s'
        },
        'simple': {
            'format': '%(levelname)-8s %(name)-15s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'detailed',
            'filename': 'app.log',
            'maxBytes': 1024 * 1024,  # 1MB
            'backupCount': 5,
            'level': 'DEBUG'
        },
        'errors': {
            'class': 'logging.FileHandler',
            'formatter': 'detailed',
            'filename': 'errors.log',
            'level': 'ERROR'
        }
    },
    'loggers': {
        'app': {
            'handlers': ['file', 'errors'],
            'level': 'DEBUG'
        },
        'external_library': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}


def setup_logger():
    logging.config.dictConfig(LOGGING_CONFIG)
