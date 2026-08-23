"""Constants for the Candy integration."""

DOMAIN = "candy"
PLATFORMS = ["sensor", "select", "time", "button"]

DATA_KEY_COORDINATOR = "coordinator"
DATA_KEY_CLIENT = "client"
DATA_KEY_WASH_CONTROL = "wash_control"

CONF_INTEGRATION_TITLE = "Candy"
CONF_KEY_USE_ENCRYPTION = "use_encryption"
CONF_ENABLE_WASH_CONTROL = "enable_wash_control"

WASH_REFRESH_TOUCH_PROGRAM = 16
WASH_REFRESH_TOUCH_PROGRAM_CODE = 41

UNIQUE_ID_WASHING_MACHINE = "{0}-washing_machine"
UNIQUE_ID_WASH_PROGRAM = "{0}-wash_program"
UNIQUE_ID_WASH_CYCLE_STATUS = "{0}-wash_cycle_status"
UNIQUE_ID_WASH_REMAINING_TIME = "{0}-wash_remaining_time"
UNIQUE_ID_WASH_TEMPERATURE = "{0}-wash_temperature"
UNIQUE_ID_WASH_SPIN_SPEED = "{0}-wash_spin_speed"
UNIQUE_ID_WASH_FILL_PERCENT = "{0}-wash_fill_percent"
UNIQUE_ID_WASH_ERROR = "{0}-wash_error"
UNIQUE_ID_WASH_DELAY = "{0}-wash_delay"
UNIQUE_ID_WASH_NTC_WATER = "{0}-wash_ntc_water"
UNIQUE_ID_WASH_NTC_DRUM = "{0}-wash_ntc_drum"
UNIQUE_ID_WASH_MOTOR_FREQ = "{0}-wash_motor_freq"
UNIQUE_ID_WASH_PROGRAM_CONTROL = "{0}-wash_program_control"
UNIQUE_ID_WASH_TEMPERATURE_CONTROL = "{0}-wash_temperature_control"
UNIQUE_ID_WASH_SPIN_SPEED_CONTROL = "{0}-wash_spin_speed_control"
UNIQUE_ID_WASH_SOIL_LEVEL_CONTROL = "{0}-wash_soil_level_control"
UNIQUE_ID_WASH_DELAY_CONTROL = "{0}-wash_delay_control"
UNIQUE_ID_WASH_START = "{0}-wash_start"
UNIQUE_ID_WASH_SCHEDULE = "{0}-wash_schedule"
UNIQUE_ID_WASH_STOP = "{0}-wash_stop"
UNIQUE_ID_WASH_PAUSE = "{0}-wash_pause"
UNIQUE_ID_WASH_RESUME = "{0}-wash_resume"
UNIQUE_ID_WASH_REFRESH_TOUCH = "{0}-wash_refresh_touch"

UNIQUE_ID_TUMBLE_DRYER = "{0}-tumble_dryer"
UNIQUE_ID_TUMBLE_PROGRAM = "{0}-tumble_program"
UNIQUE_ID_TUMBLE_CYCLE_STATUS = "{0}-tumble_cycle_status"
UNIQUE_ID_TUMBLE_REMAINING_TIME = "{0}-tumble_remaining_time"

UNIQUE_ID_OVEN = "{0}-oven"
UNIQUE_ID_OVEN_PROGRAM = "{0}-oven_program"
UNIQUE_ID_OVEN_TEMP = "{0}-oven-temp"
UNIQUE_ID_DISHWASHER = "{0}-dishwasher"
UNIQUE_ID_DISHWASHER_PROGRAM = "{0}-dishwasher_program"
UNIQUE_ID_DISHWASHER_REMAINING_TIME = "{0}-dishwasher_remaining_time"

DEVICE_NAME_WASHING_MACHINE = "Washing machine"
DEVICE_NAME_TUMBLE_DRYER = "Tumble dryer"
DEVICE_NAME_OVEN = "Oven"
DEVICE_NAME_DISHWASHER = "Dishwasher"

SUGGESTED_AREA_BATHROOM = "Bathroom"
SUGGESTED_AREA_KITCHEN = "Kitchen"
